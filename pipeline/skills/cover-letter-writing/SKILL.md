---
name: cover-letter-writing
model: opus
description: Write a posting-specific cover letter (cover-letter.md + "<Name> - <Title> - Cover Letter.docx") for one tracking posting, grounded in the professional profile, the JD, and that posting's résumé. Use when the user asks for a cover letter for a posting or invokes /cover-letter-writing <job_id or title — company>.
---

# /cover-letter-writing

Write one cover letter for one posting. It adds what the résumé can't: why this role, how two or three specific pieces of the candidate's work map to what the posting asks for, and why this employer. It never restates the résumé, and it never claims more than the professional profile supports.

**This file is the only operational authority: don't read the spec to run the skill.** The spec, [`pipeline/specs/cover-letter-skill-spec.md`](../../specs/cover-letter-skill-spec.md), holds only the rationale, decisions and changelog. The one exception is formatting: the letter must meet [`pipeline/specs/ats-formatting-spec.md`](../../specs/ats-formatting-spec.md). Authority for facts: the dossier (`naming.py paths`, row `dossier`); binding rules: the truth rules (`naming.py paths`, row `truth rules`). The résumé skill's truth boundary applies here unchanged. If this file and the profile disagree, the profile wins.

## Usage

```
/cover-letter-writing 4476509615
/cover-letter-writing "Senior UX Designer — Cricut"
```

One letter per posting. There is no title-cluster base: a letter is 1:1 with a posting, and unlike a résumé it can't be derived mechanically. When the operator asks for several letters, one agent writes up to five of them (see _Batches_ below): that spreads the reads across five letters without sharing any text between them.

## Paths

All paths are relative to the Honcho repo root. They contain spaces, so quote them and never backslash-escape.

| Input                                      | Path                                                                                               |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Professional profile (**source of truth**) | the dossier (`naming.py paths`, row `dossier`)                                                     |
| Truth rules (**binding**)                  | the truth rules (`naming.py paths`, row `truth rules`)                                             |
| The posting (JD text + custom fields)      | `applications/_tasks/<Company> - <Job title>.md`                               |
| That posting's résumé (must exist)         | `applications/<task name>/resume.md`                                                       |
| Fit report and flags                       | the task's **Fit**, **Fit flags**, **Fit gaps** fields, and the report they link in `logs/fit/` |

| Output              | Path                                                                          |
| ------------------- | ----------------------------------------------------------------------------- |
| Letter source       | `applications/<task name>/cover-letter.md`                            |
| Submission artifact | `applications/<task name>/<Name> - <Title> - Cover Letter.docx` |
| Write-back          | **Cover letter** custom field on the task: a wikilink to the `.docx` only     |

`<Title>` is the posting's job title as the JD gives it, **without the company**, with a trailing `[requisition code]` dropped and `/ \ : * ? " < > | # ^ [ ]` replaced by `-` (the same rule as résumés). The folder is `<job_id>` because titles repeat across employers. The letter's file name adds ` - Cover Letter` after the title, so it sits beside the résumé in the same folder without clashing.

`<Name>` is the `name:` in the profile's frontmatter.

**Fields are opaque ids.** Resolve _Cover letter_ (a `text` field, already defined), _Company_, _Fit_, _Fit gaps_ and the rest **by name** with `python3 pipeline/scripts/naming.py ids`. Never read the project note for them, and never hard-code an id.

## The truth boundary (binding)

Everything in the résumé skill's truth boundary applies, and every rule in the truth rules (`naming.py paths`, row `truth rules`) binds. The ones most likely to be broken by a letter:

- **No program-scale number as a personal outcome.** Use the framings in the truth rules and profile §11, and prefer the preferred proof the truth rules name.
- **No invented metrics, and no estimated ones.** Unmeasured work is design intent, not a shipped outcome.
- **Credential status, titles and current status** exactly as the truth rules give them. Don't raise an employment gap the truth rules say not to.

Letter-specific rules:

