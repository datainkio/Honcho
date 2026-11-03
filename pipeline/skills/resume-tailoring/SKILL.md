---
name: resume-tailoring
model: opus
description: Generate a posting-specific, ATS-friendly résumé ("<Name> - <Title>.docx" + resume.md) by filling the slots of a fixed résumé template, with a match report reviewed before render. Use when the user asks to produce a resume tailored for a particular job post. Invokes /resume-tailoring. Honest tailoring only — slot values, never invention.
---

# /resume-tailoring

Given a **target job posting**, produce an instance of the resume template tuned to that title and the role’s requirements and expectations stated within its description — maximizing the odds the application is viewed and yields an interview.

The goal is to produce a résumé that is both tailored to the job posting and ATS-friendly.

**This file is the only operational authority: don't read the spec to run the skill.** The spec, [`pipeline/specs/resume-tailoring-skill-spec.md`](../../specs/resume-tailoring-skill-spec.md), keeps only the rationale and the changelog. Two specs are read as part of the run: the [keyword-matching spec](../../specs/keyword-matching-spec.md) (step 3) and the [ATS formatting spec](../../specs/ats-formatting-spec.md) (step 5).

## How the résumé is made

The résumé template (`naming.py paths`, row `résumé template`) is pre-approved fixed text with a few **slots**, marked `{{ name }}` and defined in its frontmatter. The skill's only edit to the résumé is supplying the slot values. It never rewrites fixed text. Keyword matching then proposes wording changes in the match report, and Russ decides what to change in the template (the tune loop). This is the résumé half of the application-creation flow in [`reference/journeys/application creation.canvas`](../../../reference/journeys/application%20creation.canvas).

## Usage

```
/resume-tailoring 4476502229
/resume-tailoring "Nava - Designer/Researcher, Senior - Interactive Voice Response (IVR)"
```

One posting per run, named by job id or task name. Fit and prioritization are out of scope: the skill runs on the posting it's given.

**Batches (D27).** When asked for match reports across a run rather than for named postings, take the list from `python3 pipeline/scripts/naming.py reports`, and write only for its `due` rows: Prospects at priority critical with no report yet. Skip the `skip:` rows. They were triaged down at the fold (over 100 applicants) or by Russ, and a report for a posting that is then dropped is wasted. A posting Russ names gets its report whatever its priority.

## Paths

All paths are relative to the Honcho repo root. They contain spaces, so quote them and never backslash-escape.

| Input                                      | Path                                                                 |
| ------------------------------------------ | -------------------------------------------------------------------- |
| Professional profile (**source of truth**) | the dossier (`naming.py paths`, row `dossier`)                       |
| Truth rules (**binding**)                  | the truth rules (`naming.py paths`, row `truth rules`)               |
| Job description                            | `applications/_tasks/<Company> - <Job title>.md` |
| Résumé template                            | the résumé template (`naming.py paths`, row `résumé template`)       |
| Match report model                         | `reference/content models/Match Report.md`                           |

| Output                                | Path                                                                                                                                    |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Match report (reviewed before render) | `applications/<task name>/match-report.md`                                                                                      |
| Résumé source                         | `applications/<task name>/resume.md`                                                                                            |
| Submission artifact                   | `applications/<task name>/<Name> - <Title>.docx`                                                                                |
| PDF copy                              | `applications/<task name>/<Name> - <Title>.pdf`                                                                                 |
| Write-back                            | **Résumé variant** custom field on `applications/_tasks/<Company> - <Job title>.md`: a wikilink to the `.docx` only |

**Job records are dotpm tasks.** Each posting is one task; the JD text is the note body and the JD metadata is in `customFields`, keyed by opaque field id. Resolve ids **by name** with `python3 pipeline/scripts/naming.py ids`: never read the project note for them, and never hard-code an id. The task `title` is `<Company> - <Job title>`; the task `status` is the application stage, and postings at Applied or later are frozen (D13).

`<Name>` = the `name:` in the profile's frontmatter. `<Title>` = the posting's job title without the company (`naming.job_title()`), made file-safe by `naming.safe()`. The folder is the task's name (`naming.task_folder()`). The recruiter sees the file name; the folder never reaches the employer.

## The truth boundary (binding)

Every slot value and every proposed swap traces to the profile or its cited source records.

- **The truth-rules file binds.** The truth rules (`naming.py paths`, row `truth rules`) list the candidate's specific traps. Every rule in it applies to every slot value.
- **No invented metrics, no program-scale numbers as personal outcomes.** (profile §10, §11, §15)
- **Voice.** Use the profile's language kit (§14); no empty jargon, no self-congratulation.
- **A JD term the profile doesn't back is a gap.** It goes in the match report, never into a slot or a swap.

## Pipeline

### 0. Resolve the posting

- Find the task: `naming.find_task(<job_id>)`, or by task name. Read its body (the JD) and its _Company_ field.
- **Frozen check:** if `naming.is_frozen(task)` (Applied, Screening or any "done" status), stop. Submitted material is never re-rendered (D13).

### 1. Read the packet

