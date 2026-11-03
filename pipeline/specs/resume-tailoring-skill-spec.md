---
title: Résumé-Tailoring Skill Spec
aliases:
  - Title-Tailored Résumé Spec
  - Résumé Tailoring Spec
  - Resume Variant Generation Spec
id: automation.skill.resume-tailoring
type: spec
status: accepted
created: 2026-07-22
updated: 2026-10-20
version: 0.12.0
owner: Russell Lebo
project: LinkedIn Job-Retrieval Automation
scope:
  - job search
  - résumé generation
  - ATS optimization
  - agent-run skill
  - business development
summary: >-
  Specification for a résumé-tailoring skill: for one posting, it fills the bounded slots
  of a fixed, pre-approved résumé template, runs keyword matching against the posting's
  description, and renders an ATS-friendly .docx. The goal is to maximize the likelihood
  that the application is viewed and yields an interview while maintaining accessibility and readibility for human reviewers.
audience:
  - Claude Code
  - Russell Lebo
  - job-search operators
primary_audience: Claude Code
tools:
  - Claude Code
  - docx (skill)
tags:
  - ats
  - automation
  - business-development
  - job-search
  - resume
  - skill
  - spec
related:
  - "[[LinkedIn Job-Retrieval Automation]]"
  - "[[Russell Lebo — Professional Profile]]"
  - "[[Information Architecture Skill Spec]]"
---

# Résumé-Tailoring Skill Spec

**The skill, [`pipeline/skills/resume-tailoring/SKILL.md`](../skills/resume-tailoring/SKILL.md), is the only operational authority**: paths, the truth boundary, the pipeline, frontmatter, both checklists, rendering, write-back and acceptance. This spec keeps why the skill is built that way, the research behind it and its history.

## Purpose

This specification defines a **résumé-tailoring skill** for the job-search workflow:

> Given a **target job posting**, produce an instance of the resume template tuned to the job's title and the requirements and expectations stated within its description — maximizing the odds the application is viewed and yields an interview.

---

## Signaling for ATS parsers

### Formatting

- File format, layout, headings, typography and dates follow the [ATS formatting spec](ats-formatting-spec.md).

### Keyword matching

- [The final product is optimized for visibility within ATS by reflecting the vocabulary used in the job description](../../reference/content%20models/Match%20Report.md). The identification and matching process is defined in the [keyword-matching spec](keyword-matching-spec.md).
- Once keywords are identified, keyword matching happens in two passes. First, the dynamic content is tuned to include keywords where appropriate. Second, the resume owner (Russ) reviews the rendered match report and adjusts the template manually to maximize their presence.

### Recency

- The latest role's heading is fixed text. It no longer echoes the posted job title: the `job_title_short` slot was removed on 2026-10-21
- Date format: see the [ATS formatting spec](ats-formatting-spec.md)

### Timing (lever 1)

A key performance metric is the amount of time between when the job was posted and when the complete application was submitted. Support speedy action by:

- prioritizing fresh, high-fit postings in terms of effort and visibility,
- reducing the overhead and time required to add a tailored resume to the application.

## Review points

The template is pre-approved fixed text. The skill changes it in only one way: it supplies appropriate values for the slots. Russ reviews the output twice:

1. The match report from keyword matching, before any wording changes are applied.
2. The rendered document.

---

## Open questions & out of scope

### Out of scope for MVP

- **Fit and prioritization** (D20). The skill runs on the posting it's given. Fit is set by the [fit rubric](../context/fit-rubric.md); automated scoring ([calculate-fit-score spec](calculate-fit-score-spec.md)) waits until the package output is confirmed.
- **Outreach copy** (profile §2 supplies openers, but that is a separate deliverable). Cover letters have their own skill.
- **Application submission** and any LinkedIn write action — retrieval and this skill are read/generate only.

### Open questions

- **Code-orchestrated alternative.** Mirroring D2, a script that parses JDs, computes term overlap, and renders variants could make runs repeatable/batchable — worth it only once volume justifies the maintenance. Deferred.
- **Feedback loop.** Should interview-yield outcomes (from the job ledger CSV) feed back to reweight target vocabulary or fit scores?

---

## Changelog

