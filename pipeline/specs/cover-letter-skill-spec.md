---
title: Cover-Letter Skill Spec
aliases:
  - Cover Letter Writing Spec
id: automation.skill.cover-letter-writing
type: spec
status: accepted
created: 2026-10-07
updated: 2026-10-12
version: 0.3.0
owner: Russell Lebo
project: LinkedIn Job-Retrieval Automation
scope:
  - job search
  - cover letters
  - agent-run skill
  - business development
summary: >-
  Specification for a cover-letter skill: given one Application Tracking posting, it writes a
  one-page letter that adds what the résumé can't (why this role, two or three matches, why this
  employer), grounded only in the professional profile, the job description, and that posting's
  résumé. It never invents motivation, connections, or company knowledge, and it never closes a
  résumé gap with a claim.
audience:
  - Claude Code
  - Russell Lebo
primary_audience: Claude Code
tools:
  - Claude Code
  - docx (skill)
tags:
  - automation
  - business-development
  - cover-letter
  - job-search
  - skill
  - spec
related:
  - "[[Résumé-Tailoring Skill Spec]]"
  - "[[Russell Lebo — Professional Profile]]"
  - "[[LinkedIn Job-Retrieval Automation]]"
---

# Cover-Letter Skill Spec

## 0. Purpose

A cover letter is the one application document where a reader can hear Russ's reasoning. This skill writes one per posting, on request, so that:

1. It says something the résumé doesn't: a specific reason for this role, two or three matches between the posting and his work, and (when there is something concrete to say) why this employer.
2. Every claim traces to the professional profile (the dossier; `naming.py paths`, row `dossier`). The truth rules of the [résumé spec](resume-tailoring-skill-spec.md) §7 apply unchanged.
3. It stays consistent with the posting's own résumé: same titles, dates, and numbers.

**The skill, [`pipeline/skills/cover-letter-writing/SKILL.md`](../skills/cover-letter-writing/SKILL.md), is the only operational authority** (paths, truth rules, pipeline, structure, tone, self-check, acceptance). This spec keeps why it is built that way, so an agent running the skill never needs to read it (F6 of [`../context/token-efficiency-review.md`](../context/token-efficiency-review.md)).

### 0.1 Design decisions

| Decision | Choice | Why |
| --- | --- | --- |
| Granularity | One letter per posting (1:1) | A letter that could go to 50 employers is the failure mode. Nothing useful can be shared between postings, so there is no title-cluster base as there is for résumés. |
| Dependency | The posting's résumé must exist first | The letter reads it so it complements and doesn't restate it, and so numbers and titles agree. |
| Company knowledge | Only from the JD, or an operator-approved read-only company lookup | An agent that "researches" freely invents. Grounded facts or nothing. |
| Personal motivation | Never invented; asked as `open_questions` | "I've followed your work for years" is a claim only Russ can make. |
| Trigger | On request; up to five postings per agent, still one letter each | Nothing is sent or submitted by the skill. A batch spreads the profile and skill reads over five letters; no text is shared between them. |
| Batch mechanics | One `Write` per letter, one lint and render call per batch | Cost tracks calls, not letter length: each call re-reads everything the agent has read and written (130k–310k tokens per letter when written, linted and rendered one at a time). |
| Profile reads | By section (§2, §6–§8, §10–§11, §14), not the whole file | About 40% of the profile's 10.5k tokens. |
| Model | Opus for drafting | The letter is the product; output tokens are a minor cost here. A cheaper model would be tested blind on the same postings first, not adopted by default. |

## 1. Out of scope

- **Sending or submitting** anything, including LinkedIn messaging. Use of `send_message` or `connect_with_person` needs an explicit request.
- **Outreach and follow-up messages** (a separate deliverable).
- **A letter base per title cluster.** Rejected in §0.1.

## 2. Open questions

- ~~**Automating the render.**~~ Done: `pipeline/scripts/package/render_cover_letter.py` renders `cover-letter.md` with the résumé renderer and sets the task field. Writing the letter stays the skill's job.
- **Feedback loop.** Whether interview outcomes should feed back into which angles and themes are chosen.

## 3. Changelog

- **0.3.0 (2026-10-12)** — The skill becomes the only operational authority; this spec keeps purpose, decisions, scope, open questions and changelog. Batches of up to five letters per agent, one `Write` each and one render call per batch (`render_cover_letter.py` takes several job ids). The profile is read by section. Field ids come from `python3 pipeline/scripts/naming.py ids`.
- **0.2.0 (2026-10-08)** — Letters live in the posting's own folder, `applications/<Company> - <Job title>/`, beside the résumé (`cover-letter.md`; `… - Cover Letter.docx`). The `cover-letters/` folder is retired.
- **0.1.1 (2026-10-07)** — Paths follow the new task naming: letters live in `../data/cover-letters/<Company> - <Job title>/`, the same stem as the posting's task note.
- **0.1.0 (2026-10-07)** — Initial specification. One letter per posting, written after that posting's résumé, grounded in the profile, the JD, and an optional approved company lookup. File name `Russell Lebo - <Title>.docx` in `../data/cover-letters/<job_id>/`. The **Cover letter** task field links the `.docx`. Includes the letter-specific honesty rules (no invented motivation, connection, or company knowledge) and the gate, structure, tone and self-check.
