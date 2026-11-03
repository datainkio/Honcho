#!/usr/bin/env python3
"""Write the inputs an agent needs for match reports, cover letters or interest briefs into two files, so the agent
reads two files instead of discovering them (plan §3, 2.1, 2.4, 2.5).

Each mode writes, under logs/runs/packets/:
- a **fixed** file: what every posting in the mode shares (template, profile sections, truth rules, specs, shapes).
  It is named by a hash of its content, so a batch reuses it until a source changes.
- a **batch** file: per posting, its paths, the facts the agent used to compute (task folder, cleaned title,
  company, location, work type), and the inputs for that mode. Postings the mode's gate refuses are listed, not
  included.
It prints both paths and one line per posting. Give the agent the two paths; it reads them with Read.

Usage:
    python3 pipeline/scripts/package/match_packet.py report <job_id>...     # match reports: template, profile §1-§15, spec, shape; JDs
    python3 pipeline/scripts/package/match_packet.py letter <job_id>...     # cover letters: profile sections, letter shape; JD, résumé
                                                           #   frontmatter, report fields and gaps
    python3 pipeline/scripts/package/match_packet.py interest <job_id>...   # interest briefs: JD, report fields, keyword rows by
                                                           #   verdict, résumé frontmatter (no profile, D19)
    python3 pipeline/scripts/package/match_packet.py report --due --lexicon # every posting `naming.py reports` lists as due (D27), with
                                                           #   lexicon hints (rebuilt first when a report is newer, D28)
Read-only: writes only under logs/runs/packets/.
"""
import argparse
import datetime as dt
import hashlib
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from naming import split  # noqa: E402
from package.match_report import after_table, section, table  # noqa: E402
from tracking.task_links import BLOCK_RE  # noqa: E402

ROOT = naming.ROOT
OUT = naming.RUNS / "packets"
TEMPLATE = naming.RESUME_TEMPLATE
PROFILE = naming.DOSSIER
TRUTH = naming.TRUTH_RULES
KEYWORD_SPEC = naming.SPECS / "keyword-matching-spec.md"
REPORT_MODEL = naming.MODELS / "Match Report.md"
ATS_SPEC = naming.SPECS / "ats-formatting-spec.md"

REPORT_PROFILE = list(range(1, 16))  # resume-tailoring step 1: §1-§15
LETTER_PROFILE = [2, 6, 7, 8, 10, 11, 14]  # cover-letter-writing step 1

# The address and salutation every letter shares (Russ's choice, 2026-10-27). The header lines come from the profile's
# letter template and the sign-off name from the dossier (letter_head, letter_tail). Stated in the packet so no agent
# reads the renderer or an earlier letter to learn them.
LETTER_ADDRESS = """{date}

<Only when the JD names the post author: their first and last name, then *their title*, then the organization, one per line. Otherwise nothing.>

Dear <the post author's first name, or else the organization>,"""


def letter_head():
    """The numbered list under the letter template's `## Header` (name, then contact lines), then LETTER_ADDRESS."""
    m = re.search(r"^## Header\n(.*?)(?=^## |\Z)", body_of(naming.LETTER_TEMPLATE), re.M | re.S)
    lines = [re.sub(r"^\d+\.\s*", "", l.strip()) for l in (m.group(1) if m else "").splitlines() if re.match(r"\s*\d+\.", l)]
    if not lines:
        raise SystemExit(f"{naming.LETTER_TEMPLATE}: no numbered list under '## Header'")
    return "\n\n".join([f"# {lines[0].strip('*')}", *lines[1:], LETTER_ADDRESS])


def letter_tail():
    return f"Sincerely,\n\n{naming.candidate_name()}"


def body_of(path):
    return split(path)[1]


