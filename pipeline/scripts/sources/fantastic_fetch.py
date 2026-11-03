#!/usr/bin/env python3
"""Read Fantastic.jobs (paid job API: company ATS career pages and job boards); stage job descriptions verbatim.

The API returns the full description with each search result, and bills per job returned. So `search` is the
only command that calls it: it saves the raw response beside the search record
(logs/searches/YYYY-MM-DD--<name>.json), and `stage` builds logs/inbox/<id>.md notes from that saved response
with no network and no credits. `check` runs the parser on saved responses (or the vendor's sample files).
Settings come from the `fantastic:` block of the profile's criteria file. The key is FANTASTIC_JOBS_API_KEY, from
the environment or .env. Why: context/decisions.md D23.

Job ids: ATS rows are `fj<id>` (Fantastic's internal id, prefixed so it never collides with a LinkedIn id);
job-board rows from LinkedIn use the `linkedin_id`, so they dedupe against LinkedIn tasks.

Usage:
    python3 pipeline/scripts/sources/fantastic_fetch.py search fj-ux-remote-us            # dry run: print the request, no call, no credits
    python3 pipeline/scripts/sources/fantastic_fetch.py search fj-ux-remote-us --write    # call the API, save response + search record
    python3 pipeline/scripts/sources/fantastic_fetch.py stage [--write] fj-ux-remote-us=fj2424611828 ...
    python3 pipeline/scripts/sources/fantastic_fetch.py check logs/fixtures/fantastic/*.json   # offline

Stops the run (exit 1) on 401/403/429/5xx or a network error. No retries.
"""
import argparse
import collections
import datetime as dt
import json
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

BASE = "https://data.fantastic.jobs/v1"
ENDPOINTS = {"ats": "active-ats", "jb": "active-jb"}
TIMEOUT = 60
WORK_TYPE = {"Remote Solely": "remote", "Remote OK": "remote", "Hybrid": "hybrid", "On-site": "onsite"}


# ---------- config ----------

def load_cfg():
    """The `fantastic:` block, once `sources: fantastic: enabled` is checked. `check` never reads the config."""
    return common.source_cfg("fantastic")


def find_search(cfg, name):
    return common.find_search(cfg, name, "fantastic")


def cutoff(s):
    """UTC cutoff for date_posted from `max_age_hours`, or None. date_posted is UTC, naive."""
    h = s.get("max_age_hours")
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(hours=h) if h else None


def params_for(s, cut=None):
    """Query parameters: every search key except the script's own; lists become comma-separated.

    With a cutoff, date_posted_gte is the start of the cutoff's day, so date-only postings (midnight) from that day
    still come back; too_old() then applies the exact cutoff."""
    own = {"name", "endpoint", "max_age_hours"}
    p = {k: ",".join(map(str, v)) if isinstance(v, list) else str(v).lower() if isinstance(v, bool) else str(v)
         for k, v in s.items() if k not in own and v not in (None, "", [])}
    p.setdefault("description_format", "text")
    if cut:
        p["date_posted_gte"] = cut.strftime("%Y-%m-%dT00:00:00")
    return p


def too_old(j, cut):
    """Posted before the cutoff. A date-only posting (time 00:00:00) is compared by date, not as midnight."""
    try:
        posted = dt.datetime.fromisoformat(str(j.get("date_posted")))
    except ValueError:
        return False  # unreadable: keep, and let stage refuse it if the date is missing
    if posted.time() == dt.time(0):
        return posted.date() < cut.date()
    return posted < cut


# ---------- network ----------

