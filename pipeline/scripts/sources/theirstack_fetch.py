#!/usr/bin/env python3
"""Read TheirStack (paid job API aggregating job boards and company career pages); stage job descriptions verbatim.

The API returns the full description with each search result, and bills a credit per job returned. So `search` is the
only command that calls it: it saves the raw response beside the search record
(logs/searches/YYYY-MM-DD--<name>.json), and `stage` builds logs/inbox/<id>.md notes from that saved response
with no network and no credits. `check` runs the parser on saved responses.
Settings come from the `theirstack:` block of the profile's criteria file. The key is THEIRSTACK_API_KEY, from
the environment or .env. Why: context/decisions.md D24.

Job ids: a job TheirStack read from LinkedIn uses the LinkedIn id, and one read from Indeed uses the Indeed jk, so both
dedupe against existing tasks. Every other job is `ts<id>` (TheirStack's id, prefixed so it never collides).

Usage:
    python3 pipeline/scripts/sources/theirstack_fetch.py search ts-ux-remote-us            # dry run: print the request, no call, no credits
    python3 pipeline/scripts/sources/theirstack_fetch.py search ts-ux-remote-us --write    # call the API, save response + search record
    python3 pipeline/scripts/sources/theirstack_fetch.py stage [--write] ts-ux-remote-us=ts123456789 ...
    python3 pipeline/scripts/sources/theirstack_fetch.py check logs/searches/*--ts-*.json   # offline

Stops the run (exit 1) on 401/402/403/429/5xx or a network error. No retries.
"""
import argparse
import collections
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from sources import common  # noqa: E402
from sources.common import Fail, Stop, q, safe_write  # noqa: E402

ROOT = naming.ROOT
INBOX = naming.INBOX
SEARCHES = naming.SEARCHES

URL = "https://api.theirstack.com/v1/jobs/search"
TIMEOUT = 60
LINKEDIN = re.compile(r"linkedin\.com/jobs/view/(?:[^/?#]*-)?(\d{6,})")
INDEED = re.compile(r"indeed\.com/.*[?&]jk=([0-9a-f]{16})")


# ---------- config ----------

def load_cfg():
    """The `theirstack:` block, once `sources: theirstack: enabled` is checked. `check` never reads the config."""
    return common.source_cfg("theirstack")


def find_search(cfg, name):
    return common.find_search(cfg, name, "theirstack")


def body_for(s):
    """Request body: every search key except `name`, empty values left out."""
    b = {k: v for k, v in s.items() if k != "name" and v not in (None, "", [])}
    if not any(k.startswith("posted_at_") for k in b):
        raise Fail("a search needs a posted_at_* filter (the API requires one, and it bounds the cost)")
    return b


# ---------- network ----------

