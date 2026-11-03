#!/usr/bin/env python3
"""Shortlist a search record's jobs: drop what is already tracked or excluded, so the model only judges plausibility.

One set of Select rules for every source (pipeline/runbook.md Step 2 and each source's Select step; F1 of
context/token-efficiency-review.md). Reads the table of one or more logs/searches/ records (any source: the
`job_id`, `title` and `company` columns, plus `path`, `type`, `location` and `featured` when present) and drops a job when:

- a task already has its id as Job ID, or a note for it is already staged in logs/inbox/;
- a task already has the same company and title. Companies compare case-insensitively with '&'/'and', punctuation
  and legal suffixes (LLC, Inc, Corp, Co, Ltd…) removed; a tracked title that starts with the job's title counts
  as the same title ('UI/UX Designer' matches 'UI/UX Designer | AI Powered Products'), and a trailing 'Remote' is
  ignored ('Designer- Remote' matches 'Designer');
- the same job, or the same company and title, appeared earlier in this run's records. Records are read in
  SOURCE_ORDER, whatever the argument order: sources whose description is already in hand (the paid APIs) first,
  the riskiest fetch (LinkedIn) last, so a job several sources list is fetched from the cheapest (D21);
- its title contains an `exclude_title_terms` entry, its company is a placeholder, or (UI/UX Jobs Board) its type
  is in `sources: uiux: exclude_types`.

Kept jobs whose company or location needs a look (a Featured UI/UX Jobs Board card) are marked `check:`.
Subsidiaries and person-named companies still need a read: no string rule catches them.

Usage:
    python3 pipeline/scripts/tracking/select_candidates.py logs/searches/2026-10-12--uiux-remote-us.md [more records…]
    python3 pipeline/scripts/tracking/select_candidates.py --kept-only <records…>   # just the kept lines
Prints `keep | id | company | title | location | path-or-url` and `drop | id | company | title | reason`.
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402

ROOT = naming.ROOT
INBOX = naming.INBOX
CONFIG = naming.CRITERIA

PLACEHOLDER_COMPANIES = {"our team", "confidential", "stealth company", "stealth startup", "undisclosed", "company"}
SOURCE_ORDER = ("fantastic", "theirstack", "uiux", "jobgether", "indeed", "linkedin")  # cheapest description first
LEGAL = r"(?:l\.?l\.?c|inc|incorporated|corp|corporation|co|ltd|limited|plc|gmbh|llp|lp|pbc|s\.?a)"


def norm_company(s):
    s = s.lower().replace("&", " ").replace("+", " ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\band\b", " ", s)
    words = s.split()
    while words and re.fullmatch(LEGAL, words[-1]):
        words.pop()
    return " ".join(words)


def norm_title(s):
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\[[^\]]*\]", " ", s)  # requisition codes
    s = re.sub(r"[^\w\s/+-]", " ", s)
    s = " ".join(s.split())
    # A trailing work-type marker ('Designer- Remote', 'Designer (Remote)', 'Designer, Remote') is a repost, not a new
    # title: the 2026-10-23 BeyondTrust repost slipped through on it.
    return re.sub(r"[\s-]*\bremote$", "", s) or s


def read_table(path):
    """Rows of the first markdown table that has job_id, title and company columns."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, ln in enumerate(lines):
        if not ln.startswith("|"):
            continue
        cols = [c.strip().lower() for c in re.split(r"(?<!\\)\|", ln.strip())[1:-1]]
        if {"job_id", "title", "company"} <= set(cols):
            rows = []
            for row in lines[i + 2:]:
                if not row.startswith("|"):
                    break
                cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row.strip())[1:-1]]
                rows.append(dict(zip(cols, cells)))
            return rows
    return []


def front(path):
    """A search record's frontmatter as a dict, or {} when it has none."""
    fm, _ = naming.split_text(path.read_text(encoding="utf-8"))
    return (yaml.safe_load(fm) or {}) if fm else {}


