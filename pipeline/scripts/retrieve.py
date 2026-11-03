#!/usr/bin/env python3
"""One command per retrieval step: run every enabled source's search, or stage every approved pick (D21, plan §1.2-1.3).

`search` runs each enabled script source's searches concurrently (one worker per source; within a worker the
commands run one after another with that source's delay between them), merges the new titles, runs Select over the
records this run wrote (reading the day's other records too, so a second call, such as `--sources linkedin` after the fast sources, lists only what is new), and prints one shortlist grouped by source. It saves the shortlist as a TSV for `stage`.
`stage` sends each approved pick to its source's stage command, LinkedIn in its own process beside the others, then
runs the fold dry run. Picks for Chrome sources (Jobgether, Indeed) are printed as job-fetcher lines instead.

Every source script keeps its own pacing, caps and hard stops. A script that exits 1 is a hard stop: the other
running scripts are terminated, no later command starts, and this exits 1. No retries.

Usage:
    python3 pipeline/scripts/retrieve.py search                        # plan: the commands it would run; no network
    python3 pipeline/scripts/retrieve.py search --write                # run free sources, write records, print the shortlist
    python3 pipeline/scripts/retrieve.py search --write --paid         # also make the paid Fantastic and TheirStack calls
    python3 pipeline/scripts/retrieve.py search --write --incremental  # LinkedIn's same-day second pass (`incremental:`)
    python3 pipeline/scripts/retrieve.py search --write --sources jobgether,uiux
    python3 pipeline/scripts/retrieve.py stage --shortlist <tsv> [--only <id> ...] [--except <id> ...]   # plan
    python3 pipeline/scripts/retrieve.py stage --write --shortlist <tsv> [--only ...] [--except ...]
    python3 pipeline/scripts/retrieve.py stage --write linkedin:design-manager=4300000001 uiux:uiux-remote-us=/job/123-x ...

Without --write nothing is called: LinkedIn's and the board's own dry runs still fetch, so they are never run as a
plan. Logs and the shortlist go to logs/runs/<timestamp>/.
"""
import argparse
import csv
import datetime as dt
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml

import naming
from sources.common import block, enabled, pacing
from tracking.select_candidates import select, source_of

ROOT = naming.ROOT
SCRIPTS = naming.SCRIPTS
SOURCE_DIR, TRACKING_DIR = SCRIPTS / "sources", SCRIPTS / "tracking"
CONFIG = naming.CRITERIA
SEARCHES = naming.SEARCHES
RUNS = naming.RUNS
PY = sys.executable
SCRIPTED = ("linkedin", "jobgether", "uiux", "fantastic", "theirstack")
PAID = ("fantastic", "theirstack")
CHROME = ("jobgether", "indeed")  # listing pages or results read in the operator's Chrome by the job-fetcher
SHORTLIST_COLS = ("source", "search", "job_id", "company", "title", "location", "where", "note")


def load_cfg():
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}


def names(cfg, src):
    return [s["name"] for s in block(cfg, src).get("searches", [])]


def delay(cfg, src):
    return pacing(block(cfg, src), "fetch_delay_seconds", 5)


def script(folder, name):
    return [PY, str(folder / name)]


class Run:
    """Workers, one per source, each running its commands in order. The first exit 1 stops every worker."""

    def __init__(self, logdir):
        self.logdir, self.stop, self.lock = logdir, threading.Event(), threading.Lock()
        self.procs, self.results = set(), {}

    def worker(self, src, cmds, gap):
        out, code, started = [], 0, time.monotonic()
        for i, cmd in enumerate(cmds):
            if i and gap:  # pacing between two processes of one source, which the scripts can't see
                self.stop.wait(gap)
            if self.stop.is_set():
                out.append("not started: the run was stopped")
                break
            p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            with self.lock:
                self.procs.add(p)
            text, _ = p.communicate()
            with self.lock:
                self.procs.discard(p)
            out += text.rstrip("\n").splitlines()
            code = p.returncode
            if code == 1 or code < 0:
                if not self.stop.is_set():
                    self.stop.set()
                    with self.lock:
                        for other in self.procs:
                            # SIGINT, not SIGTERM: Python raises KeyboardInterrupt, so a script's `finally` runs
                            # (linkedin_fetch.py closes its browser session there).
                            other.send_signal(signal.SIGINT)
                break
        (self.logdir / f"{src}.log").write_text("\n".join(out) + "\n", encoding="utf-8")
        self.results[src] = (code, time.monotonic() - started, out)

    def run(self, jobs):
        threads = [threading.Thread(target=self.worker, args=(s, c, g)) for s, (c, g) in jobs.items()]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return self.results