- **0.12.0 (2026-10-20)** — Approval moves from the match report's `status: approved` to the task's **Matching approved** checkbox (D22). `render_resume.py` reads only the checkbox; reports no longer carry a `status`.
- **0.11.0 (2026-10-19)** — The skill is rewritten to this flow (D20): one posting per run; slots filled; keyword matching writes proposals to the match report; Russ approves it (`status: approved`) before `pipeline/scripts/package/render_resume.py` renders. Fit and the honesty review are out of scope for now.
- **0.10.0 (2026-10-15)** — Résumés are now rendered from one fixed, pre-approved template (the résumé template; `naming.py paths`, row `résumé template`) whose bounded slots hold words or phrases, never narrative. The per-title-cluster base (`master.md`) and the derive-per-posting step are retired. After the slots are filled, the [keyword-matching](keyword-matching-spec.md) process aligns the document's vocabulary with the posting and writes a match report. Russ reviews twice: the match report, then the rendered document. The two-page limit is gone (D18). The ATS research moved to the Research ATS parsing task; the worked example and the prior-art tables were removed. The skill is not yet updated to this flow.
- **0.9.0 (2026-10-12)** — The skill becomes the only operational authority. This spec keeps purpose, the response model, cluster rationale, ATS research, the worked example, prior art, open questions, changelog and sources; the operational sections (inputs, outputs, pipeline, structure, checklists, honesty rules, emphasis map, acceptance) were already in the skill and were removed here. The profile is read §1–§15; field ids come from `python3 pipeline/scripts/naming.py ids`. Section references in the prior-art tables point to the pre-0.9.0 numbering.
- **0.8.0 (2026-10-08)** — Posting résumés moved from `../data/resumes/postings/<task name>/` to `applications/<task name>/`, shared with the cover letter. The posting source is `resume.md` (bases stay `master.md`). `resumes/` now holds only bases.
- **0.7.0 (2026-10-07)** — Task notes are now named `<Company> - <Job title>` instead of `job-<job_id>`, and posting-résumé folders follow the task name (`../data/resumes/postings/<Company> - <Job title>/`). The job id is read from the task's **Job ID** field and kept in `master.md`. Linkage table and paths updated.
- **0.6.0 (2026-10-07)** — Posting résumés also render a PDF (`Russell Lebo - <Title>.pdf`) beside the `.docx` and `master.md`, via `pipeline/scripts/package/render_pdf.py`. The `.docx` stays the default submission; the PDF serves postings that ask for one and gives a measurable page count (`render.pdf_pages`). Task notes link both. §2.2, §2.4, §4.7, §10 updated.
- **0.5.0 (2026-10-07)** — Résumés are now **one per posting** (1:1) instead of one per title cluster (\*:1). File name is `Russell Lebo - <Title>.docx`, with `<Title>` the posting title without the company. Because many postings share a title, files live in `../data/resumes/postings/<job_id>/`, and the cluster `master.md` becomes a **base** that postings are derived from (no `.docx`). Added `type: resume-posting` frontmatter, `base` / `gaps`, the §2.4 link table and staleness rule. The **Résumé variant** field holds a link to the `.docx` only, never `master.md`. §2, §3, §4.7, §9, §10 and §12 updated. Existing rendered cluster `.docx` files predate this and are to be migrated (see `context/implementation-plan.md`).
- **0.4.0 (2026-10-06)** — Job records moved: the separate `../data/jobs/<id>.md` notes were folded into the Application Tracking dotpm tasks (`../../goals/Application Tracking/_tasks/job-<id>.md`). JD frontmatter now lives in each task's `customFields` (keyed by field id; resolve ids by name from the project note's `customFields`), and the JD text is the task body. `resume_variant` → the **Résumé variant** custom field; `fit_score` → **Fit**; JD `status` retired in favor of the task status. Paths throughout updated; the write-back contract is unchanged. Migration: `pipeline/scripts/tracking/fold_jobs_into_tasks.py`.
- **0.3.0 (2026-07-22)** — Added §2.4 "Variant ↔ job linkage and the application flow": made the `source_jobs` ↔ `resume_variant` links bidirectional and mandatory, defined the operator flow from posting selection to résumé upload (including the blank-variant and PDF-exception paths), post-submission `status`/ledger reconciliation, and the rule for new postings joining an already-served cluster. Spec status flipped draft → accepted.
- **0.2.0 (2026-07-22)** — Added §11 "Prior art & adopted heuristics": folded concrete tactics from the open-source [`Paramchoudhary/ResumeSkills`](https://github.com/Paramchoudhary/ResumeSkills) pack (`job-description-analyzer`, `resume-tailor`, `resume-ats-optimizer`, `resume-formatter`, `resume-version-manager`) into §4–§6, with explicit overrides where its defaults — metric invention (`resume-quantifier`), the keyword-count match model, pasted-résumé input, and chat-report output — conflict with the profile's honest-attribution discipline (§7) and the vault file model (§1–§2). Renumbered Open questions → §12, Changelog → §13, Sources → §14.
- **0.1.0 (2026-07-22)** — Initial specification. Defines the agent-run résumé-tailoring skill: inputs (profile, fit-scored titles-index, retrieved JDs), the three-lever response model, the §4 pipeline (prioritize → JD signal → emphasis selection → honest keyword mapping → assemble → self-check → render/write-back), canonical ATS section order, embedded 2026 ATS best practices and the four ranking signals, binding honesty constraints from profile §11/§14, the title→emphasis map, a worked example, and MVP acceptance criteria. Output: Markdown master variant + ATS `.docx`, with `resume_variant` written back to `../data/jobs/`.

---

## Sources

**Vault:** the dossier (`naming.py paths`, row `dossier`) · [`titles-index.md`](../../logs/searches/titles-index.md) · the Application Tracking tasks (`applications/_tasks/`) · the criteria file (`naming.py paths`, row `criteria`) · [`README.md`](../../README.md) · [`context/decisions.md`](../../context/decisions.md).

**ATS best practices (web, 2026):** formatting sources moved to the [ATS formatting spec](ats-formatting-spec.md).

- How ATS Systems Rank Resumes: The 4 Signals — https://resumeoptimizerpro.com/blog/how-ats-systems-rank-resumes
- How ATS Ranks Candidates on Job Criteria — https://www.mokahr.io/myblog/ats-candidate-ranking-job-criteria/
- 500+ Resume Keywords for the ATS (Jobscan) — https://www.jobscan.co/blog/top-resume-keywords-boost-resume/
- Best day to submit a job application — https://bestjobsearchapps.com/articles/en/best-day-to-submit-a-job-application-datadriven-guide-to-23x-higher-response-rates

**Prior art (external skills):**

- Paramchoudhary/ResumeSkills (MIT) — https://github.com/Paramchoudhary/ResumeSkills
- resume-tailor — https://github.com/Paramchoudhary/ResumeSkills/blob/main/skills/resume-tailor/SKILL.md
- job-description-analyzer — https://github.com/Paramchoudhary/ResumeSkills/blob/main/skills/job-description-analyzer/SKILL.md
