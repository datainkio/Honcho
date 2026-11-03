#!/usr/bin/env python3
"""Run LinkedIn searches and stage job descriptions verbatim, by calling the linkedin MCP server over stdio.

The same server Claude Code uses (`.mcp.json`: `uvx mcp-server-linkedin@latest`, Russ's logged-in browser profile),
called from a script so no description passes through a model's context (F1 of context/token-efficiency-review.md).
`search` runs `search_jobs` for saved searches and records the returned jobs; `stage` runs `get_job_details` and writes
logs/inbox/<job_id>.md; `check` parses saved tool results with no network.
Settings come from the top-level `defaults:`, `searches:` and `selection:` blocks of the profile's criteria file;
`--incremental` lays the `incremental:` block over each search.

Usage:
    python3 pipeline/scripts/sources/linkedin_fetch.py search experience-designer [lead-ux-designer-remote ...] [--write]
    python3 pipeline/scripts/sources/linkedin_fetch.py search --all [--write]
    python3 pipeline/scripts/sources/linkedin_fetch.py search --all --incremental [--write]   # same-day second pass: `incremental:` over defaults
    python3 pipeline/scripts/sources/linkedin_fetch.py search experience-designer --pages 1 --raw logs/fixtures/linkedin   # capture a fixture
    python3 pipeline/scripts/sources/linkedin_fetch.py stage --search experience-designer [--write] <job_id> ...
    python3 pipeline/scripts/sources/linkedin_fetch.py stage [--write] experience-designer=<job_id> design-manager=<job_id> ...  # one run, many searches
    python3 pipeline/scripts/sources/linkedin_fetch.py check logs/fixtures/linkedin/*.json   # offline

Human-paced: waits `fetch_delay_seconds` before every tool call, including the first, and refuses more than
`max_fetches_per_run` ids. Stops the run (exit 1) on a tool error, a login, captcha or security-check page, or two
postings in a row with no readable description. No retries. Close the Claude Code LinkedIn session first
(`close_session`): the server drives one browser profile.
"""
import argparse
import datetime as dt
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from sources import common  # noqa: E402
from sources.common import Fail, Stop, q, safe_write  # noqa: E402

ROOT = naming.ROOT
INBOX = naming.INBOX
SEARCHES = naming.SEARCHES
MCP_JSON = naming.MCP_JSON

# Checked only where a posting should be (the text before 'About the job', or the whole text when that section is
# missing): a description may well say 'automated' or 'sign in'.
CHALLENGE = ("security verification", "security check", "unusual activity", "captcha", "verify you're a human",
             "verify you are human", "automated", "sign in to", "join linkedin", "join now", "authwall")
