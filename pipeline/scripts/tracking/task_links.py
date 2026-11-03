#!/usr/bin/env python3
"""Keep the links at the top of each Application Tracking task note current.

Between the task's `# Title` line and the job description, each task carries a marked block:

    <!-- links -->
    - **Posting:** [<job title>](<url>)
    - **Résumé:** [[<vault path>|<file name>]] · [[<vault path>|PDF]]   or: no resume
    - **Cover letter:** [[<vault path>|<file name>]]  or: no cover letter
    - **Interest statement:** [[<vault path>|why-interested]]   only when why-interested.md exists (D19)
    - **Match report:** [[<vault path>|Match report]]   only when match-report.md exists
    <!-- /links -->

Existence is decided by the files on disk (applications/<task name>/, named from the task's title, not its file name; the letter's .docx ends ' - Cover Letter'),
so the block can't drift from reality. The frontmatter fields (Résumé variant, Cover letter) are left alone.
The block is replaced in place on every run, so this is idempotent. `fold_jobs_into_tasks.py`,
`render_resume.py` and `render_cover_letter.py` call refresh() after they write a task.

Usage:
    python3 pipeline/scripts/tracking/task_links.py            # dry run: report what would change
    python3 pipeline/scripts/tracking/task_links.py --write    # backs up _tasks to the scratchpad, then rewrites
"""
import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from naming import split  # noqa: E402

VAULT_ROOT = naming.VAULT_ROOT
TASKS = naming.TASKS

BLOCK_RE = re.compile(r"<!-- links -->\n.*?<!-- /links -->", re.S)


def field_ids():
    by_name = naming.field_ids()
    return by_name["Posting"], by_name["Company"]


def docs(folder, letter):
    """The .docx files in a posting folder: the cover letter's (name ends LETTER_SUFFIX) or the résumé's."""
    found = folder.glob(f"{naming.candidate_name()} - *.docx") if folder.exists() else []
    return sorted(f for f in found if f.stem.endswith(naming.LETTER_SUFFIX) == letter)


def file_link(folder, no_text, letter=False):
    """Link the .docx (the submission file), plus the .pdf beside it when one exists."""
    files = docs(folder, letter)
    if not files:
        return no_text
    link = lambda f, label: f"[[{f.resolve().relative_to(VAULT_ROOT).as_posix()}|{label}]]"
    out = link(files[0], files[0].stem)
    pdf = files[0].with_suffix(".pdf")
    return out + (f" · {link(pdf, 'PDF')}" if pdf.exists() else "")


def interest_link(folder):
    """The interest statement line, or None: unlike the résumé and letter, a missing statement isn't listed."""
    f = folder / "why-interested.md"
    return f"- **Interest statement:** [[{f.resolve().relative_to(VAULT_ROOT).as_posix()}|why-interested]]" if f.exists() else None


def match_report_link(folder):
    """The match report line, or None when the posting has no report."""
    f = folder / "match-report.md"
    return f"- **Match report:** [[{f.resolve().relative_to(VAULT_ROOT).as_posix()}|Match report]]" if f.exists() else None


def build_block(fm, ids):
    posting_id, company_id = ids
    vals = fm.get("customFields") or {}
    stem = naming.folder_name(fm["title"], vals.get(company_id, ""))  # not the file name: dotpm renames files
    title = naming.job_title(fm["title"], vals.get(company_id, ""))
    url = vals.get(posting_id)
    posting = f"[{title}]({url})" if url else title
    lines = [
        "<!-- links -->",
        f"- **Posting:** {posting}",
        f"- **Résumé:** {file_link(naming.APPLICATIONS / stem, 'no resume')}",
        f"- **Cover letter:** {file_link(naming.APPLICATIONS / stem, 'no cover letter', letter=True)}",
        interest_link(naming.APPLICATIONS / stem),
        match_report_link(naming.APPLICATIONS / stem),
        "<!-- /links -->",
    ]
    return "\n".join(l for l in lines if l)


def apply_block(body, block):
    if BLOCK_RE.search(body):
        return BLOCK_RE.sub(lambda m: block, body, count=1)
    m = re.search(r"^# .*$", body, re.M)
    if not m:
        return block + "\n\n" + body.lstrip("\n")
    return body[: m.end()] + "\n\n" + block + "\n\n" + body[m.end():].lstrip("\n")


def refresh(task, ids=None, write=True):
    """Rewrite one task's link block. Returns True if the note changed."""
    ids = ids or field_ids()
    text = task.read_text(encoding="utf-8")
    fm_text, body = split(task)
    new_body = apply_block(body, build_block(naming.load_yaml(fm_text), ids))
    if new_body == body:
        return False
    if write:
        task.write_text(f"---\n{fm_text}\n---\n{new_body}", encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    ids = field_ids()
    tasks = naming.tasks()
    if args.write:
        backup = naming.backup_dir() / f"_tasks.bak-links-{dt.datetime.now():%H%M%S}"
        shutil.copytree(TASKS, backup)
        print(f"backed up _tasks to {backup}")
    changed = sum(refresh(t, ids, write=args.write) for t in tasks)
    by_name = naming.field_ids()
    have = lambda letter: sum(1 for t in tasks if docs(naming.APPLICATIONS / naming.task_folder(t, by_name), letter))
    print(f"{len(tasks)} tasks, {changed} {'updated' if args.write else 'would change'}; "
          f"{have(False)} with a résumé, {have(True)} with a cover letter")
    if not args.write:
        print("dry run; pass --write to apply")


if __name__ == "__main__":
    main()