def call(body):
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "Authorization": f"Bearer {common.api_key('THEIRSTACK_API_KEY')}", "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            usage = {k: v for k, v in r.headers.items() if k.lower() in ("ratelimit-limit", "ratelimit-remaining")}
            return json.loads(r.read().decode("utf-8")), usage
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")[:300]
        if e.code in (401, 402, 403, 429) or e.code >= 500:
            raise Stop(f"HTTP {e.code}: {text}")
        raise Fail(f"HTTP {e.code}: {text}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Stop(f"network error: {e}")


# ---------- parsing ----------

def jobs_of(data):
    """The job list of a saved response (wrapped by `search`) or a raw API response."""
    jobs = data.get("jobs", data.get("data")) if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        raise Fail("response is not a list of jobs")
    return jobs


def parse_job(j):
    """Note fields and body for one API job; `verdict` 'ok' means stageable."""
    src = j.get("source_url") or ""
    if m := LINKEDIN.search(src):
        jid, url, origin = m.group(1), f"https://www.linkedin.com/jobs/view/{m.group(1)}", "linkedin"
    elif m := INDEED.search(src):
        jid, url, origin = m.group(1), f"https://www.indeed.com/viewjob?jk={m.group(1)}", "indeed"
    else:
        jid, url = f"ts{j.get('id')}", j.get("final_url") or j.get("url") or src
        origin = re.sub(r"^www\.", "", urllib.parse.urlsplit(src).hostname or "") if src else ""
    remote, hybrid = j.get("remote"), j.get("hybrid")
    work = "remote" if remote else "hybrid" if hybrid else "onsite" if remote is False and hybrid is False else ""
    f = {
        "job_id": jid,
        "url": url,
        "title": (j.get("job_title") or "").strip(),
        "company": ((j.get("company_object") or {}).get("name") or j.get("company") or "").strip(),
        "location": (j.get("short_location") or j.get("location") or j.get("country") or "").strip(),
        "work_type": work,
        "posted": str(j.get("date_posted") or "")[:10],
        "source": origin,
    }
    body = (j.get("description") or "").strip()
    if not body:
        verdict = "refuse: no description"
    elif not all(f[k] for k in ("title", "company", "posted", "url")) or jid in ("tsNone", "ts"):
        verdict = "refuse: lacks id, title, company, date_posted or url"
    else:
        verdict = "ok"
    return {"fields": f, "body": body, "verdict": verdict}


def build_note(f, retrieved_at, body, search):
    head = [
        "---",
        "type: theirstack-job",
        f"job_id: {q(f['job_id'])}",
        f"url: {q(f['url'])}",
        f"title: {q(f['title'])}",
        f"company: {q(f['company'])}",
        f"location: {q(f['location']) if f['location'] else ''}".rstrip(),
        f"work_type: {f['work_type']}".rstrip(),
        f"retrieved_at: {retrieved_at}",
        f"posted: {f['posted']}",
        f"source_search: {q(search)}",
        "---",
    ]
    return "\n".join(head) + f"\n\n# {f['title']} — {f['company']}\n\n{body}\n"


# ---------- commands ----------

def cmd_search(args):
    cfg = load_cfg()
    body = body_for(find_search(cfg, args.name))
    print(f"POST {URL}")
    for k, v in body.items():
        print(f"  {k} = {json.dumps(v)}")
    if not args.write:
        print("dry run: no call made, no credits used. Pass --write to call the API.")
        return 0
    now = dt.datetime.now()
    stem = f"{now.strftime('%Y-%m-%d')}--{args.name}"
    out, raw = SEARCHES / f"{stem}.md", SEARCHES / f"{stem}.json"
    if out.exists() or raw.exists():
        raise Fail(f"{out.name} or {raw.name} exists; not calling the API again today")
    data, usage = call(body)
    fetched_at = now.strftime("%Y-%m-%dT%H:%M:%S")
    jobs = jobs_of(data)
    capped = len(jobs) >= int(body.get("limit", 0) or 10**9)
    safe_write(raw, json.dumps({"fetched_at": fetched_at, "request": body, "usage": usage,
                                "metadata": data.get("metadata"), "capped": capped, "jobs": jobs}, ensure_ascii=False, indent=1), [SEARCHES])
    rows = [parse_job(j) for j in jobs]
    esc = lambda v: str(v).replace("|", "\\|")
    for r in rows:
        f = r["fields"]
        print(" | ".join([f["job_id"], f["company"], f["title"], f["work_type"], f["location"], f["posted"], f["source"]])
              + ("" if r["verdict"] == "ok" else f" | {r['verdict']}"))
    print(f"{len(rows)} returned · usage: {usage or 'no rate-limit headers'}")
    if capped:
        print(f"WARNING: returned exactly its limit ({body['limit']}); the source likely had more. A later call will report the overflow as new.")
    crit = [f"  {k}: {q(v)}" for k, v in body.items()]
    text = "\n".join([
        "---", "type: theirstack-search-run", f"search_name: {q(args.name)}", f"run_at: {fetched_at}",
        "criteria:", *crit, f"result_count: {len(rows)}", f"capped: {str(capped).lower()}", f"response: {q(raw.name)}",
        "fetched: []", "---", "",
        f"# {args.name} — {now.strftime('%Y-%m-%d')}", "",
        "| job_id | title | company | location | work_type | posted | source | url |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        *[f"| {r['fields']['job_id']} | " + " | ".join(esc(r["fields"][k]) for k in
          ("title", "company", "location", "work_type", "posted", "source", "url")) + " |" for r in rows], ""])
    safe_write(out, text, [SEARCHES])
    print(f"wrote {out}\nwrote {raw}")
    return 0


