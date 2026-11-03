---
name: interest-statement
description: Write a posting's 3-5 sentence answer to 'Why are you interested in this role, company, and industry?' (why-interested.md, with its brief in interest.md), from the posting's JD, match report and résumé. Use when the user asks for an interest statement or a 'why this role' answer for a posting, or invokes /interest-statement <job_id or title — company>.
---

# /interest-statement

Write one short paragraph per posting that answers some form of 'Why are you interested in this role, company, and industry?'. Application forms ask it as a free-text field. The answer is pasted, not rendered: there is no `.docx`.

**This file is the only operational authority.** The why is [D19](../../../context/decisions.md). Binding rules: the truth rules (`naming.py paths`, row `truth rules`). The statement claims nothing the match report or résumé doesn't back, and those trace to the dossier (`naming.py paths`, row `dossier`).

## Usage

```
/interest-statement 4476502229
/interest-statement "Lead Product (UX) Designer — Mark43"
/interest-statement all          # every posting the gate passes that has no statement yet
```

## Paths

All paths are relative to the Honcho repo root. They contain spaces, so quote them and never backslash-escape.

| Input                                       | Path                                                 |     |
| ------------------------------------------- | ---------------------------------------------------- | --- |
| The posting (JD text + custom fields)       | `applications/_tasks/<Company> - <Job title>.md` |     |
| Match report (**required**)                 | `applications/<task name>/match-report.md`                 |     |
| Résumé (optional; not needed for the brief) | `applications/<task name>/resume.md`                       |     |

| Output | Path |
| --- | --- |
| Brief, then the check | `applications/<task name>/interest.md` |
| Statement | `applications/<task name>/why-interested.md` |

