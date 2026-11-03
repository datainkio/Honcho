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
so the block can't drift from reality. The Cover letter frontmatter field is left alone.
The same files set four checkbox fields and dotpm's `progress` (D38): Has résumé (the .docx and the .pdf),
Has cover letter (the letter's .docx), Has match report, Has questions (questions.md, or the legacy
application-questions.md). `progress` is the share of the four that are checked: 0, 25, 50, 75 or 100.
The block is replaced in place on every run, so this is idempotent. `fold_jobs_into_tasks.py`,
`render_resume.py` and `render_cover_letter.py` call refresh() after they write a task; run it with job ids
after writing a match report or questions by hand or by agent.

Usage:
    python3 pipeline/scripts/tracking/task_links.py                     # dry run: report what would change
    python3 pipeline/scripts/tracking/task_links.py --write             # backs up _tasks to the scratchpad, then rewrites
    python3 pipeline/scripts/tracking/task_links.py --write <job_id>... # only these postings' tasks
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
PROGRESS_FIELDS = ("Has résumé", "Has cover letter", "Has match report", "Has questions")
QUESTIONS_FILES = ("questions.md", "application-questions.md")


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


def progress_flags(folder):
    """{field name: bool} for the four progress checkboxes; the résumé counts only when its .pdf sits beside the .docx."""
    resume = docs(folder, False)
    return {
        "Has résumé": bool(resume) and resume[0].with_suffix(".pdf").exists(),
        "Has cover letter": bool(docs(folder, True)),
        "Has match report": (folder / "match-report.md").exists(),
        "Has questions": any((folder / f).exists() for f in QUESTIONS_FILES),
    }


def set_progress(fm_text, fm, by_name):
    """The task's frontmatter with the four checkboxes and `progress` set from the files on disk."""
    from tracking.fold_jobs_into_tasks import set_values  # lazy: the fold imports this module's refresh()
    company = (fm.get("customFields") or {}).get(by_name["Company"], "")
    flags = progress_flags(naming.APPLICATIONS / naming.folder_name(fm["title"], company))
    fm_text = re.sub(r"^customFields: \{\}$", "customFields:", fm_text, flags=re.M)
    fm_text = set_values(fm_text, {by_name[n]: v for n, v in flags.items()})
    line = f"progress: {round(100 * sum(flags.values()) / len(flags))}"
    if re.search(r"^progress:.*$", fm_text, re.M):
        return re.sub(r"^progress:.*$", line, fm_text, count=1, flags=re.M)
    m = re.search(r"^due:.*$", fm_text, re.M)  # dotpm's own place for it
    return fm_text[: m.end()] + "\n" + line + fm_text[m.end():] if m else fm_text + "\n" + line


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
    """Rewrite one task's link block, progress checkboxes and progress. Returns True if the note changed."""
    ids = ids or field_ids()
    fm_text, body = split(task)
    fm = naming.load_yaml(fm_text)
    new_fm = set_progress(fm_text, fm, naming.field_ids())
    new_body = apply_block(body, build_block(fm, ids))
    if (new_fm, new_body) == (fm_text, body):
        return False
    if write:
        task.write_text(f"---\n{new_fm}\n---\n{new_body}", encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("job_ids", nargs="*", help="only these postings' tasks (default: every task)")
    args = ap.parse_args()
    ids = field_ids()
    if args.job_ids:
        index = naming.index()
        missing = [j for j in args.job_ids if j not in index]
        if missing:
            sys.exit(f"no task for job id(s): {' '.join(missing)}")
        tasks = [index[j] for j in args.job_ids]
    else:
        tasks = naming.tasks()
    if args.write:
        backup = naming.backup_dir() / f"_tasks.bak-links-{dt.datetime.now():%H%M%S}"
        if args.job_ids:
            backup.mkdir(parents=True, exist_ok=True)
            for t in tasks:
                shutil.copy2(t, backup / t.name)
        else:
            shutil.copytree(TASKS, backup)
        print(f"backed up {len(tasks)} task(s) to {backup}")
    changed = sum(refresh(t, ids, write=args.write) for t in tasks)
    by_name = naming.field_ids()
    have = lambda letter: sum(1 for t in tasks if docs(naming.APPLICATIONS / naming.task_folder(t, by_name), letter))
    print(f"{len(tasks)} tasks, {changed} {'updated' if args.write else 'would change'}; "
          f"{have(False)} with a résumé, {have(True)} with a cover letter")
    if not args.write:
        print("dry run; pass --write to apply")


if __name__ == "__main__":
    main()