def profile_sections(numbers):
    """The profile's `## N. …` sections, in order, by number."""
    text = body_of(PROFILE)
    parts = re.split(r"(?m)^(?=## \d+\. )", text)
    keep = [p for p in parts if (m := re.match(r"## (\d+)\. ", p)) and int(m.group(1)) in numbers]
    return "\n".join(p.rstrip() + "\n" for p in keep)


def frontmatter_text(path):
    return split(path)[0].strip()


def jd_of(task):
    body = BLOCK_RE.sub("", body_of(task)).strip()
    return re.sub(r"^# .*\n+", "", body, count=1)  # the task's own title line


def facts(task, ids):
    fm = naming.task_fm(task)
    cf = fm.get("customFields") or {}
    company = cf.get(ids["Company"], "")
    folder = naming.APPLICATIONS / naming.task_folder(task, ids)
    get = lambda name: cf.get(ids[name], "") if name in ids else ""
    return {
        "job_id": str(cf.get(ids["Job ID"], "")), "company": company, "title": naming.job_title(fm["title"], company),
        "status": fm.get("status"), "priority": fm.get("priority"), "task": task, "folder": folder,
        "location": get("Location"), "work_type": get("Work type"), "posting": get("Posting"),
        "fit": get("Fit"), "fit_flags": get("Fit flags"), "fit_gaps": get("Fit gaps"),
    }


def head(f, extra=()):
    lines = [f"## {f['company']}, {f['title']} ({f['job_id']})", "",
             f"- task: {f['task']}", f"- folder: {f['folder']}", f"- job_title (cleaned, no company): {f['title']}",
             f"- company: {f['company']}", f"- location: {f['location'] or '-'}", f"- work type: {f['work_type'] or '-'}",
             f"- posting: {f['posting'] or '-'}", f"- priority: {f['priority']}", *extra, ""]
    return "\n".join(lines)


# ---------- modes ----------

def fixed_report():
    tfm, tbody = split(TEMPLATE)
    return "\n".join([
        "# Match-report packet: fixed inputs",
        "Everything a match report needs that does not change per posting. Follow the resume-tailoring skill; this "
        "file replaces its step 1 reads.", "",
        "## Truth rules (binding)", body_of(TRUTH).strip(), "",
        "## Keyword-matching steps", section(body_of(KEYWORD_SPEC), "Decisions"), "",
        "## Match-report shape (content model)", body_of(REPORT_MODEL).strip(), "",
        "## Résumé template: slot definitions (frontmatter)", "```yaml", tfm.strip(), "```", "",
        "## Résumé template: fixed text (search this for keyword matches)", tbody.strip(), "",
        f"## Professional profile §1-§15 (updated: {naming.task_fm(PROFILE).get('updated')})",
        profile_sections(REPORT_PROFILE),
    ])


def gate_report(f):
    if naming.is_frozen(f["task"]):
        return "frozen (Applied or later, D13)"
    return ""


LEXICON = False  # set by --lexicon: hints, the default for report batches (D28, blind test 2026-10-26)


def batch_report(f):
    exists = (f["folder"] / "match-report.md").exists()
    jd = jd_of(f["task"])
    out = head(f, [f"- write: {f['folder'] / 'match-report.md'}" + (" (exists: overwrite only if asked)" if exists else "")])
    if LEXICON:
        from package.keyword_lexicon import hints
        rows = hints(jd)  # the lexicon is rebuilt in main() first when a report is newer than it
        if rows:
            out += "\n".join([
                "### Known verdicts (lexicon: earlier reports agree; hints, not rows)",
                "Terms below appear in this JD and earlier reports judged them the same way against the current template. "
                "Choose the high-value terms yourself, as the spec says. When you choose one of these, you may use its "
                "verdict after confirming the quoted wording; don't add a row just because it is listed.", "",
                "| term | found as | where | action | backing | seen, agreement |", "| --- | --- | --- | --- | --- | --- |",
                *rows, ""])
    return out + "### Job description\n\n" + jd + "\n"