- **No invented motivation, connection, or company knowledge.** Don't write "I've followed your work for years", "I use your product", "a colleague told me", or any personal anecdote the operator hasn't supplied. Don't invent a recent launch, funding round, or news item. Company facts come only from the JD, or from a read-only company lookup (below). Anything personal that would strengthen the letter goes to the operator as a question, not into the draft.
- **Never close a gap with a claim.** The résumé's `gaps` list (and the task's _Fit gaps_) are required terms the profile doesn't back. The letter doesn't claim them. If a gap is central to the role, it may state the nearest honest adjacent experience in the profile in one clause, in plain words, and never "I'm the perfect candidate" or "I know I don't have much experience but…".
- **Consistency with the résumé.** Same titles, dates, and numbers. If the letter cites a number, it appears in the résumé or profile §10–§11.
- **Never write a seniority claim the résumé doesn't make.** A Staff or Principal posting doesn't make the candidate a former Staff or Principal.

## Pipeline (ordered)

### 0. Gate

- Read the task's **Fit**. Confirm with the operator before writing for Fit below 7, or for postings flagged `not-design-role`, `public-trust`, or location-ineligible.
- Confirm the posting's résumé exists. If not, run `/resume-tailoring` first. The letter reads the résumé so it doesn't duplicate it.
- Letters are written on request. Never submit or send anything, and never write outreach or follow-up messages (a separate deliverable).

### 1. Read

- **The packet.** Run `python3 pipeline/scripts/package/match_packet.py letter <job_id>…` and Read the two files it prints. The **fixed** file holds the letter's exact header, date line, salutation and sign-off, profile §2, §6, §7, §8, §10–§11 and §14 with its `updated:` date (`profile_version`), and the truth rules. The **batch** file holds, per posting, the path to write, the cleaned title, company, work type, Fit fields, the `resume.md` frontmatter (`target_vocabulary`, `gaps`, slots), the match report's slot values and gaps, and the JD. Postings it refuses (frozen, no résumé) are listed in its output. Don't read the renderer, an earlier letter, the profile or the task notes separately: the packet has what they would tell you.
- From the JD in the packet, note the named hiring contact, if it gives one.
- If the packet can't run, read the sources directly: the profile sections above by line range (`grep -n '^## '` first), the truth rules (`naming.py paths`, row `truth rules`), the task and the posting's `resume.md` frontmatter.

### 2. Gather company facts

Use only what's grounded:

1. The JD (mission, team, product, "About us" text).
2. Optionally `mcp__linkedin__get_company_profile` — read-only, but it drives the operator's real browser: confirm with the operator first, one call, and respect the human-paced rule in `CLAUDE.md`. Never use the messaging or connection tools.

If the employer is unnamed (flag `recruiter-unnamed-employer`) or the JD says little, write the "why this role" paragraph and skip the "why this company" one. Don't pad with flattery.

### 3. Choose the angle

- Pick the **two strongest matches** between the JD's top requirements and the profile's evidence. Choose ones the résumé doesn't lead with, or give the context the bullet can't.
- Pick one **signature theme** from profile §7 that makes the letter sound like the candidate and not a generic senior designer.
- Match the domain: healthcare, civic/federal, data/AI, and brand each have their own lead evidence in profile §6.
- Pick the tone from the table below.

### 4. Draft

**Three to four paragraphs, one page, roughly 250–350 words.** Every paragraph earns its place.

1. **Opening — why this role.** A specific reason this posting caught the candidate's attention, taken from the JD. If a direct, true connection exists (domain expertise, or a connection the operator stated), say it in the first line. Never open with "I am writing to express my interest…" or "I am excited to apply…".
2. **Why the candidate — the match.** The two chosen matches, each with brief context and the honest framing of its number. Use the JD's own words where the profile backs them. Don't repeat résumé bullets.
3. **Why this company** (only with grounded facts). One concrete thing from the JD or company profile, and why it matters to the work the candidate does. Generic flattery doesn't count. Cut the paragraph if there's nothing concrete.
4. **Close.** A clear, confident next step: an offer to discuss how the candidate's experience in X could support the team's work on Y. Not desperate, not demanding.

The header, address and salutation follow the letter template (`naming.py paths`, row `letter template`), as the packet states them: address and greet the post author by first name only if the JD names them, otherwise "Dear <Organization>," and never guess a name. Sign off "Sincerely," followed by `<Name>`.

**Voice.** Profile §14: plain, specific, evidence-led, no empty jargon ("synergy", filler "seamless"), no self-congratulation. First person, active.

**Tone by employer type** (read the JD to calibrate):