AGE = re.compile(r"^(?:Reposted )?(\d+) (minute|hour|day|week|month)s? ago$")
UNIT_DAYS = {"minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30}
JOB_ID = re.compile(r"^\d{6,}$")
# Redesigned search page: lines that are never part of a card's title, company and location. A line not matched
# here and not in a card is caught by the card count check, never mislabeled.
BADGE = re.compile(r"^(?:[·•]|---|\d+|Next|Previous|Viewed|Applied|Saved|Promoted|Easy Apply|Be an early applican.*"
                   r"|You’d be a top applicant|Actively reviewing applicants|Posted .*|.*\bbenefits?$|\$.*"
                   r"|(?:Medical|Vision|Dental|401\(k\))(?:, .*)?|.* works? here|[\d,]+\+? results"
                   r"|How promoted jobs are ranked|How AI search works|We found more results related to your search.*"
                   r"|Are these results helpful\?|Your feedback helps us improve search results\."
                   r"|No results found|Try shortening or rephrasing your search\.|Clear all filters)$")
FEEDBACK_REF = "Is this information helpful?"  # the redesigned page's only 'job result' reference text


# ---------- config ----------

def load_config():
    """The whole criteria file (LinkedIn's blocks are top level), once `sources: linkedin: enabled` is checked (opt-in, D17)."""
    return common.source_cfg("linkedin", block=False)


def find_search(cfg, name):
    return common.find_search(cfg, name, "LinkedIn")


def tool_args(s):
    """search_jobs arguments from a merged search entry; lists become comma-separated (applicant/criteria/README.md)."""
    keys = ("keywords", "location", "work_type", "experience_level", "job_type", "date_posted", "max_pages", "sort_by",
            "easy_apply")
    return {k: ",".join(s[k]) if isinstance(s[k], list) else s[k] for k in keys if k in s and s[k] not in (None, "")}


# ---------- MCP over stdio (one place) ----------

class Client:
    """Minimal MCP stdio client: newline-delimited JSON-RPC, one request at a time."""

    def __init__(self):
        spec = json.loads(MCP_JSON.read_text(encoding="utf-8"))["mcpServers"]["linkedin"]
        env = {**os.environ, **spec.get("env", {})}
        self.timeout = int(env.get("TOOL_TIMEOUT", "300")) + 60
        self.proc = subprocess.Popen([spec["command"], *spec.get("args", [])], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=sys.stderr, env=env, text=True, bufsize=1)
        # A reader thread, not select(): select can't see lines already sitting in the text wrapper's buffer.
        self.lines = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()
        self.next_id = 0
        self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "linkedin_fetch.py", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _pump(self):
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)  # server exited

    def send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params):
        self.next_id += 1
        rid = self.next_id
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            left = deadline - time.monotonic()
            try:
                line = self.lines.get(timeout=max(left, 0.001))
            except queue.Empty:
                raise Stop(f"no reply to {method} within {self.timeout}s")
            if line is None:
                raise Stop(f"linkedin server exited during {method} (another session holding the browser?)")
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if "method" in msg and "id" in msg:  # a request from the server (roots, sampling): decline it
                self.send({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "not supported"}})
                continue
            if msg.get("id") != rid:
                continue
            if "error" in msg:
                raise Stop(f"{method} failed: {msg['error'].get('message', msg['error'])}")
            return msg["result"]

    def call(self, tool, args):
        """Return the tool's JSON result; a tool error stops the run."""
        res = self.request("tools/call", {"name": tool, "arguments": args})
        text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        if res.get("isError"):
            raise Stop(f"{tool} returned an error: {text[:300]}")
        if isinstance(res.get("structuredContent"), dict) and "sections" in res["structuredContent"]:
            return res["structuredContent"]
        try:
            return json.loads(text)
        except ValueError:
            raise Stop(f"{tool} returned non-JSON text: {text[:300]}")

    def close(self):
        try:
            self.request("tools/call", {"name": "close_session", "arguments": {}})
        except Stop:
            pass
        finally:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()


_last_end = time.monotonic()  # starting at load paces the first call too, across back-to-back runs


def paced(client, delay, tool, args):
    global _last_end
    wait = delay - (time.monotonic() - _last_end)
    if wait > 0:
        time.sleep(wait)
    try:
        return client.call(tool, args)
    finally:
        _last_end = time.monotonic()


# ---------- parsing ----------

def challenged(text):
    low = text.lower()
    return next((m for m in CHALLENGE if m in low), None)


def parse_search(result):
    """Rows {id, title, company, location, age, promoted} in result order. The reference text is the title, sometimes
    cut short; the result text lists each card as title, company, location, then badges and age."""
    text = (result.get("sections") or {}).get("search_results", "")
    lines = [ln.strip() for ln in text.split("\n")]
    refs = []
    for r in (result.get("references") or {}).get("search_results", []):
        m = re.search(r"/jobs/view/(\d+)", r.get("url", ""))
        if r.get("kind") == "job" and r.get("context") == "job result" and m:
            refs.append((m.group(1), (r.get("text") or "").strip()))
    promoted = {str(x) for x in result.get("promoted_job_ids") or []}
    if not any(t and not t.startswith(FEEDBACK_REF) for _, t in refs):
        return parse_redesigned(result, lines, promoted)
    rows, i = [], 0
    for n, (jid, ref_title) in enumerate(refs):
        k = i
        while k < len(lines) and not (ref_title and lines[k].startswith(ref_title)):
            k += 1
        if k + 2 >= len(lines):
            rows.append({"id": jid, "title": ref_title, "company": "", "location": "", "age": "", "promoted": jid in promoted})
            continue
        nxt = refs[n + 1][1] if n + 1 < len(refs) else None
        age = ""
        for ln in lines[k + 3:k + 12]:
            if nxt and ln.startswith(nxt):
                break
            if AGE.match(ln):
                age = ln
                break
        rows.append({"id": jid, "title": lines[k], "company": lines[k + 1], "location": lines[k + 2], "age": age,
                     "promoted": jid in promoted})
        i = k + 3
    have = {r["id"] for r in rows}
    for jid in (str(x) for x in result.get("job_ids") or []):  # an id the references lack: keep it, unlabeled
        if jid not in have:
            rows.append({"id": jid, "title": "", "company": "", "location": "", "age": "", "promoted": jid in promoted})
    return rows