def fixed_letter():
    today = dt.date.today()
    return "\n".join([
        "# Cover-letter packet: fixed inputs",
        "Everything a cover letter needs that does not change per posting. Follow the cover-letter-writing skill; "
        "this file replaces its step 1 reads of the profile and truth rules.", "",
        f"## Letter shape ({naming.LETTER_TEMPLATE.relative_to(naming.ROOT).as_posix()})",
        "Body of cover-letter.md, after its frontmatter:", "", "```markdown",
        letter_head().format(date=f"{today:%B} {today.day}, {today:%Y}"), "", "<3-4 paragraphs, 250-350 words>", "",
        letter_tail(), "```",
        "Name the post author only when the JD names them, and never guess a name. One page. No < > { } \" or curly quotes (D9): "
        "quote the posting with single quotes. Render once per batch with `python3 pipeline/scripts/package/render_cover_letter.py "
        "<ids> --write`; the system python3 has every dependency.", "",
        "## Truth rules (binding)", body_of(TRUTH).strip(), "",
        f"## Professional profile §{', §'.join(map(str, LETTER_PROFILE))} (updated: {naming.task_fm(PROFILE).get('updated')})",
        profile_sections(LETTER_PROFILE),
    ])


def gate_letter(f):
    if naming.is_frozen(f["task"]):
        return "frozen (Applied or later, D13)"
    if not (f["folder"] / "resume.md").exists():
        return "no résumé yet (render it first)"
    return ""


def batch_letter(f):
    rep = f["folder"] / "match-report.md"
    rmd = body_of(rep) if rep.exists() else ""
    fields = "\n".join(f"- {r[0]}: {r[1]}" for r in table(rmd, "Fields") if len(r) >= 2)
    extra = [f"- Fit: {f['fit'] or '-'}; flags: {f['fit_flags'] or '-'}; gaps: {f['fit_gaps'] or '-'}",
             f"- write: {f['folder'] / 'cover-letter.md'}"]
    return head(f, extra) + "\n".join([
        "### résumé.md frontmatter (titles, numbers and gaps the letter must match)", "```yaml",
        frontmatter_text(f["folder"] / "resume.md"), "```", "",
        "### Match report: slot values", fields or "(no report)", "",
        "### Match report: count, gaps and flags", after_table(rmd, "Keywords") or "(no report)", "",
        "### Job description", "", jd_of(f["task"]), ""])


def fixed_interest():
    return "\n".join([
        "# Interest-brief packet: fixed inputs",
        "Follow the interest-statement skill's step 1 (Brief). Each posting's file section holds every input the brief "
        "needs: the JD, the match report's slot values, its keyword rows grouped by verdict, and the slot "
        "values, vocabulary and gaps the résumé frontmatter will hold. Don't read the profile, the full résumé or the cover letter (D19).", "",
        "- Evidence: choose from the 'present' rows only (exact, variant, synonym), and cite the résumé item named "
        "in their `where`.",
        "- Avoid: copy every 'absent' term, plus the report's requirement flags.",
        "- Role, Company and Industry: from the JD and the slot values, each bullet ending in its source.",
    ])


def gate_interest(f):
    verdict = next((v for v, p, _ in naming.interest_gate() if p == f["task"]), "skip: no match report")
    return "" if verdict == "ok" else verdict