Run `python3 pipeline/scripts/package/match_packet.py report --lexicon <job_id>…` (a batch from `naming.py reports`: `--due --lexicon`). It prints two paths; Read both. The **fixed** file holds the truth rules, the keyword-matching steps, the match-report shape, the template's slot definitions and fixed text, and profile §1–§15 with its `updated:` date. The **batch** file holds, per posting, the task path, the folder to write to, the cleaned `job_title`, company, location, work type and the JD. Postings the packet refuses (frozen, no task) are listed in its output and are not written. Don't read those sources again, list `applications/`, or compute folder names: the packet did.

`--lexicon` adds, per posting, known verdicts from earlier reports for terms in its JD, rebuilding the lexicon first when a report is newer (D28). Always pass it: in the 2026-10-26 blind test, hinted Opus reports ranked first for every posting with no verdict errors. A hint never adds a row: you still choose the high-value terms, and keep the count within 25-35.

If the packet can't run, read the sources directly: profile §1–§15, the truth rules in full, then the template's `slots:` block and fixed text.

### 2. Fill the slots

Supply a value for every agent-owned slot in the template's `slots:` block. Each value follows that slot's `source`, `form` and `length`, and must read correctly in the sentence around it.

- `job_title` and `job_title_article` are filled by the render script. Record them in the report for reading, but don't hand-edit them.
- `related_projects`: 2–3 options exactly as listed, joined as one phrase ('SBA.gov and Forms.gov'; 'A, B and C'). Choose the projects whose work the posting most resembles.
- `common_theme` must be true of every chosen project per the profile.
- No `< > { } "` or curly quotes in any value (D9).

### 3. Keyword matching → match report

Run the [keyword-matching spec](../../specs/keyword-matching-spec.md) on the template with the slots filled, and write `applications/<task name>/match-report.md` in the shape of the [match report model](../../../reference/content%20models/Match%20Report.md):

- Frontmatter: `type: match-report`, `job_id`, `generated_at`, `profile_version`. Approval is not recorded in the report (step 4); a `status` key in older reports is ignored.
- **Fields** table: `| slot | value |`, one row per slot, then the Summary sentence as it will read.
- **Keywords** table: term, found as, where, action, backing.
- **Count** against the 25–35 target, and **Gaps**: bullets only, one short line per absent term or shortfall, grouped as no backing, backed with no template wording, and partly backed. No paragraphs.
- No **Slot choices** prose. The Fields table is the record of the slots; the posting wording behind a choice is not written out. Add a line only where Russ must decide something the table can't show (for example, a slot with two reasonable values).

**Flags** (D28): after the Gaps, list the eligibility facts Russ needs before approving. Name a location the profile's 'Baltimore, MD + remote' doesn't meet (remote limited to other states, hybrid or on-site elsewhere, another country). Quote any pay range the JD states, without judging it. Note contract or staffing-firm terms, clearance, travel and required degrees. Write 'Flags: none' when there are none.

Actions are **proposals**. Never apply them to the template or to `resume.md`. Mark a term found only in a slot as such in its `where` cell: slots describe the posting, not the candidate's experience.

### 4. Stop for review

Report to Russ (see Run output) and stop. Russ reviews the match report and either:

- **passes** it: checks the task's **Matching approved** box (a dotpm checkbox field), possibly after editing slot values in the report's Fields table; or
- **fails** it: tunes the template's fixed text, the profile or the slot values, then asks for step 3 again.

Never check Matching approved yourself (D22).

### 5. Render and write back

Once the task's Matching approved box is checked:

```bash
python3 pipeline/scripts/package/render_resume.py <job_id>           # dry run: slot values and file names
python3 pipeline/scripts/package/render_resume.py <job_id> --write   # resume.md, .docx, .pdf, Résumé variant link
```

The script fills the template from the report's Fields table, refuses a task whose Matching approved box is unchecked, a frozen posting, an unfilled slot or a forbidden character, renders per the [ATS formatting spec](../../specs/ats-formatting-spec.md), and sets the task's Résumé variant to the `.docx` and refreshes its links block.

Then the cover letter (`/cover-letter-writing`) and interest statement (`/interest-statement`) complete the application package.

## Done when (acceptance criteria)

1. `match-report.md` exists with the Fields table, the Keywords table, the Count and the Gaps, and the task's Matching approved box is checked by Russ.
2. The count of present terms is within 25–35, or the shortfall is recorded as a gap.
3. `resume.md`, `<Name> - <Title>.docx` and `<Name> - <Title>.pdf` exist; the `.docx` opens cleanly; `python3 pipeline/scripts/package/charset.py` exits 0.
4. The task's Résumé variant holds the `.docx` link.

## Run output (report to operator)

- After step 3: the slot values and the Summary sentence as it reads, the count against 25–35, the gaps (backed and unbacked), and the proposed swaps.
- After step 5: the file paths.

**Task note links.** Each task's body starts with a `<!-- links -->` block (Posting, Résumé, Cover letter). It is built from the files on disk by `pipeline/scripts/tracking/task_links.py`, which the render scripts call. Run `python3 pipeline/scripts/tracking/task_links.py --write` after any change made by hand.