def call(endpoint, params):
    url = f"{BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {common.api_key('FANTASTIC_JOBS_API_KEY')}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            usage = {k: v for k, v in r.headers.items() if k.lower().startswith("x-api-")}
            return json.loads(r.read().decode("utf-8")), usage
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        if e.code in (401, 403, 429) or e.code >= 500:
            raise Stop(f"HTTP {e.code} on {endpoint}: {body}")
        raise Fail(f"HTTP {e.code} on {endpoint}: {body}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Stop(f"network error on {endpoint}: {e}")


# ---------- parsing ----------

def jobs_of(data):
    """The job list of a saved response (wrapped by `search`) or a raw API/sample array."""
    jobs = data.get("jobs") if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        raise Fail("response is not a list of jobs")
    return jobs


def parse_job(j):
    """Note fields and body for one API job; `verdict` 'ok' means stageable."""
    li = j.get("linkedin_id")
    if j.get("source_type") == "jobboard" and j.get("source") == "linkedin" and li:
        jid, url = str(li), f"https://www.linkedin.com/jobs/view/{li}"
    else:
        jid, url = f"fj{j.get('id')}", j.get("url") or ""
    arr = j.get("ai_work_arrangement") or ""
    f = {
        "job_id": jid,
        "url": url,
        "title": (j.get("title") or "").strip(),
        "company": (j.get("organization") or "").strip(),
        "location": "; ".join(j.get("locations_derived") or []),
        "work_type": WORK_TYPE.get(arr, ""),
        "arrangement": arr,
        "posted": str(j.get("date_posted") or "")[:10],
        "source": j.get("source") or "",
    }
    body = (j.get("description_text") or "").strip()
    if not body:
        verdict = "refuse: no description_text (was description_format=text sent?)"
    elif not all(f[k] for k in ("title", "company", "posted", "url")) or jid in ("fjNone", "fj"):
        verdict = "refuse: lacks id, title, company, date_posted or url"
    else:
        verdict = "ok"
    return {"fields": f, "body": body, "verdict": verdict}


def build_note(f, retrieved_at, body, search):
    head = [
        "---",
        "type: fantastic-job",
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
    s = find_search(cfg, args.name)
    endpoint = ENDPOINTS[s.get("endpoint", "ats")]
    cut = cutoff(s)
    params = params_for(s, cut)
    print(f"GET {BASE}/{endpoint}")
    for k, v in params.items():
        print(f"  {k} = {v}")
    if cut:
        print(f"  (script) drop jobs posted before {cut.strftime('%Y-%m-%dT%H:%M')} UTC")
    if not args.write:
        print("dry run: no call made, no credits used. Pass --write to call the API.")
        return 0
    now = dt.datetime.now()
    stem = f"{now.strftime('%Y-%m-%d')}--{args.name}"
    out, raw = SEARCHES / f"{stem}.md", SEARCHES / f"{stem}.json"
    if out.exists() or raw.exists():
        raise Fail(f"{out.name} or {raw.name} exists; not calling the API again today")
    jobs, usage = call(endpoint, params)
    fetched_at = now.strftime("%Y-%m-%dT%H:%M:%S")
    jobs = jobs_of(jobs)
    capped = len(jobs) >= int(params.get("limit", 0) or 10**9)
    old = [j for j in jobs if cut and too_old(j, cut)]
    jobs = [j for j in jobs if j not in old]
    for j in old:
        print(f"{parse_job(j)['fields']['job_id']} | {j.get('organization')} | {j.get('title')} | dropped: posted {j.get('date_posted')}")
    safe_write(raw, json.dumps({"fetched_at": fetched_at, "endpoint": endpoint, "params": params, "usage": usage,
                                "dropped_old": [[j.get("id"), j.get("date_posted")] for j in old],
                                "capped": capped, "jobs": jobs}, ensure_ascii=False, indent=1), [SEARCHES])
    rows = [parse_job(j) for j in jobs]
    esc = lambda v: str(v).replace("|", "\\|")
    for r in rows:
        f = r["fields"]
        print(" | ".join([f["job_id"], f["company"], f["title"], f["arrangement"], f["location"], f["posted"], f["source"]])
              + ("" if r["verdict"] == "ok" else f" | {r['verdict']}"))
    print(f"{len(rows) + len(old)} returned, {len(old)} dropped as too old · usage: {usage or 'no x-api headers'}")
    if capped:
        print(f"WARNING: returned exactly its limit ({params['limit']}); the source likely had more. A later call will report the overflow as new.")
    crit = [f"  {k}: {q(v)}" for k, v in params.items() if k != "description_format"]
    text = "\n".join([
        "---", "type: fantastic-search-run", f"search_name: {q(args.name)}", f"run_at: {fetched_at}",
        f"endpoint: {endpoint}", "criteria:", *crit, f"result_count: {len(rows)}", f"capped: {str(capped).lower()}", f"response: {q(raw.name)}",
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
            print("  " + " | ".join([f["job_id"], f["company"], f["title"], f["arrangement"] or "-", f["location"] or "-",
                                     f["posted"], f"{len(r['body'].split())} words", r["verdict"]]))
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
    c = sub.add_parser("check", help="offline: run the parser on saved responses or sample files")
    c.add_argument("--show", type=int, default=5, help="rows to print per file")
    c.add_argument("files", nargs="+")
    args = ap.parse_args()
    return common.run({"search": cmd_search, "stage": cmd_stage, "check": cmd_check}, args)


if __name__ == "__main__":
    sys.exit(main())