def batch_interest(f):
    rmd = body_of(f["folder"] / "match-report.md")
    rows = [r for r in table(rmd, "Keywords") if len(r) >= 5]
    present = [r for r in rows if not r[1].startswith("absent")]
    absent = [r[0] for r in rows if r[1].startswith("absent")]
    fields = "\n".join(f"- {r[0]}: {r[1]}" for r in table(rmd, "Fields") if len(r) >= 2)
    # The same values render_resume.py writes to the résumé frontmatter, so the brief can start before the résumé exists.
    keep = {"slots": {r[0]: r[-1] for r in table(rmd, "Fields") if len(r) >= 2},
            "target_vocabulary": [r[0] for r in rows if not r[1].startswith("absent")],
            "gaps": absent}
    exists = (f["folder"] / "interest.md").exists()
    return head(f, [f"- write: {f['folder'] / 'interest.md'}" + (" (exists: overwrite only if asked)" if exists else "")]) + "\n".join([
        "### Match report: slot values", fields, "",
        "### Keyword rows present (term | found as | where | backing)",
        *[f"- {r[0]} | {r[1]} | {r[2]} | {r[4]}" for r in present], "",
        "### Keyword rows absent (Avoid)", ", ".join(absent) or "(none)", "",
        "### Match report: count, gaps and flags", after_table(rmd, "Keywords"), "",
        "### Slots, vocabulary and gaps (as the résumé frontmatter will hold them)", "```yaml",
        yaml.safe_dump(keep, allow_unicode=True, sort_keys=False).strip(), "```", "",
        "### Job description", "", jd_of(f["task"]), ""])


MODES = {"report": (fixed_report, gate_report, batch_report),
         "letter": (fixed_letter, gate_letter, batch_letter),
         "interest": (fixed_interest, gate_interest, batch_interest)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=MODES)
    ap.add_argument("job_ids", nargs="*")
    ap.add_argument("--due", action="store_true", help="report mode: every posting `naming.py reports` lists as due")
    ap.add_argument("--lexicon", action="store_true", help="report mode: add known verdicts from logs/lexicon.json (hints)")
    args = ap.parse_intermixed_args()
    global LEXICON
    LEXICON = args.lexicon
    if LEXICON:  # learn from the last wave first: rebuild when any match report is newer than the lexicon
        from package import keyword_lexicon
        newest = max((p.stat().st_mtime for p in naming.APPLICATIONS.glob("*/match-report.md")), default=0)
        if not keyword_lexicon.LEXICON.exists() or keyword_lexicon.LEXICON.stat().st_mtime < newest:
            keyword_lexicon.build(5, 0.9)
    ids = naming.field_ids()
    jids = list(args.job_ids)
    if args.due:
        jids += [naming.job_id(p, ids) for v, p, _ in naming.report_queue() if v == "due"]
    if not jids:
        sys.exit("error: name job ids (or pass --due in report mode)")
    fixed_fn, gate, batch_fn = MODES[args.mode]
    index = naming.index()
    OUT.mkdir(parents=True, exist_ok=True)

    fixed = fixed_fn()
    digest = hashlib.sha1(fixed.encode("utf-8")).hexdigest()[:10]
    fixed_path = OUT / f"{args.mode}-fixed-{digest}.md"
    if not fixed_path.exists():
        fixed_path.write_text(fixed, encoding="utf-8")

    parts, lines = [f"# {args.mode.capitalize()} packet: {dt.datetime.now():%Y-%m-%d %H:%M}",
                    f"Fixed inputs: {fixed_path}", ""], []
    for jid in jids:
        task = index.get(str(jid))
        if not task:
            lines.append(f"{jid}\trefused: no task with this Job ID")
            continue
        f = facts(task, ids)
        why = gate(f)
        if why:
            lines.append(f"{jid}\trefused: {why}\t{f['folder'].name}")
            continue
        parts.append(batch_fn(f))
        lines.append(f"{jid}\tok\t{f['folder'].name}")
    ok = sum(1 for ln in lines if "\tok\t" in ln)
    batch_path = OUT / f"{args.mode}-batch-{dt.datetime.now():%Y%m%d-%H%M%S}.md"
    if ok:
        batch_path.write_text("\n".join(parts), encoding="utf-8")
    words = lambda p: len(p.read_text(encoding="utf-8").split()) if p.exists() else 0
    print(f"fixed: {fixed_path} ({words(fixed_path)} words)")
    print(f"batch: {batch_path if ok else '(none: every posting refused)'}" + (f" ({words(batch_path)} words)" if ok else ""))
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
