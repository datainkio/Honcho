---
name: faqs
description: Given a MD file holding a list of questions for the candidate, use your insights into the applicant and the job description to produce meaningful and engaging answers. For each question, synthesize a 2-3 sentence answer using material from the resume or match report. Use when the user asks for a questions document or invokes /question-answers <job_id or title — company>.
---
# /faqs
Write one short answer statement per question. Application forms often include free-text fields. The answers are pasted, not rendered: there is no .docx or PDF.
This file is the only operational authority. Binding rules: the truth rules (`naming.py paths`, row `truth rules`). The answers claim nothing the match report or résumé does not back, and those trace to the dossier specified by the user in the currently selected profile.
## Usage

/faqs 4476502229
/faqs "Lead Product (UX) Designer — Mark43"
/faqs all  (every posting the gate passes that has no faqs.md yet)
## Paths
All paths are relative to the Honcho repo root. They contain spaces, so quote them and never backslash-escape.

| Input                                 | Path                                                |
| ------------------------------------- | --------------------------------------------------- |
| The posting (JD text + custom fields) | `applications/_tasks/<Company> - <Job title>.md |
| Match report (**required**)           | `applications/<task name>/match-report.md`                |
| Question set (user-supplied)          | the questions (`naming.py paths`, row `questions`)  |

| Output                | Path                                        |
| --------------------- | ------------------------------------------- |
| Brief, then the check | `applications/<task name>/src/questions-brief.md` |
| Answers               | `applications/<task name>/questions.md`           |
Never read the dossier (the match report's backing column and the résumé already trace to it) or the cover letter (the answers are written independently of it).

**The question set** is supplied by the user: a flat list, one question per item (a line, a bullet or a heading), with no sections or nesting. Every posting gets an answer to every item, in the list's order.

## Pipeline

### 0. Gate
Write only for postings that pass all three:

- **Status** labeled Prospect, resolved by label, never by id (the id `blocked` is labeled Applied). Every other stage is skipped.
- **Match report present** (`applications/<task name>/match-report.md`; the task's Has match report box). Don't fall back to the JD and résumé: the report's gap list is what keeps the answers honest. Report it as `no match report`.
- **Existing answers.** Don't overwrite `questions.md` unless the operator asks.

Never change a task's status.

### 1. Brief (Sonnet)
Read each posting's task note (the job description) and its match report: the slot values, the keyword rows (present, with where and backing, and absent), the gaps and the flags. No `resume.md` is needed: Evidence comes from the present rows and Avoid from the absent rows and flags. Write `src/questions-brief.md`:

```markdown
---
type: questions-brief
job_id: "<job_id>"
company: "<company, or 'Jobgether (employer unnamed)'>"
generated_at: <YYYY-MM-DD>
brief_by: sonnet
---

# Brief: <Company>, <Job title>

## Role
## Company
## Industry
## Evidence
## Avoid
```

Every bullet ends in its source in parentheses: `(JD: 'quoted phrase')`, `(report: hook_quality)`, `(resume: Seven Bridges bullet 2)`.
#### Role
2-4 reasons the role fits, from the report's `role_summary` and `hook_quality` and the JD.
#### Company
1-3 facts from the **JD only**, quoted: mission, product, users, values. No web lookup. If the employer is unnamed (a recruiter or Jobgether listing), say so, note only what the JD says about the team, and never name it.
#### Industry
1-2 reasons tied to the domain, each joined to résumé evidence, from the report's `related_projects` and `common_theme`.
#### Evidence
2-4 résumé items whose keyword rows in the report are exact, variant or synonym. Never an item that rests on an absent term.
#### Avoid
Every term the report lists as absent, plus any term the profile's honest-use notes rule out. These are never written, not even to describe the role.

### 2. Draft (Opus)

From the brief and the question set only, write questions.md:

```markdown
---
type: questions-answers
job_id: "<job_id>"
company: "<company>"
generated_at: <YYYY-MM-DD>
drafted_by: opus
checked_by: sonnet
sources: [task note JD, src/questions-brief.md, question set]
status: draft
---
<the answers>
```
Repeat each question from the set as a `##` heading, in order, with its answer below it.
#### For each question:
- 2-3 sentence, one paragraph, 120 words or fewer. First person.
- Restate the job description's own words where they fit.
- Silent on gaps. Never mention what the applicant lacks or is new to, and never use and Avoid term.
- No invented facts, motivation, or company claims beyond the brief. Numbers are permitted, but limit their use to maintain readibility.
- Write in a voice that is plain, specific, and confident. No clichés ('passionate', 'excited to leverage', 'dream role').
- No `< > { } "` or curly quotes. These will block form submission when present in text.
#### Tone and shape reference
> This role pairs research and design on a service people rely on, starting with how millions of Americans check a refund, and it asks for work that is 'simple, empathetic, and accessible'. Nava serves agencies 'constrained by legacy systems' through human-centered design and modern engineering, which is the kind of work I did at Bixal, adapting USWDS component libraries across SBA, USDA and Made in America. I want to keep doing government work because the results can be measured: I designed the digital-forms system behind the first randomized controlled trial of a federal form. This role asks for the same 'measurable outcomes'.
### 3. Check (Sonnet)

