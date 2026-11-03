#!/usr/bin/env python3
"""
Aggregate unique job titles from all search-run records into titles-index.md.

Scans logs/searches/*.md, pulls the job_id and title columns from each run's
markdown table, dedupes titles case-insensitively, and counts distinct job_ids per
title. The index is MERGED, not regenerated: hand-scored Fit values and any extra
frontmatter (taxonomy fields) are kept; new titles are added with a blank Fit.

Usage:
    python3 pipeline/scripts/tracking/unique_titles.py            # dry run: report what would change
    python3 pipeline/scripts/tracking/unique_titles.py --write    # rewrite titles-index.md
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402

SEARCHES = naming.SEARCHES
INDEX = SEARCHES / "titles-index.md"
PIPE = re.compile(r"(?<!\\)\|")  # split on unescaped pipes only


def cells(line):
    return [c.strip().replace("\\|", "|") for c in PIPE.split(line.strip())[1:-1]]


def esc(s):
    return s.replace("|", "\\|")


def run_rows(md):
    """Yield (job_id, title) for each row of a run's results table."""
    cols = None
    for line in md.split("\n"):
        if not line.startswith("|"):
            cols = None
            continue
        row = cells(line)
        if cols is None:
            low = [c.lower() for c in row]
            if "job_id" in low and "title" in low:
                cols = (low.index("job_id"), low.index("title"))
            continue
        if set("".join(row)) <= set("-: "):
            continue  # separator row
        jid, title = (row[i] if i < len(row) else "" for i in cols)
        if title and title not in ("…", "...", "—", "-") and not (title.startswith("(") and title.endswith(")")):
            yield jid, title


def load_index():
    """Return (frontmatter dict, intro text, {lower title: (title, fit)})."""
    if not INDEX.exists():
        return {}, "", {}
    m = naming.FM_RE.match(INDEX.read_text(encoding="utf-8"))
    fm, body = (yaml.safe_load(m.group(1)) or {}, m.group(2)) if m else ({}, INDEX.read_text())
    intro, fits = [], {}
    in_table = False
    for line in body.split("\n"):
        if line.startswith("|"):
            in_table = True
            row = cells(line)
            if len(row) >= 3 and row[0].lower() != "title" and not set("".join(row)) <= set("-: "):
                fits[row[0].lower()] = (row[0], row[2])
        elif not in_table and not line.startswith("# "):
            intro.append(line)
    return fm, "\n".join(intro).strip(), fits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    runs = sorted(p for p in SEARCHES.glob("*.md") if p != INDEX)
    jobs = {}  # lower title -> (display title, set of job_ids)
    for p in runs:
        for jid, title in run_rows(p.read_text(encoding="utf-8")):
            key = title.lower()
            shown, ids = jobs.get(key, (title, set()))
            ids.add(jid or f"{p.name}:{title}")  # rows without an id count once per run
            jobs[key] = (shown, ids)

    fm, intro, fits = load_index()
    rows = []
    for key, (title, ids) in jobs.items():
        shown, fit = fits.get(key, (title, ""))
        rows.append((shown, len(ids), fit))
    dropped = [t for k, (t, _) in fits.items() if k not in jobs]
    rows.sort(key=lambda r: (-r[1], r[0].lower()))

    new = [r for r in rows if r[0].lower() not in fits]
    unscored = sum(1 for r in rows if r[2] == "")
    print(f"{len(runs)} runs · {len(rows)} unique titles · {len(new)} new · "
          f"{unscored} unscored · {len(rows) - unscored} with a Fit score")
    if dropped:
        print(f"WARNING: {len(dropped)} indexed titles no longer appear in any run (kept): {dropped[:5]}")
        for t in dropped:
            shown, fit = fits[t.lower()]
            rows.append((shown, 0, fit))
    if not args.write:
        for t, n, _ in new[:15]:
            print(f"  + {t} ({n})")
        print("dry run — pass --write to update titles-index.md")
        return

    fm["generated_at"] = datetime.now().isoformat(timespec="seconds")
    fm.setdefault("title", "Unique Job Titles Index")
    w = max([len("Title")] + [len(esc(r[0])) for r in rows])
    lines = ["---", yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000).strip(), "---", "",
             f"# Unique Job Titles ({len(rows)} unique titles across {len(runs)} search runs)", ""]
    note = "Count is the number of distinct job_ids carrying the title. Fit is scored 0-10 by hand; blank = not yet scored."
    intro = intro or "Titles are deduplicated case-insensitively and sorted by frequency (most common first)."
    lines += [intro if note in intro else f"{intro}\n\n{note}", ""]
    lines += [f"| {'Title'.ljust(w)} | Count | Fit |", f"| {'-' * w} | ----- | --- |"]
    lines += [f"| {esc(t).ljust(w)} | {str(n).ljust(5)} | {str(f).ljust(3)} |" for t, n, f in rows]
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {INDEX}")


if __name__ == "__main__":
    main()