| Employer                                | Tone                                                                                                                                                |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Startup / product company               | Conversational, direct; lead with the work                                                                                                          |
| Enterprise / health system              | Professional, measured; lead with scale and complexity handled                                                                                      |
| Government / civic / federal contractor | Formal and criteria-aware. If the JD lists qualifications or selection criteria, address them in order. Use plain language, as the work itself does |
| Agency / consultancy                    | Craft and collaboration forward; client-facing range                                                                                                |
| Non-profit / mission-driven             | Mission-aligned, only if the candidate's real work backs the alignment                                                                                       |

### 5. Self-check

- [ ] No sentence could be sent unchanged to 50 other companies
- [ ] No résumé bullet restated; no new fact absent from the profile
- [ ] Every number traces to profile §10–§11 and matches the résumé, with its honest framing
- [ ] No invented motivation, connection, or company fact; open questions listed for the operator
- [ ] No gap closed by a claim; no seniority claim the résumé lacks
- [ ] Every item in the truth-rules checklist holds
- [ ] Posting title used exactly as the JD gives it
- [ ] Meets every rule in the [ATS formatting spec](../../specs/ats-formatting-spec.md) (one page, same header as the résumé)
- [ ] Voice intact (§14)
- [ ] No `< > { } "` or curly quotes (D9): quote the posting with single quotes, write `p under 0.10`. `python3 pipeline/scripts/package/charset.py` must exit 0; the renderer refuses otherwise

### 6. Render and write back

1. Write `applications/<task name>/cover-letter.md` in **one** `Write`, with this frontmatter, then the letter (header, date, salutation, the paragraphs, sign-off). Run the step 5 self-check on the draft before writing it, so the file is final when written:

```yaml
---
type: cover-letter
job_id: <job_id>
target_title: "<posting title, no company>"
company: "<company>"
resume: resume.md
generated_at: <ISO timestamp>
profile_version: <profile updated: date>
angle: "<one line: the two matches + the theme>"
company_facts: ["<fact>  (source: JD | company profile)"]
open_questions: ["<anything personal the candidate could add>"]
honesty_review: passed       # only after step 5
---
```

2. Lint and render, once per batch rather than per letter: `python3 pipeline/scripts/package/charset.py`, then `python3 pipeline/scripts/package/render_cover_letter.py <job_id>… --write` with every job id in the batch. The system `python3` has every dependency. It renders `<Name> - <Title> - Cover Letter.docx` beside `cover-letter.md` with the same renderer as the résumés, and refuses unless `honesty_review: passed` and the posting's résumé exists. The `.docx` is never hand-edited.
3. The script sets the task's **Cover letter** field (its backup goes to the scratchpad). The value is `"[[applications/<task name>/<Name> - <Title> - Cover Letter.docx|Cover letter]]"`. Set only that field, and back up the task first when editing more than one.
4. Never change the task's status. Application stages move only when the operator asks.

### Batches

When asked for several letters, take up to five per agent. A letter agent writes letters only: it never spawns another agent, and interest statements are separate agents the main session spawns (interest-statement skill, Batches). For each posting, do steps 0–5 and the one `Write`. Don't re-read a letter after writing it, and don't render between letters. When all five are written, lint and render them in one call (step 6.2). Fix only what the linter or renderer reports, then re-run that call. Opus writes the letters: the letter is the product.

### A résumé regenerated later

A letter cites the résumé's titles and numbers. If the posting's `resume.md` has a newer `generated_at` than the letter, the letter is stale: re-check its numbers and titles before it's used. Never for a posting at Applied or later (D13).

## Done when

1. `cover-letter.md` and the `.docx` exist, named as above; the `.docx` opens cleanly and fits one page.
2. The step 5 checklist passes and `honesty_review: passed`.
3. The task's **Cover letter** field links the `.docx`.

## Report to the operator

- The letter's path and its `angle`.
- **`open_questions`**: personal or company-specific details the candidate could add to strengthen it.
- Any required JD term left unaddressed (the résumé's `gaps`) and how the letter handled it.
- Anything skipped, such as the company paragraph for an unnamed employer, and why.

**Task note links.** Each task's body starts with a `<!-- links -->` block (Posting, Résumé, Cover letter; "no resume" / "no cover letter" when a file is missing). It is built from the files on disk by `pipeline/scripts/tracking/task_links.py`, which the render scripts call. Run `python3 pipeline/scripts/tracking/task_links.py --write` after any change made by hand.