def report(results, stopped):
    for src, (code, secs, out) in results.items():
        state = "ok" if code == 0 else ("STOPPED" if code == 1 else ("terminated" if code < 0 else f"exit {code}"))
        if "not started: the run was stopped" in out:
            state = "cut short"
        last = next((ln for ln in reversed(out) if ln.strip()), "")
        print(f"[{src}] {state}, {secs:.0f}s: {last[:160]}")
    if stopped:
        print("RUN STOPPED: a source hit a hard stop (exit 1). Read its log; don't retry.", file=sys.stderr)


def show(jobs, logdir=None):
    for src, (cmds, gap) in jobs.items():
        for c in cmds:
            print(f"[{src}] " + " ".join(a if " " not in a else repr(a) for a in c[1:]))
        if gap and len(cmds) > 1:
            print(f"[{src}]   ({gap}s between commands)")


def cmd_search(args):
    cfg = load_cfg()
    want = args.sources.split(",") if args.sources else list(SCRIPTED)
    jobs, notes = {}, []
    for src in want:
        if src not in SCRIPTED:
            notes.append(f"{src}: not scripted (Indeed is searched in Chrome: runbook)")
            continue
        if not enabled(cfg, src):
            notes.append(f"{src}: off in `sources:`")
            continue
        if src in PAID and not args.paid:
            notes.append(f"{src}: paid, skipped (pass --paid to make the call)")
            continue
        if src == "linkedin":
            cmds = [script(SOURCE_DIR, "linkedin_fetch.py") + ["search", "--all", "--write", "--quiet"]
                    + (["--incremental"] if args.incremental else [])]
        elif src == "jobgether":
            cmds = [script(SOURCE_DIR, "jobgether_fetch.py") + ["search", "--all", "--write", "--quiet"]]
        elif src == "uiux":
            cmds = [script(SOURCE_DIR, "uiux_board.py") + ["search", n, "--write"] for n in names(cfg, src)]
        else:
            cmds = [script(SOURCE_DIR, f"{src}_fetch.py") + ["search", n, "--write"] for n in names(cfg, src)]
        jobs[src] = (cmds, delay(cfg, src) if src == "uiux" else 0)
    for n in notes:
        print(f"note: {n}")
    if not jobs:
        print("nothing to run")
        return 0
    if not args.write:
        show(jobs)
        print("plan only; pass --write to run (and --paid for the paid sources)")
        return 0

    stamp = dt.datetime.now()
    logdir = RUNS / f"{stamp:%Y-%m-%d-%H%M%S}-search"
    logdir.mkdir(parents=True, exist_ok=True)
    before = {p: p.stat().st_mtime_ns for p in SEARCHES.glob("*.md")}
    run = Run(logdir)
    results = run.run(jobs)
    report(results, run.stop.is_set())
    if run.stop.is_set():
        return 1
    day = sorted(SEARCHES.glob(f"{stamp:%Y-%m-%d}--*.md"))
    # Only this call's sources: a LinkedIn call running beside the fast sources writes records of its own meanwhile.
    records = [p for p in day if before.get(p) != p.stat().st_mtime_ns and source_of(p) in jobs]
    if not records:
        print("no new search records")
        return 0
    subprocess.run(script(TRACKING_DIR, "unique_titles.py") + ["--write"], cwd=ROOT, stdout=subprocess.DEVNULL, check=False)
    rows = select(day, only=set(records))  # read the whole day so a repeat of an earlier call or slice is dropped
    kept = [r for r in rows if r["keep"]]
    tsv = logdir / "shortlist.tsv"
    with tsv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, SHORTLIST_COLS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(kept)
    print(f"\n{len(records)} records; {len(kept)} kept, {len(rows) - len(kept)} dropped")
    for src in dict.fromkeys(r["source"] for r in kept):
        group = [r for r in kept if r["source"] == src]
        print(f"\n## {src} ({len(group)})")
        for r in group:
            note = f" | {r['note']}" if r["note"] else ""
            print(f"{r['job_id']} | {r['company']} | {r['title']} | {r['location'][:60]} | {r['search']}{note}")
    print(f"\nshortlist: {tsv}")
    print(f"after approval: python3 pipeline/scripts/retrieve.py stage --write --shortlist '{tsv}' [--only <id>...] [--except <id>...]")
    return 0