def latest_response(search):
    found = sorted(SEARCHES.glob(f"????-??-??--{search}.json"))
    if not found:
        raise Fail(f"no saved response for '{search}': run `search {search} --write` first")
    return found[-1]


def cmd_stage(args):
    cfg = load_cfg()
    targets = []
    for a in args.ids:
        search, sep, jid = a.partition("=")
        if not sep:
            raise Fail(f"write <search>=<job_id>: {a}")
        find_search(cfg, search)
        targets.append((search, jid))
    cache = {}
    for search, jid in targets:
        if search not in cache:
            path = latest_response(search)
            data = json.loads(path.read_text(encoding="utf-8"))
            cache[search] = (data.get("fetched_at", ""), {(p := parse_job(j))["fields"]["job_id"]: p for j in jobs_of(data)})
        fetched_at, by_id = cache[search]
        dest = INBOX / f"{jid}.md"
        if dest.exists():
            print(f"{jid} | - | - | skipped: already staged")
            continue
        j = by_id.get(jid)
        if not j:
            print(f"{jid} | - | - | skipped: not in the saved {search} response")
            continue
        f = j["fields"]
        label = f"{jid} | {f['company'] or '-'} | {f['title'] or '-'}"
        if j["verdict"] != "ok":
            print(f"{label} | skipped: {j['verdict'].removeprefix('refuse: ')}")
            continue
        n = len(j["body"].split())
        if args.write:
            safe_write(dest, build_note(f, fetched_at, j["body"], search), [INBOX])
            print(f"{label} | staged ({n} words)")
        else:
            print(f"{label} | would stage ({n} words)")
    return 0


def cmd_check(args):
    bad = False
    for fp in args.files:
        jobs = jobs_of(json.loads(Path(fp).read_text(encoding="utf-8")))
        rows = [parse_job(j) for j in jobs]
        ok = sum(r["verdict"] == "ok" for r in rows)
        print(f"== {fp}: {len(rows)} jobs, {ok} stageable")
        for r in rows[: args.show]:
            f = r["fields"]
            print("  " + " | ".join([f["job_id"], f["company"], f["title"], f["work_type"] or "-", f["location"] or "-",
                                     f["posted"], f["source"] or "-", f"{len(r['body'].split())} words", r["verdict"]]))
        for v, n in collections.Counter(r["verdict"] for r in rows if r["verdict"] != "ok").items():
            print(f"  {n} × {v}")
        bad |= ok == 0
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="call the API for one search; save the response and a search record")
    s.add_argument("name")
    s.add_argument("--write", action="store_true", help="make the paid call (default: print the request only)")
    g = sub.add_parser("stage", help="stage jobs from the saved response (no network)")
    g.add_argument("--write", action="store_true", help="write inbox notes (default: dry run)")
    g.add_argument("ids", nargs="+", metavar="search=job_id")
    c = sub.add_parser("check", help="offline: run the parser on saved responses")
    c.add_argument("--show", type=int, default=5, help="rows to print per file")
    c.add_argument("files", nargs="+")
    args = ap.parse_args()
    return common.run({"search": cmd_search, "stage": cmd_stage, "check": cmd_check}, args)


if __name__ == "__main__":
    sys.exit(main())