def source_of(path):
    t = str(front(path).get("type", ""))
    return {"jobgether-search-run": "jobgether", "indeed-search-run": "indeed", "uiux-search-run": "uiux",
            "fantastic-search-run": "fantastic", "theirstack-search-run": "theirstack"}.get(t, "linkedin")


def tracked():
    """({job ids}, [(company, title)] normalized) from every Application Tracking task."""
    ids = naming.field_ids()
    jids, pairs = set(), []
    for p in naming.tasks():
        fm = naming.task_fm(p)
        cf = fm.get("customFields") or {}
        if cf.get(ids["Job ID"]):
            jids.add(str(cf[ids["Job ID"]]))
        company = str(cf.get(ids["Company"]) or "")
        title = naming.job_title(str(fm.get("title", "")), company)
        if company and title:
            pairs.append((norm_company(company), norm_title(title)))
    return jids, pairs


def same_posting(pairs, company, title):
    c, t = norm_company(company), norm_title(title)
    return bool(c and t) and any(pc == c and (pt == t or pt.startswith(t + " ")) for pc, pt in pairs)


def search_name(path):
    return str(front(path).get("search_name", ""))


def select(records, only=None):
    """One dict per job in the records, in source order (with `only`, a set of records: every record is read, so a job seen
    in another source or an earlier call is dropped as a repeat, but only rows from `only` are returned). Keys: keep (bool), reason, source, search, job_id, company, title,
    location, where (path or url), note. Exits on a missing record or one without a job table."""
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    terms = [t.lower() for t in cfg.get("selection", {}).get("exclude_title_terms", [])]
    types = {t.lower() for t in ((cfg.get("sources") or {}).get("uiux") or {}).get("exclude_types", [])}
    jids, pairs = tracked()
    staged = {p.stem for p in INBOX.glob("*.md")}
    seen_ids, run_pairs = set(), []

    for rec in records:
        if not rec.exists():
            sys.exit(f"error: no such record: {rec}")
    ordered = sorted(((source_of(r), r) for r in records), key=lambda sr: SOURCE_ORDER.index(sr[0]))
    out = []
    for src, rec in ordered:
        rows = read_table(rec)
        if not rows:
            sys.exit(f"error: no job_id/title/company table in {rec}")
        search = search_name(rec)
        for r in rows:
            jid, title, company = r.get("job_id", ""), r.get("title", ""), r.get("company", "")
            low = title.lower()
            reason = None
            if jid in jids:
                reason = "tracked (job id)"
            elif jid in staged:
                reason = "already staged"
            elif jid in seen_ids:
                reason = "repeat in this run"
            elif same_posting(pairs, company, title):
                reason = "tracked (company and title)"
            elif same_posting(run_pairs, company, title):
                reason = "repeat in this run (company and title)"
            elif any(t in low for t in terms):
                reason = "excluded title: " + next(t for t in terms if t in low)
            elif norm_company(company) in PLACEHOLDER_COMPANIES or not company:
                reason = "placeholder company"
            elif src == "uiux" and r.get("type", "").lower() in types:
                reason = "excluded type: " + r["type"]
            seen_ids.add(jid)
            run_pairs.append((norm_company(company), norm_title(title)))
            if only is not None and rec not in only:
                continue
            note = "check: Featured card, confirm location" if src == "uiux" and r.get("featured") == "yes" else ""
            out.append({"keep": reason is None, "reason": reason, "source": src, "search": search, "job_id": jid,
                        "company": company, "title": title, "location": r.get("location", ""),
                        "where": r.get("path") or r.get("url") or "", "note": note})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("records", nargs="+", type=Path)
    ap.add_argument("--kept-only", action="store_true")
    args = ap.parse_args()
    rows = select(args.records)
    for r in rows:
        if r["keep"]:
            note = f" | {r['note']}" if r["note"] else ""
            print(f"keep | {r['job_id']} | {r['company']} | {r['title']} | {r['location']} | {r['where']}{note}")
        elif not args.kept_only:
            print(f"drop | {r['job_id']} | {r['company']} | {r['title']} | {r['reason']}")
    kept = sum(r["keep"] for r in rows)
    print(f"{kept} kept, {len(rows) - kept} dropped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
