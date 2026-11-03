#!/usr/bin/env python3
"""Run the Jobgether searches by script and write their search records, so no search result enters a model's context.

Calls the same public `searchJobs` tool the session used (`.mcp.json`: https://jobgether.com/mcp, no login, D10) as
JSON-RPC over HTTP, 2 seconds between requests (`sources: jobgether: pacing: fetch_delay_seconds`). Listing pages (the
description text) are still read in the operator's Chrome by the job-fetcher: scripted requests to them get 403.
Settings come from the `jobgether:` block of the profile's criteria file. `max_age_days` (not an API parameter) drops
postings older than that many days and stops paging once a page reaches them, since results are sorted by date.

Usage:
    python3 pipeline/scripts/sources/jobgether_fetch.py search jg-ux-designer [jg-content-designer ...] [--write]
    python3 pipeline/scripts/sources/jobgether_fetch.py search --all [--write] [--quiet] [--suffix -pm]
Writes logs/searches/YYYY-MM-DD--<name><suffix>.md (type: jobgether-search-run), one per search that found jobs,
with --write.
Without --write it still calls the API (a free public search) and prints the rows.

Stops the run (exit 1) on an HTTP error status, a network error or a tool error. No retries. Exit 2: usage or config.
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from sources import common  # noqa: E402
from sources.common import Fail, Stop, q  # noqa: E402

ROOT = naming.ROOT
MCP_JSON = naming.MCP_JSON
SEARCHES = naming.SEARCHES
API_ARGS = ("keyword", "jobReferences", "locations", "industries", "contractType", "experience", "remoteType",
            "includeHybrid", "salaryMin", "salaryMax", "currency", "sort", "limit")


class Client:
    """JSON-RPC over HTTP to the Jobgether MCP endpoint, paced: `delay` seconds between the end of one request and
    the start of the next, the first included."""

    def __init__(self, url, delay):
        self.url, self.delay, self.next_id, self.last = url, delay, 0, 0.0
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                "clientInfo": {"name": "jobgether_fetch.py", "version": "1"}})
        self.rpc("notifications/initialized", notify=True)

    def rpc(self, method, params=None, notify=False):
        wait = self.delay - (time.monotonic() - self.last)
        if wait > 0 and not notify:
            time.sleep(wait)
        body = {"jsonrpc": "2.0", "method": method, **({"params": params} if params is not None else {})}
        if not notify:
            self.next_id += 1
            body["id"] = self.next_id
        req = urllib.request.Request(self.url, json.dumps(body).encode(), {
            "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
            "User-Agent": "jobgether_fetch.py (job-search automation, human-paced)"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw, ctype = r.read().decode("utf-8"), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            raise Stop(f"{method}: HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError) as e:
            raise Stop(f"{method}: network error: {e}")
        finally:
            if not notify:
                self.last = time.monotonic()
        if notify or not raw.strip():
            return None
        if "event-stream" in ctype:  # the server may answer as server-sent events; the last data line is the reply
            raw = [ln[5:].strip() for ln in raw.splitlines() if ln.startswith("data:")][-1]
        msg = json.loads(raw)
        if "error" in msg:
            raise Stop(f"{method}: {msg['error'].get('message', msg['error'])}")
        return msg["result"]

    def search(self, args):
        res = self.rpc("tools/call", {"name": "searchJobs", "arguments": args})
        if res.get("isError"):
            text = "".join(c.get("text", "") for c in res.get("content", []))
            raise Stop(f"searchJobs returned an error: {text[:300]}")
        return res.get("structuredContent") or json.loads(res["content"][0]["text"])


def load():
    return common.source_cfg("jobgether")  # `sources: jobgether:`; on unless its `enabled` is false (D17)


def posted_date(job):
    return (job.get("postedAt") or "")[:10]


def run_search(client, s, today):
    """Rows for one merged search entry, newest first, within max_age_days; and the page count."""
    args = {k: s[k] for k in API_ARGS if s.get(k) not in (None, "", [])}
    cutoff = (today - dt.timedelta(days=int(s["max_age_days"]))).isoformat() if s.get("max_age_days") else ""
    rows, pages = [], 0
    for page in range(1, int(s.get("max_pages", 1)) + 1):
        data = client.search({**args, "page": page})
        pages += 1
        jobs = data.get("jobs") or []
        fresh = [j for j in jobs if not cutoff or posted_date(j) >= cutoff]
        rows += fresh
        if len(fresh) < len(jobs) or not (data.get("pagination") or {}).get("hasMore"):
            break
    return rows, pages


def record(name, s, rows, now):
    esc = lambda v: str(v or "").replace("|", "\\|")
    crit = [f"  {k}: {json.dumps(v, ensure_ascii=False)}" for k, v in s.items() if k != "name"]
    table = [f"| {j['id']} | {esc(j.get('title'))} | {esc(j.get('company'))} | {esc(j.get('location'))} | "
             f"{posted_date(j)} | {esc(j.get('salaryRange'))} | {j.get('url', '')} |" for j in rows]
    return "\n".join([
        "---", "type: jobgether-search-run", f"search_name: {q(name)}", f"run_at: {now:%Y-%m-%dT%H:%M:%S}",
        "criteria:", *crit, f"result_count: {len(rows)}", "fetched: []", "---", "",
        f"# {name} — {now:%Y-%m-%d}", "",
        "| job_id | title | company | location | posted | salary | url |", "| --- | --- | --- | --- | --- | --- | --- |",
        *table, ""])


def cmd_search(args):
    jg = load()
    by_name = {s["name"]: s for s in jg["searches"]}
    names = list(by_name) if args.all else args.names
    if not names:
        raise Fail("name one or more searches, or pass --all")
    unknown = [n for n in names if n not in by_name]
    if unknown:
        raise Fail(f"unknown Jobgether search: {', '.join(unknown)} (have: {', '.join(by_name)})")
    day = dt.date.today()
    outs = {n: SEARCHES / f"{day.isoformat()}--{n}{args.suffix}.md" for n in names}
    if args.write:
        clash = [str(o) for o in outs.values() if o.exists()]
        if clash:
            raise Fail(f"exists, not overwriting: {', '.join(clash)}")
    url = json.loads(MCP_JSON.read_text(encoding="utf-8"))["mcpServers"]["jobgether"]["url"]
    delay = common.pacing(jg, "fetch_delay_seconds", 2)
    client = Client(url, delay)
    for n in names:
        s = {**(jg.get("defaults") or {}), **by_name[n]}
        rows, pages = run_search(client, s, day)
        if not args.quiet:
            for j in rows:
                print(" | ".join([n, j["id"], j.get("title") or "-", j.get("company") or "-", posted_date(j) or "-"]))
        print(f"{n}: {len(rows)} jobs ({pages} page{'s' if pages != 1 else ''})")
        if args.write and rows:
            outs[n].write_text(record(n, s, rows, dt.datetime.now()), encoding="utf-8")
            print(f"wrote {outs[n]}")
        elif args.write:  # normal within max_age_days; select_candidates.py refuses a record with no rows
            print(f"no record for {n}: no jobs within max_age_days")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="run saved searches and print/record the returned jobs")
    s.add_argument("names", nargs="*")
    s.add_argument("--all", action="store_true", help="every search in the config")
    s.add_argument("--write", action="store_true", help="save the search records (default: print only)")
    s.add_argument("--quiet", action="store_true", help="print only the per-search counts")
    s.add_argument("--suffix", default="", help="appended to each record's file name, e.g. -pm for a second run in a day")
    args = ap.parse_args()
    return common.run({"search": cmd_search}, args)


if __name__ == "__main__":
    sys.exit(main())