def picks_from(args):
    """[(source, search, job_id, where, title, company)] from --shortlist (filtered) or source:search=item tokens."""
    picks = []
    if args.shortlist:
        with open(args.shortlist, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if args.only and r["job_id"] not in args.only:
                    continue
                if args.exclude and r["job_id"] in args.exclude:
                    continue
                picks.append((r["source"], r["search"], r["job_id"], r["where"], r["title"], r["company"]))
        if args.only:
            missing = set(args.only) - {p[2] for p in picks}
            if missing:
                sys.exit(f"error: not in the shortlist: {' '.join(sorted(missing))}")
    for t in args.items:
        src, sep, rest = t.partition(":")
        search, sep2, item = rest.partition("=")
        if not (sep and sep2 and src and search and item):
            sys.exit(f"error: write picks as <source>:<search>=<id, or path for uiux>: {t}")
        picks.append((src, search, item if src != "uiux" else item.rsplit("/", 1)[-1].split("-", 1)[0], item, "", ""))
    if not picks:
        sys.exit("error: no picks: pass --shortlist <tsv> or <source>:<search>=<item> tokens")
    return picks


def cmd_stage(args):
    picks = picks_from(args)
    by_src = {}
    for p in picks:
        by_src.setdefault(p[0], []).append(p)
    jobs, chrome = {}, []
    for src, group in by_src.items():
        if src in CHROME:
            chrome += group
        elif src == "linkedin":
            jobs[src] = ([script(SOURCE_DIR, "linkedin_fetch.py") + ["stage", "--write"] + [f"{s}={j}" for _, s, j, *_ in group]], 0)
        elif src == "uiux":
            jobs[src] = ([script(SOURCE_DIR, "uiux_board.py") + ["stage", "--write"] + [f"{s}={w}" for _, s, _, w, *_ in group]], 0)
        elif src in PAID:  # offline: stage from the saved response, no network, no credits
            jobs[src] = ([script(SOURCE_DIR, f"{src}_fetch.py") + ["stage", "--write"] + [f"{s}={j}" for _, s, j, *_ in group]], 0)
        else:
            sys.exit(f"error: unknown source '{src}'")
    if not args.write:
        show(jobs)
    elif jobs:
        logdir = RUNS / f"{dt.datetime.now():%Y-%m-%d-%H%M%S}-stage"
        logdir.mkdir(parents=True, exist_ok=True)
        run = Run(logdir)
        results = run.run(jobs)
        for src, (code, secs, out) in results.items():
            for ln in out:
                print(f"[{src}] {ln}")
        report(results, run.stop.is_set())
        if run.stop.is_set():
            return 1
    if chrome:
        print(f"\njob-fetcher batches (Chrome, one batch at a time, batch_size from `selection:`):")
        for src in dict.fromkeys(p[0] for p in chrome):
            print(f"source: {src}")
            for _, s, j, w, title, company in (p for p in chrome if p[0] == src):
                print(f"{j} | {title} | {company} | {w} | {s}")
    if not args.write:
        print("plan only; pass --write to stage")
        return 0
    fold = subprocess.run(script(TRACKING_DIR, "fold_jobs_into_tasks.py"), cwd=ROOT, capture_output=True, text=True)
    print("\nfold dry run: " + (fold.stdout.splitlines() or [fold.stderr.strip()])[0])
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="run every enabled source's search, then Select; print the shortlist")
    s.add_argument("--write", action="store_true", help="run the searches and write records (default: plan only)")
    s.add_argument("--paid", action="store_true", help="also make the paid Fantastic and TheirStack calls")
    s.add_argument("--incremental", action="store_true", help="LinkedIn's same-day second pass (`incremental:`)")
    s.add_argument("--sources", help="comma-separated subset, e.g. jobgether,uiux")
    g = sub.add_parser("stage", help="stage approved picks with each source's script, then the fold dry run")
    g.add_argument("--write", action="store_true", help="stage (default: plan only)")
    g.add_argument("--shortlist", help="a shortlist.tsv written by `search`")
    g.add_argument("--only", nargs="+", default=[], metavar="JOB_ID", help="stage only these shortlist ids")
    g.add_argument("--except", dest="exclude", nargs="+", default=[], metavar="JOB_ID", help="skip these shortlist ids")
    g.add_argument("items", nargs="*", metavar="source:search=item")
    args = ap.parse_args()
    return {"search": cmd_search, "stage": cmd_stage}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