Never read the profile (the match report's backing column and the résumé already trace to it) or the cover letter (the statement is written independently of it).

## Pipeline

### 0. Gate

Run `python3 pipeline/scripts/naming.py interest`. It lists every posting that has a match report, as `ok` or `skip: <reason>`, and whether a statement exists. Write only for `ok` rows:

- **Status** labeled Prospect (`naming.interest_statuses()`, resolved by label). Every other stage is skipped: Preparing, Blocked, and everything from Applied on (D13). The status id `blocked` is labeled **Applied**, not Blocked.
- **Match report present.** A posting without one isn't listed. Don't fall back to the JD and résumé: the report's gap list is what keeps the statement honest. Report it as `no match report`.
- **Existing statement.** Don't overwrite `why-interested.md` unless the operator asks.

Never change a task's status.

### 1. Brief (Sonnet)

Run `python3 pipeline/scripts/package/match_packet.py interest <job_id>…` and Read the batch file it prints. Per posting it holds the JD, the match report's slot values, its keyword rows grouped as present (with `where` and backing) and absent, its gaps and flags, and the slot values, vocabulary and gaps the `resume.md` frontmatter will hold (derived from the report, so no `resume.md` is needed). The gate is applied there too: refused postings are listed in its output. Don't read the task note, the full `resume.md` or the match report separately: Evidence comes from the present rows and Avoid from the absent rows and flags. Write `interest.md`:

```markdown
---
type: interest-brief
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

- **Role:** 2-4 reasons the role fits, from the report's `role_summary` and `hook_quality` and the JD.
- **Company:** 1-3 facts from the **JD only**, quoted: mission, product, users, values. No web lookup. If the employer is unnamed (a recruiter or Jobgether listing), say so, note only what the JD says about the team, and never name it.
- **Industry:** 1-2 reasons tied to the domain, each joined to résumé evidence, from the report's `related_projects` and `common_theme`.
- **Evidence:** 2-4 résumé items whose keyword rows in the report are exact, variant or synonym. Never an item that rests on an absent term.
- **Avoid:** every term the report lists as absent, plus any term the profile's honest-use notes rule out. These are never written, not even to describe the role.

Under 350 words. Program-scale numbers are never the candidate's personal results.

### 2. Draft (Opus)

From the brief only, write `why-interested.md`:

```markdown
---
type: why-interested
job_id: "<job_id>"
company: "<company>"
generated_at: <YYYY-MM-DD>
drafted_by: opus
checked_by: sonnet
sources: [task note JD, match-report.md]
status: draft
---

<the paragraph>
```

- 3-5 sentences, one paragraph, 120 words or fewer. First person.
- Role, then company, then industry, grounded in one or two Evidence items. Quote the JD's own words in single quotes where they fit.
- **Silent on gaps:** never mention what the candidate lacks or is new to, and never use an Avoid term.
- No invented facts, motivation or company claims beyond the brief. Prefer no numbers.
- Plain, specific, confident. No clichés ('passionate', 'excited to leverage', 'dream role').
- No `< > { } "` or curly quotes (D9).

Tone and shape reference (Nava, approved 2026-10-16):

> This role pairs research and design on a service people rely on, starting with how millions of Americans check a refund, and it asks for work that is 'simple, empathetic, and accessible'. Nava serves agencies 'constrained by legacy systems' through human-centered design and modern engineering, which is the kind of work I did at Bixal, adapting USWDS component libraries across SBA, USDA and Made in America. I want to keep doing government work because the results can be measured: I designed the digital-forms system behind the first randomized controlled trial of a federal form. This role asks for the same 'measurable outcomes'.

### 3. Check (Sonnet)

A different agent from the drafter reads the statement and its brief, and appends a `## Check` section to `interest.md`: a verdict (`pass` or `fix`) and, per problem, the exact phrase, the rule broken and a minimal replacement. Rules checked:

1. Every claim about the candidate traces to the brief's Role, Industry or Evidence bullets. Overstatement counts: 'led X' where the brief says he led part of X, a team or program result as his own, a motive the brief doesn't give.
2. Every claim about the company or role traces to the brief's Company or Role bullets.
3. No Avoid term appears, in any use.
4. Every single-quoted phrase appears in the brief.
5. 3-5 sentences.

The checker doesn't rewrite the statement.

### 4. Apply and lint

The main session applies each fix to `why-interested.md` with the smallest change, **except** a replacement that brings back an Avoid term: drop the phrase instead. (In the pilot, the checker suggested 'explainable' for Jobgether, a gap term.) Then run `python3 pipeline/scripts/package/charset.py`, which must exit 0.

## Batches

One agent per pass takes up to five postings, so five postings cost three agents. Each agent's startup is most of its cost (about 50k tokens in the pilot), so never spawn one per posting. Pass the agent the packet's batch path and the rules of its pass from this file, not file contents.

**Briefs start when the match reports land, not after the résumés** (elapsed-time plan step 3). The brief reads only the report, so spawn the brief agents for a report batch as soon as it is written, while Russ reviews it. If Russ edits a report's Fields table at approval, `naming.py interest` shows `brief stale`: run that posting's brief again before the draft.

**Flat, and spawned by the main session** (plan 2.6). No agent spawns another. On 2026-10-23 each Opus letter agent spawned its own brief and check agents, and their hand-backs landed in the Opus context: about 165k weighted tokens per posting. For each batch of five:

1. As soon as its reports are written (before approval): the brief agent (`model: sonnet`).
2. Once its résumés are rendered, in parallel: the letters agent (`model: opus`, cover-letter-writing skill) and, if the brief is done and not stale, the draft agent (`model: opus`). The statement never reads the letter.
3. When the draft is done: the check agent (`model: sonnet`). It is a different agent from the drafter (D19).

Always pass `model` when spawning: a `general-purpose` agent without one inherits the session's model.

## Done when

1. `interest.md` has the brief and a `## Check` section; `why-interested.md` has the frontmatter above and a paragraph of 3-5 sentences.
2. Every check finding is applied or dropped as step 4 says.
3. `python3 pipeline/scripts/package/charset.py` exits 0.

## Report to the operator

- One line per posting: the path, the sentence and word counts, the check verdict, and each fix applied or dropped.
- Postings skipped by the gate, with the reason.
- Anything in a statement that states an intention the operator should confirm (such as 'where I want my next stretch of work to go').
