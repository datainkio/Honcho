#!/usr/bin/env python3
"""Build the keyword lexicon: verdicts that repeat across match reports, because the résumé template is fixed text
(plan §3, 2.2). `match_packet.py report --lexicon` lists the entries whose term appears in a posting's JD as known
verdicts. The agent still chooses which terms are high-value; a hint only saves it the template search.

An entry is a term seen in at least --min-n reports whose `found as` agrees in at least --min-share of them. It
keeps the commonest `where`, `action` and `backing` of the agreeing rows. Freshness: an entry is dropped when a
template phrase its `where` quotes is no longer in the template, or when an 'absent' term now appears there.
Measured on 2026-10-26 (built from reports before 2026-10-23, tested on that day's 40): with 5 and 0.9, verdicts
agree 94% where agent and lexicon both list a term, but only 31% of lexicon terms in a JD were terms the agent chose.
That is why entries are hints, never pre-filled rows.

Usage:
    python3 pipeline/scripts/package/keyword_lexicon.py build [--min-n 5] [--min-share 0.9] [--exclude <job_id>...]   # logs/lexicon.json
    HONCHO_LEXICON=<file> …                                              # build or read another file (tests)
    python3 pipeline/scripts/package/keyword_lexicon.py show [term]                           # entries, or one term
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from naming import split  # noqa: E402
from package.match_report import table  # noqa: E402

LEXICON = Path(os.environ.get("HONCHO_LEXICON") or naming.LEXICON)  # override for tests
TEMPLATE = naming.RESUME_TEMPLATE


def norm(term):
    return " ".join(term.lower().split())


def verdict(found_as):
    f = found_as.strip().lower()
    return "absent" if f.startswith("absent") else f.split()[0] if f else ""


def quoted(where):
    """Template phrases a `where` cell quotes ('…'), at least three words, so a quote of one word can't pass by luck."""
    return [q for q in re.findall(r"'([^']{3,})'", where) if len(q.split()) >= 3]


def fresh(entry, template):
    low = template.lower()
    if entry["found_as"] == "absent":
        return re.search(rf"(?<!\w){re.escape(entry['term'])}(?!\w)", low) is None
    return all(q.lower() in low for q in quoted(entry["where"]))


def build(min_n, min_share, exclude=()):
    rows = collections.defaultdict(list)
    reports = 0
    for p in sorted(naming.APPLICATIONS.glob("*/match-report.md")):
        if exclude and str((naming.load_yaml(split(p)[0]) or {}).get("job_id", "")) in exclude:
            continue  # held out, e.g. the postings a test runs on
        reports += 1
        for r in table(split(p)[1], "Keywords"):
            if len(r) >= 5 and r[0]:
                rows[norm(r[0])].append(r)
    template = split(TEMPLATE)[1]
    entries, stale = {}, 0
    for term, rs in rows.items():
        if len(rs) < min_n:
            continue
        top, n = collections.Counter(verdict(r[1]) for r in rs).most_common(1)[0]
        if n / len(rs) < min_share:
            continue
        agree = [r for r in rs if verdict(r[1]) == top]
        common = lambda i: collections.Counter(r[i] for r in agree).most_common(1)[0][0]
        e = {"term": term, "found_as": top, "where": common(2), "action": common(3), "backing": common(4),
             "seen": len(rs), "agree": round(n / len(rs), 2)}
        if fresh(e, template):
            entries[term] = e
        else:
            stale += 1
    LEXICON.write_text(json.dumps({
        "built_at": dt.datetime.now().isoformat(timespec="seconds"), "reports": reports, "min_n": min_n,
        "min_share": min_share, "template_sha1": hashlib.sha1(TEMPLATE.read_bytes()).hexdigest()[:10],
        "entries": entries}, ensure_ascii=False, indent=1), encoding="utf-8")
    by = collections.Counter(e["found_as"] for e in entries.values())
    print(f"{len(entries)} entries from {reports} reports ({dict(by)}); {stale} dropped as stale; wrote {LEXICON}")


def load():
    if not LEXICON.exists():
        return None
    data = json.loads(LEXICON.read_text(encoding="utf-8"))
    template = split(TEMPLATE)[1]
    data["entries"] = {t: e for t, e in data["entries"].items() if fresh(e, template)}  # re-check at use
    return data


def hints(jd):
    """Lexicon entries whose term appears in the JD, as packet lines; [] when there is no lexicon."""
    data = load()
    if not data:
        return []
    low = jd.lower()
    hit = [e for t, e in sorted(data["entries"].items()) if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", low)]
    return [f"| {e['term']} | {e['found_as']} | {e['where']} | {e['action']} | {e['backing']} | {e['seen']}, {e['agree']:.0%} |"
            for e in hit]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--min-n", type=int, default=5)
    b.add_argument("--min-share", type=float, default=0.9)
    b.add_argument("--exclude", nargs="+", default=[], metavar="JOB_ID", help="leave these postings' reports out")
    s = sub.add_parser("show")
    s.add_argument("term", nargs="?")
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.min_n, args.min_share, set(args.exclude))
        return 0
    data = load()
    if not data:
        sys.exit("no lexicon: run `keyword_lexicon.py build`")
    for t, e in sorted(data["entries"].items()):
        if not args.term or norm(args.term) == t:
            print(f"{t} | {e['found_as']} | {e['where'][:80]} | seen {e['seen']}, {e['agree']:.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
