#!/usr/bin/env python3
"""Fill the résumé template from a posting's match report, once Russ approves it, then render and link it (skill: resume-tailoring step 5).

Reads applications/<task name>/match-report.md: its Fields table gives the agent's slot values, its Keywords
table gives target_vocabulary (terms present) and gaps (terms absent). job_title and job_title_article are filled here,
never from the report. Writes resume.md, `<Name> - <Title>.docx` and `.pdf` beside the report, and sets the task's
Résumé variant field to a wikilink to the .docx. Fixed text is rendered as written.
Refuses: a frozen posting (D13), a task whose Matching approved box is unchecked (D22), an unfilled slot, a forbidden
character (D9). The report's own `status` is not read.

Usage:
    python3 pipeline/scripts/package/render_resume.py 4476502229 [more job ids…]            # dry run: slot values and file names
    python3 pipeline/scripts/package/render_resume.py 4476502229 [more job ids…] --write    # backs up each task, renders, links
Needs python-docx, reportlab and pyyaml.
"""
import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from naming import split  # noqa: E402
from package import charset  # noqa: E402
from package.match_report import table  # noqa: E402
from package.render_docx import render_docx, wikilink  # noqa: E402
from package.render_pdf import render_pdf  # noqa: E402
from tracking.fold_jobs_into_tasks import refresh_links, set_values  # noqa: E402

TEMPLATE = naming.RESUME_TEMPLATE
SCRIPT_SLOTS = ("job_title", "job_title_article")
SLOT_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def article(title):
    """'an' before a vowel sound. Most U- titles (UX, UI, User, Usability, Uni-) start with a 'you' sound; Un-, Up-, Ul-, Um- don't."""
    return "an" if re.match(r"(?i)[aeio]|u[nplm][^aeiouy]", title) else "a"


def fill(body, values):
    missing = sorted({s for s in SLOT_RE.findall(body) if not values.get(s)})
    if missing:
        sys.exit(f"unfilled slot(s): {', '.join(missing)}")
    return SLOT_RE.sub(lambda m: values[m.group(1)], body)


def for_render(body):
    """The renderers know # to ###; a #### sub-heading inside a role renders as a bold label."""
    return re.sub(r"^#### (.+)$", r"**\1**", body, flags=re.M)


def render_one(jid, write, rid):
    task = naming.find_task(jid)
    if not task:
        sys.exit(f"no task with Job ID {jid}")
    if naming.is_frozen(task):
        sys.exit(f"status {naming.task_fm(task).get('status')} is frozen (Applied or a 'done' status): the résumé was submitted")
    fm_text, jd = split(task)
    cf = yaml.safe_load(fm_text)
    ids = naming.field_ids()
    if (cf.get("customFields") or {}).get(ids["Matching approved"]) is not True:
        sys.exit(f"{jid}: the task's Matching approved box is not checked; Russ checks it after reviewing the match report")
    company = (cf.get("customFields") or {}).get(ids["Company"], "")
    title = naming.job_title(cf["title"], company)
    folder = naming.APPLICATIONS / naming.task_folder(task)
    report = folder / "match-report.md"
    if not report.exists():
        sys.exit(f"no match report: {report}")
    rfm_text, rbody = split(report)
    rfm = yaml.safe_load(rfm_text) or {}
    title = rfm.get("job_title") or title  # cleaned title, when the posting's carries pipes or location suffixes

    values = {r[0]: r[-1] for r in table(rbody, "Fields") if len(r) >= 2}  # value is the last column (some reports add filled_by)
    values["job_title"], values["job_title_article"] = title, article(title)
    keywords = table(rbody, "Keywords")
    vocab = [r[0] for r in keywords if len(r) > 1 and r[1] != "absent"]
    gaps = [r[0] for r in keywords if len(r) > 1 and r[1] == "absent"]

    _, tbody = split(TEMPLATE)
    body = for_render(fill(tbody.lstrip("\n"), values))
    charset.check(body, f"{jid} résumé")
    fname = f"{naming.candidate_name()} - {naming.safe(title)}.docx"
    print(f"{jid}  {folder.name}/{fname}")
    for k, v in values.items():
        print(f"    {k}: {v}")
    if not write:
        return

    backup = naming.backup_dir() / f"{task.stem}.bak-{dt.datetime.now():%H%M%S}.md"
    shutil.copy2(task, backup)
    for old in [*folder.glob(f"{naming.candidate_name()} - *.docx"), *folder.glob(f"{naming.candidate_name()} - *.pdf")]:
        if old.stem != Path(fname).stem and not old.stem.endswith(naming.LETTER_SUFFIX):
            old.unlink()
    render_pdf(body, folder / Path(fname).with_suffix(".pdf"), title)
    meta = {
        "type": "resume-posting", "job_id": int(jid) if jid.isdigit() else jid, "target_title": title, "company": company,
        "template": TEMPLATE.relative_to(naming.ROOT).as_posix(), "match_report": "match-report.md",
        "generated_at": dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), "profile_version": str(rfm.get("profile_version", "")),
        "slots": values, "target_vocabulary": vocab, "gaps": gaps,
        "render": {"formats": ["docx", "pdf"], "font": naming.render_style("docx")["font"]},
    }
    (folder / "resume.md").write_text("---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n\n" + body, encoding="utf-8")
    render_docx(body, folder / fname, title)
    task.write_text(f"---\n{set_values(fm_text, {rid: wikilink(folder / fname, 'Résumé')})}\n---\n{jd}", encoding="utf-8")
    refresh_links(task)
    print(f"    wrote resume.md, .docx, .pdf; task backed up to {backup}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", nargs="+")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    rid = naming.field_ids()["Résumé variant"]
    for jid in args.jobs:
        render_one(jid, args.write, rid)
    if not args.write:
        print("dry run; pass --write to apply")


if __name__ == "__main__":
    main()