def parse_redesigned(result, lines, promoted):
    """The /jobs/search-results page (2026-10-21): its cards have no permalink, so the references carry no titles.
    The text lists the cards in job_ids order, one block per card between badge lines: title (sometimes first as
    'Selected, <title>' or '<title> (Verified job)'), company, location. A location with no work type is normal: the
    page ignores the location filter and mixes in local on-site jobs. Each page opens with '<n> results' and the
    account's area, which is skipped. If the count of cards differs from job_ids, rows stay unlabeled."""
    ids = [str(x) for x in result.get("job_ids") or []]
    cards, ages, cur, after_count = [], [], [], False
    for ln in (ln for ln in lines if ln):
        if after_count:  # the area line under '<n> results'
            after_count = False
        elif BADGE.match(ln) or AGE.match(ln):
            after_count = ln.endswith(" results")
            if cur:
                cards.append(cur)
                ages.append("")
                cur = []
            if AGE.match(ln) and ages and not ages[-1]:
                ages[-1] = ln
        else:
            cur.append(ln)
    if cur:
        cards.append(cur)
        ages.append("")
    for c in cards:
        head = c[0].removeprefix("Selected, ").removesuffix(" (Verified job)")
        if len(c) > 1 and head == c[1]:
            del c[0]
    if len(cards) != len(ids) or any(len(c) < 3 for c in cards):
        return [{"id": j, "title": "", "company": "", "location": "", "age": "", "promoted": j in promoted} for j in ids]
    return [{"id": j, "title": c[0], "company": c[1], "location": c[2], "age": a, "promoted": j in promoted}
            for j, c, a in zip(ids, cards, ages)]


def parse_job(result, retrieved_at):
    """Note fields and body from a get_job_details result. `verdict` 'ok' means stageable.
    The body is the text between the 'About the job' line and LinkedIn's '… more' line, verbatim apart from trailing
    spaces trimmed and runs of blank lines folded to one."""
    text = (result.get("sections") or {}).get("job_posting", "")
    start = text.find("\nAbout the job\n")
    if start < 0:
        hit = challenged(text)
        return {"verdict": f"stop: '{hit}' page" if hit else "refuse: no 'About the job' section", "fields": {}, "body": None}
    hit = challenged(text[:start])
    if hit:
        return {"verdict": f"stop: '{hit}' in the posting header", "fields": {}, "body": None}
    head = [ln.strip() for ln in text[:start].split("\n") if ln.strip()]
    end = text.find("\n… more\n", start)
    raw = text[start + len("\nAbout the job\n"): end if end > 0 else len(text)]
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(ln.rstrip() for ln in raw.split("\n"))).strip("\n")
    meta = head[2].split(" · ") if len(head) > 2 else []
    age = next((m for m in meta[1:] if AGE.match(m)), "")
    applicants = next((m for m in meta[1:] if "applicant" in m or "clicked apply" in m), "")
    work = next((h for h in head[3:12] if h in ("Remote", "Hybrid", "On-site")), "")
    posted = ""
    if age:
        n, unit = AGE.match(age).groups()
        posted = (retrieved_at - dt.timedelta(days=int(n) * UNIT_DAYS[unit])).strftime("%Y-%m-%d")
    fields = {
        "company": head[0] if head else "",
        "title": head[1] if len(head) > 1 else "",
        "location": meta[0] if meta else "",
        "work_type": {"Remote": "remote", "Hybrid": "hybrid", "On-site": "onsite"}.get(work, ""),
        "posted": posted,
        "posted_raw": age,
        "over100": applicants.startswith("Over 100"),
    }
    if end < 0:
        verdict = "refuse: no '… more' line after the description (layout change?)"
    elif not body:
        verdict = "refuse: empty description"
    elif not (fields["company"] and fields["title"]):
        verdict = "refuse: no company or title in the header"
    else:
        verdict = "ok"
    return {"verdict": verdict, "fields": fields, "body": body}


def build_note(job_id, f, retrieved_at, body, search):
    head = [
        "---",
        "type: linkedin-job",
        f"job_id: {q(str(job_id))}",
        f"url: https://www.linkedin.com/jobs/view/{job_id}/",
        f"title: {q(f['title'])}",
        f"company: {q(f['company'])}",
        f"location: {q(f['location']) if f['location'] else ''}".rstrip(),
        f"work_type: {f['work_type']}".rstrip(),
        f"retrieved_at: {retrieved_at.strftime('%Y-%m-%dT%H:%M:%S')}",
        f"posted: {f['posted']}".rstrip(),
        f"posted_raw: {q(f['posted_raw']) if f['posted_raw'] else ''}".rstrip(),
        f"source_search: {q(search)}",
        *(["over100: true"] if f.get("over100") else []),  # the header said 'Over 100 applicants': the fold sets medium priority
        "---",
    ]
    return "\n".join(head) + f"\n\n# {f['title']} — {f['company']}\n\n{body}\n"