A different agent from the drafter reads the questions document and its brief, and appends a `## Check` section to `src/questions-brief.md`: a verdict (`pass` or `fix`) and, per problem, the exact phrase, the rule broken and a minimal replacement. Rules checked:

1. Every claim about the applicant traces to the brief's Role, Industry or Evidence bullets. Overstatement counts: 'led X' where the brief says they led part of X, a team or program result as their own, a motive the brief doesn't give.
2. Every claim about the company or role traces to the brief's Company or Role bullets.
3. No Avoid term appears, in any use.
4. Every question in the set is answered, each in 2-3 sentences.

The checker doesn't rewrite the answers.
### 4. Apply and lint
The main session applies each fix to questions.md` with the smallest change, **except** a replacement that brings back an Avoid term: drop the phrase instead. (In the pilot, the checker suggested 'explainable' for Jobgether, a gap term.) Then run `python3 pipeline/scripts/package/charset.py`, which must exit 0, and `python3 pipeline/scripts/tracking/task_links.py --write <job_id>...`, which checks each task's Has questions box and updates its progress (D38).
## Batches
One agent per pass takes up to five postings, so five postings cost three agents. Each agent's startup is most of its cost (about 50k tokens in the pilot), so never spawn one per posting. Pass the agent the job ids and the rules of its pass from this file, not file contents.
**Briefs start when the match reports land, not after the résumés** (elapsed-time plan step 3). The brief reads only the report, so spawn the brief agents for a report batch as soon as it is written, while Russ reviews it. If Russ edits a report's Fields table at approval, the brief is stale: run that posting's brief again before the draft.
**Flat, and spawned by the main session** (plan 2.6). No agent spawns another. On 2026-10-23 each Opus letter agent spawned its own brief and check agents, and their hand-backs landed in the Opus context: about 165k weighted tokens per posting. For each batch of five:
1. As soon as its reports are written (before approval): the brief agent (`model: sonnet`).
2. Once its résumés are rendered, in parallel: the letters agent (`model: opus`, cover-letter-writing skill) and, if the brief is done and not stale, the draft agent (`model: opus`). The answers never read the letter.
3. When the draft is done: the check agent (`model: sonnet`). It is a different agent from the drafter (D19).
Always pass `model` when spawning: a `general-purpose` agent without one inherits the session's model.
## Done when
1. `src/questions-brief.md` has the brief and a `## Check` section; `questions.md` has the frontmatter above and answers of 2-3 sentences for each of the questions listed.
2. Every check finding is applied or dropped as step 4 says.
3. `python3 pipeline/scripts/package/charset.py` exits 0.
4. The task's Has questions box is checked (`task_links.py --write <job_id>`).
## Report to the operator
- One line per posting: the path, the sentence and word counts, the check verdict, and each fix applied or dropped.
- Postings skipped by the gate, with the reason.
- Anything in an answer that states an intention the operator should confirm (such as 'where I want my next stretch of work to go').