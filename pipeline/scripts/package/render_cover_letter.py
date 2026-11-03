#!/usr/bin/env python3
"""Render a posting's cover-letter.md to .docx and link it from the posting's task (spec: pipeline/specs/cover-letter-skill-spec.md §2).

Reads applications/<task name>/cover-letter.md (frontmatter + letter body), renders
`<Name> - <Title> - Cover Letter.docx` beside it with the same renderer and file-name rule as the résumés, and sets the
task's Cover letter field to a wikilink. Writing the letter is the skill's job; this only renders and links.
Refuses to run unless the posting's résumé exists and the letter's honesty_review is `passed`.

Usage:
    python3 pipeline/scripts/package/render_cover_letter.py 4476509615 [more job ids…]            # dry run
    python3 pipeline/scripts/package/render_cover_letter.py 4476509615 [more job ids…] --write    # backs up each task, renders, links
Needs python-docx and pyyaml.
"""
import argparse
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from naming import split  # noqa: E402
from package.render_docx import render_docx, wikilink  # noqa: E402
from tracking.fold_jobs_into_tasks import refresh_links, set_values  # noqa: E402


def render_one(jid, write):
    """Render and link one posting's letter; sys.exit(message) on any refusal."""
    task = naming.find_task(jid)
    if not task:
        sys.exit(f"no task with Job ID {jid}")
    if naming.is_frozen(task):
        sys.exit(f"status {naming.task_fm(task).get('status')} is frozen (Applied or a 'done' status): the letter was submitted")
    folder = naming.APPLICATIONS / naming.task_folder(task)
    src = folder / "cover-letter.md"
    if not src.exists():
        sys.exit(f"no letter: {src}")
    fm_text, body = split(src)
    meta = yaml.safe_load(fm_text)
    if meta.get("type") != "cover-letter" or str(meta.get("job_id")) != jid:
        sys.exit("frontmatter is not a cover-letter for this job_id")
    if meta.get("honesty_review") != "passed":
        sys.exit("honesty_review is not 'passed'; run the skill's self-check first")
    if not (folder / "resume.md").exists():
        sys.exit(f"the posting's résumé doesn't exist yet: write it first (render_resume.py)")

    title = meta["target_title"]
    fname = f"{naming.candidate_name()} - {naming.safe(title)}{naming.LETTER_SUFFIX}.docx"
    field = naming.field_ids()["Cover letter"]
    link = wikilink(folder / fname, "Cover letter")
    print(f"{jid}  {fname}\n  {link}")
    if not write:
        print("  dry run; pass --write to apply")
        return

    shutil.copy(task, naming.backup_dir() / f"{task.stem}.md.bak")
    for old in folder.glob(f"{naming.candidate_name()} - *{naming.LETTER_SUFFIX}.docx"):
        if old.name != fname:
            old.unlink()
    render_docx(body.lstrip("\n"), folder / fname, title)
    task_fm, task_body = split(task)
    task.write_text(f"---\n{set_values(task_fm, {field: link})}\n---\n{task_body}", encoding="utf-8")
    refresh_links(task)
    print("  rendered and linked")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job_ids", nargs="+", metavar="job_id")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    failed = []
    for jid in args.job_ids:  # one call renders a whole batch of letters (F7)
        try:
            render_one(jid, args.write)
        except SystemExit as e:
            failed.append(jid)
            print(f"{jid}  refused: {e.code}", file=sys.stderr)
    if failed:
        sys.exit(f"{len(failed)} of {len(args.job_ids)} refused: {' '.join(failed)}")


if __name__ == "__main__":
    main()