# ---------- commands ----------

def record(name, s, rows, warning, now):
    esc = lambda v: str(v).replace("|", "\\|")
    crit = [f"  {k}: {json.dumps(v, ensure_ascii=False)}" for k, v in s.items() if k != "name"]
    body = [f"| {r['id']} | {esc(r['title'])} | {esc(r['company'])} | {esc(r['location'])} | {r['age']} | "
            f"{'yes' if r['promoted'] else ''} |" for r in rows]
    return "\n".join([
        "---", "type: linkedin-search-run", f"search_name: {q(name)}", f"run_at: {now.strftime('%Y-%m-%dT%H:%M:%S')}",
        "criteria:", *crit, f"result_count: {len(rows)}", "fetched: []", "---", "",
        f"# {name} — {now.strftime('%Y-%m-%d')}", "",
        *([f"> {warning}", ""] if warning else []),
        "| job_id | title | company | location | age | promoted |", "| --- | --- | --- | --- | --- | --- |",
        *body, ""])


def cmd_search(args):
    cfg = load_config()
    names = [s["name"] for s in cfg.get("searches", [])] if args.all else args.names
    if not names:
        raise Fail("name one or more searches, or pass --all")
    searches = [find_search(cfg, n) for n in names]
    suffix = args.suffix
    if args.incremental:
        inc = cfg.get("incremental") or {}
        if not inc:
            raise Fail("--incremental needs an `incremental:` block in the profile's criteria file (naming.py paths)")
        searches = [{**s, **inc} for s in searches]
        suffix = suffix or "-incremental"
    if args.pages:
        searches = [{**s, "max_pages": args.pages} for s in searches]
    delay = cfg.get("selection", {}).get("fetch_delay_seconds", 8)
    day = dt.datetime.now().strftime("%Y-%m-%d")
    outs = [SEARCHES / f"{day}--{n}{suffix}.md" for n in names]
    if args.write:
        clash = [str(o) for o in outs if o.exists()]
        if clash:
            raise Fail(f"exists, not overwriting: {', '.join(clash)}")
    client = Client()
    try:
        for name, s, out in zip(names, searches, outs):
            res = paced(client, delay, "search_jobs", tool_args(s))
            if args.raw:
                raw = Path(args.raw) / f"search-{name}.json"
                raw.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"saved {raw}")
            text = (res.get("sections") or {}).get("search_results", "")
            if not res.get("job_ids") and challenged(text):
                raise Stop(f"'{challenged(text)}' page on search {name}")
            rows = parse_search(res)
            err = (res.get("section_errors") or {}).get("search_results") or {}
            warning = f"{err.get('error_type')}: {err.get('error_message')}" if err else ""
            ceiling = 25 * s.get("max_pages", 1)
            if len(rows) >= ceiling:  # results are in relevance order, so the cut can drop fresh jobs
                capped = f"capped: {len(rows)} rows fill all {s.get('max_pages', 1)} pages, so results past them were not read."
                warning = f"{warning}\n>\n> {capped}" if warning else capped
                print(f"{name}: {capped}")
            if not args.quiet:
                for r in rows:
                    print(" | ".join([name, r["id"], r["title"] or "-", r["company"] or "-", r["location"] or "-", r["age"] or "-"]))
            print(f"{name}: {len(rows)} jobs" + (f" ({err.get('error_type')})" if err else ""))
            if args.write:
                safe_write(out, record(name, s, rows, warning, dt.datetime.now()), [SEARCHES])
                print(f"wrote {out}")
    finally:
        client.close()
    return 0


def stage_targets(cfg, default, items):
    """[(source_search, item)] from `<search>=<item>` pairs, or bare items under `--search`. Every search must exist."""
    names = {s["name"] for s in cfg.get("searches", [])}
    out = []
    for a in items:
        name, sep, rest = a.partition("=")
        if sep and name in names:
            out.append((name, rest))
        elif default:
            out.append((default, a))
        else:
            raise Fail(f"no search for '{a}': pass --search <name> or write <search>=<item>")
    for name in {n for n, _ in out}:
        find_search(cfg, name)
    return out


def cmd_stage(args):
    cfg = load_config()
    targets = stage_targets(cfg, args.search, args.job_ids)
    sel = cfg.get("selection", {})
    delay, cap = sel.get("fetch_delay_seconds", 8), sel.get("max_fetches_per_run", 50)
    bad = [j for _, j in targets if not JOB_ID.match(j)]
    if bad:
        raise Fail(f"not LinkedIn job ids: {', '.join(bad)}")
    if len(targets) > cap:
        raise Fail(f"{len(targets)} ids exceeds max_fetches_per_run={cap}")
    client = None
    missing_in_a_row = 0
    try:
        for search, job_id in targets:
            dest = INBOX / f"{job_id}.md"
            if dest.exists():
                print(f"{job_id} | - | - | skipped: already staged | -")
                continue
            client = client or Client()
            res = paced(client, delay, "get_job_details", {"job_id": job_id})
            retrieved_at = dt.datetime.now()
            j = parse_job(res, retrieved_at)
            f = j["fields"]
            label = f"{job_id} | {f.get('company') or '-'} | {f.get('title') or '-'}"
            if j["verdict"].startswith("stop: "):
                raise Stop(f"{job_id}: {j['verdict'].removeprefix('stop: ')}")
            if j["verdict"] != "ok":
                print(f"{label} | skipped: {j['verdict'].removeprefix('refuse: ')} | -")
                missing_in_a_row += 1
                if missing_in_a_row >= 2:
                    raise Stop("two postings in a row without a readable description: layout may have changed")
                continue
            missing_in_a_row = 0
            flag = "over100" if f["over100"] else "-"
            words = len(j["body"].split())
            if args.write:
                safe_write(dest, build_note(job_id, f, retrieved_at, j["body"], search), [INBOX])
                print(f"{label} | staged ({words} words) | {flag}")
            else:
                print(f"{label} | would stage ({words} words) | {flag}")
    finally:
        if client:
            client.close()
    return 0


def cmd_check(args):
    bad = False
    for fp in args.files:
        res = json.loads(Path(fp).read_text(encoding="utf-8"))
        sections = res.get("sections") or {}
        if "search_results" in sections:
            rows = parse_search(res)
            blank = sum(1 for r in rows if not (r["title"] and r["company"]))
            ok = bool(rows) and not blank
            print(f"{fp}: search, {len(rows)} jobs, {blank} unlabeled, {'ok' if ok else 'refuse'}")
        elif "job_posting" in sections:
            j = parse_job(res, dt.datetime.now())
            f = j["fields"]
            n = len(j["body"].split()) if j["body"] else 0
            ok = j["verdict"] == "ok"
            print(f"{fp}: {f.get('company', '-')} | {f.get('title', '-')} | {f.get('location', '-')} | "
                  f"{f.get('work_type', '-')} | {f.get('posted_raw', '-')} | {n} words | {j['verdict']}")
        else:
            ok = False
            print(f"{fp}: neither a search_jobs nor a get_job_details result")
        bad |= not ok
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="run saved searches and print/record the returned jobs")
    s.add_argument("names", nargs="*")
    s.add_argument("--all", action="store_true", help="every search in the config")
    s.add_argument("--write", action="store_true", help="save the search records (default: dry run)")
    s.add_argument("--quiet", action="store_true", help="print only the per-search counts (read the shortlist instead)")
    s.add_argument("--suffix", default="", help="appended to each record's file name, e.g. -incremental for a second run in a day")
    s.add_argument("--pages", type=int, help="override max_pages for this run")
    s.add_argument("--raw", metavar="DIR", help="also save each search_jobs result as DIR/search-<name>.json (fixtures for check)")
    s.add_argument("--incremental", action="store_true",
                   help="same-day second pass: apply the config's `incremental:` block; suffix defaults to -incremental")
    g = sub.add_parser("stage", help="fetch job details and stage them in the inbox")
    g.add_argument("--search", help="source_search for bare ids; omit when every id is written <search>=<job_id>")
    g.add_argument("--write", action="store_true", help="write inbox notes (default: dry run)")
    g.add_argument("job_ids", nargs="+", metavar="[search=]job_id")
    c = sub.add_parser("check", help="offline: parse saved tool results")
    c.add_argument("files", nargs="+")
    args = ap.parse_args()
    return common.run({"search": cmd_search, "stage": cmd_stage, "check": cmd_check}, args)


if __name__ == "__main__":
    sys.exit(main())
