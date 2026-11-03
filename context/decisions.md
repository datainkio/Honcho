---
title: "Decisions — Honcho"
description: "Decision record for Honcho, continuing the old job-retrieval automation's record (D1 to D30)."
type: decisions
status: active
tags:
  - automation
  - linkedin
  - decisions
date: 2026-07-21
---

# Decisions

> Entries D1 to D30 were made in the old automation repo (`Portfolio/business development/automation`), whose layout was `scripts/`, `skills/`, `specs/`, `config/`, `input/`, `../data/`, `../source/` and `tracking/`. Paths inside them are history. For the mapping to Honcho's layout, see [`migration-plan.md`](migration-plan.md).

## D1 — Adopt `mcp-server-linkedin` as the retrieval layer

**2026-07-21.** The MVP's two needs (search-by-criteria, fetch JD content) map 1:1
to the server's `search_jobs` and `get_job_details` tools. It's actively maintained,
Apache-2.0, and MCP-standard. Full assessment, including the ToS / account-risk
tradeoff, in [`linkedin-mcp-server-evaluation.md`](linkedin-mcp-server-evaluation.md).

**2026-07-21 (update):** the PyPI package was renamed `linkedin-scraper-mcp` →
`mcp-server-linkedin` upstream; `.mcp.json` and docs updated to the new name
(old name still resolves as an alias for now).

## D2 — MCP-native orchestration for the MVP (no custom code yet)

**2026-07-21.** The server is designed to be consumed by an MCP client. For the MVP
the "runner" is an operator/agent following [`../runbook.md`](../runbook.md) and calling
the two tools, rather than a bespoke script driving the server programmatically.

- **Why:** thinnest path to the MVP; matches how the server is meant to be used; nothing to maintain when LinkedIn's markup shifts (the server absorbs that).
- **Deferred alternative:** a code-orchestrated runner (Python MCP client subprocess-launching the server, looping over criteria, writing `data/`) — worth it only when runs need to be scheduled/repeatable/unattended. Not now, and unattended high-frequency runs are discouraged by the ToS/rate-limit constraint anyway.

## D3 — Output as Obsidian markdown keyed by `job_id`

**2026-07-21.** Retrieved JDs are saved one-file-per-job as `../data/jobs/<job_id>.md`,
with `job_id` (the numeric ID from a LinkedIn `/jobs/view/<id>` URL) as the natural key.

- **Why:** reconciles directly with the existing [job ledger](../../source/Job%20Openings-Grid%20view.csv), which already stores those URLs; keeps JDs analyzable with the vault's normal markdown tooling.
- Placeholder frontmatter fields (`fit_score`, `status`, `resume_variant`) reserve space for downstream steps without committing to them now.

## D4 — Data gitignored by default

**2026-07-21.** `../data/searches/` and `data/jobs/` contents are gitignored; structure and
docs are tracked. Scraped external content and repo size argue for keeping it local by
default; flip the [`../.gitignore`](../.gitignore) rules if tracking is wanted later.

## D5 — One note per posting: job descriptions fold into dotpm tasks

**2026-10-06.** Supersedes D3 (and D4 for job records). Keeping a JD note in `../data/jobs/` and a separate task for each posting
in `goals/Application Tracking/_tasks/` was costly and fragile to keep in sync. Each posting is now a single dotpm task,
`<Company> - <Job title>.md`: the JD frontmatter lives in the task's `customFields`, and the JD text is the task description (note body).

- **Field mapping:** Fit (number), Company, Posting (url), Job ID, Location, Work type (select), Posted (date), Retrieved (date), Search, Résumé variant, Industry (select), Activities and Technologies (multiselect). Retired: `type`, `title` (it's the task title), `status` (it's the task status), `posted_raw`.
- **Field ids:** values are keyed by opaque field id. Scripts and skills look ids up by name in the project note — never hard-code them. Deleting and recreating a field orphans its values; renaming a field is safe.
- **Retrieval:** `get_job_details` stages notes in `../data/inbox/`, and [`scripts/fold_jobs_into_tasks.py`](../scripts/fold_jobs_into_tasks.py) `--write --consume` folds them into tasks. Re-running it is safe and preserves task status.
- **Prioritization:** dotpm saved views can't sort by custom fields, so [`Priority.md`](../dashboard.md) (DataviewJS) ranks open postings by Fit, then freshness.
- **Trade-off:** `goals/` is outside every git repo, so JD text has no version history. The pre-migration `data/jobs/` folder and its archive were deleted on 2026-10-06, so the tasks are now the only copy.

## D6 — Fit is scored per posting by a fixed rubric

**2026-10-07.** Each posting's Fit (0–10) comes from [`fit-rubric.md`](fit-rubric.md): discipline, seniority, domain, and requirements against the profile, with caps for military or clearance work and for location eligibility. Scores are made in batches. Each batch gets a reviewed report in `../data/fit/` before its scores are written to the tasks.

- **Why:** `Priority.md` ranks by Fit, but only 10 postings had a score, all set by hand with no recorded reasoning. A rubric makes scores repeatable and explainable.
- **Title Fit** in `titles-index.md` stays a separate, title-only signal.

## D7 — Résumés are one per posting, named `Russell Lebo - <Title>`

**2026-10-07.** Each posting gets its own résumé file, `Russell Lebo - <Title>.docx`, with `<Title>` the posting's job title without the company. This replaces one-résumé-per-title-cluster (D-spec 0.1–0.4). The files live in `../data/resumes/postings/<job_id>/`, and the cluster `master.md` becomes a **base** that posting résumés derive from.

- **Why:** Russ wants a résumé named for the role, one per posting. The recruiter-visible file name should carry only the candidate and the role.
- **Two layers, not 197 independent résumés:** tailoring effort stays proportional to distinct emphases. A posting résumé changes only title, wording, and skill order, so it can't widen the truth boundary.
- **Folder by `job_id`:** titles repeat across employers and the file name is title-only, so the folder disambiguates.
- **The Résumé variant field links the `.docx` only**, never `master.md`.
- Spec: [`../specs/resume-tailoring-skill-spec.md`](../specs/resume-tailoring-skill-spec.md) v0.5.0 §2.
- **Superseded in part (2026-10-08):** the folder moved to `../data/applications/<task name>/`, shared with the cover letter. See D11.

## D8 — Tasks are named `<Company> - <Job title>`

**2026-10-07.** Application Tracking tasks, and the résumé and cover-letter folders under them, are named `<Company> - <Job title>` instead of `job-<job_id>`. A task's `title` field matches. When two postings share both company and title, later ones get ` (<job_id>)` appended.

**Amended 2026-10-09.** dotpm renames each task file to a slug of its title, cut at 60 characters. On a long title that cuts off a trailing id, so two tasks get the same slug and dotpm reports "A note named ... already exists" (both EPAM Design Strategist postings hit this). A colliding task's title now carries the id right after the company: `<Company> (<job_id>) - <Job title>`. `naming.unique_title` checks new titles against every task's slug and file name. Folder names keep the trailing ` (<job_id>)`, and `naming.job_title` and `naming.folder_name` read the id in either position.

- **Why:** the numeric id told Russ nothing in file lists, dashboards, or links.
- **The id stays findable:** it's the task's **Job ID** field. Scripts look tasks up through `scripts/naming.py` (`find_task`), never by file name.
- Supersedes the `job-<id>` prefix noted in D5. Migration: `scripts/rename_tasks_to_company_title.py`. Migration script retired 2026-10-29: it targeted `resumes/postings/` and `cover-letters/`, folders that no longer exist.

## D9 — Submitted text never contains `< > { } "`

**2026-10-07.** Online application forms flag `<`, `>`, `{`, `}` and `"` (straight or curly) as invalid and won't submit until each is removed, which is slow to find by hand.

- **Rule:** résumé and cover-letter text contains none of `< > { } " “ ”`. Quote JD phrases with single quotes; write `p under 0.10` for `p<0.10`.
- **Enforced:** `scripts/charset.py` is the single definition. `render_docx` and `render_pdf` raise if the body has one, so no file renders with it. `python3 scripts/charset.py` lints every master; `--fix --backup <dir>` applies the two replacements above.
- **Source facts unchanged:** `professional-profile.md` keeps `p<0.10`; the replacement happens when text is written into a master.
- Fixed on 2026-10-07: 132 masters (bases, posting résumés, cover letters) and all 195 rendered files.

## D10 — Jobgether is a second source, joined at the inbox

**2026-10-08.** Postings also come from [Jobgether](https://jobgether.com/developers), whose public API searches across companies with no key. A Jobgether posting is staged in `../data/inbox/` like a LinkedIn one, so the fold, tasks, scoring, résumés, and letters run unchanged. Spec: [`../specs/integrated-datasources-spec.md`](../specs/integrated-datasources-spec.md).

- **Why Jobgether:** of the free sources checked, it alone searches every employer, fits Russ's roles, and invites agent use (MCP server, `llms.txt`). Greenhouse, Lever, and Ashby need a company to search; Indeed and Monster have no public read API.
- **Manual runs only**, like LinkedIn (D2). A 15-minute schedule was considered and dropped, so the spec's five-minute story is not met.
- **Description from the listing page**, read through Russ's Chrome, because the API returns none. 2 seconds between requests, Jobgether's `Crawl-delay`.
- **Source is marked by `source_search: jg-<name>`**, not a new task field, so `Priority.md` and the dotpm columns don't change.
- **Duplicates across sources** are skipped at selection by company and title, because the ids differ (LinkedIn numeric, Jobgether 24-character hex).

## D11 — One folder per posting holds the résumé and the cover letter

**2026-10-08.** Output for a posting lives in `../data/applications/<Company> - <Job title>/`. Before, résumés were in `resumes/postings/` and letters in `cover-letters/`, so one posting's files sat in two places, and `postings/` under `resumes/` said nothing.

- **Files:** `resume.md`, `Russell Lebo - <Title>.docx` and `.pdf`, `cover-letter.md`, and `Russell Lebo - <Title> - Cover Letter.docx`. The letter `.docx` adds the suffix so the two don't clash. The résumé keeps its D7 name.
- **`resumes/`** held only the four cluster bases (`master.md`). Archived outside the project 2026-10-29; nothing reads them since D20.
- **Code:** the folder and suffix are defined once in `scripts/naming.py` (`APPLICATIONS`, `LETTER_SUFFIX`). Each renderer deletes only its own files when it re-renders.
- Migrated 121 postings and repointed their task fields and links the same day.

## D12 — Descriptions are fetched in subagent batches, after a title filter

**2026-10-09.** In the 2026-10-09 run, 41 `get_job_details` calls returned about 586k characters, 70% of all tool output, and the session ran out of context. Retyping each description into the staged note cost about 60k output tokens more.

- **Subagent batches:** the main session searches and selects, then hands `batch_size` jobs at a time to the `job-fetcher` subagent, which fetches, stages, and replies one line per job. Descriptions never enter the main context. Batches run one after another, because the LinkedIn server drives a single browser. This changes who does the fetching, not the rules: still MCP-native (D2), manual and human-paced, and verbatim.
- **Title filter before fetching:** `exclude_title_terms` drops clear misfits, and company + title catches reposts under a new `job_id`. Most of that run's rejects had plausible titles (Head of Design, Design Manager), so the filter saves less than the batches do. The subagent still drops misfits it sees only in the description.
- `seo` and `marketing` are deliberately not excluded: some SEO content-strategist roles are being pursued.

## D13 — Submitted résumés and letters are frozen

**2026-10-09.** A profile update re-derived all 167 posting résumés and edited 45 letters, including ones already sent. Russ had the Applied ones reverted. A posting's résumé and cover letter are now never edited, re-derived or re-rendered once its task is at Applied (`blocked`) or at any status with dotpm's "done" toggle.

- **Live, not hard-coded:** `scripts/naming.py` `frozen_statuses()` reads the toggle from the project note's `config.statuses`, so toggling a status in dotpm changes what is protected.
- **Enforced:** `derive_posting_resumes.py` skips frozen postings even when a base changes; `render_cover_letter.py` refuses them.
- **Retired 2026-10-29:** `derive_posting_resumes.py` was deleted; `render_docx.py` now holds the shared renderer.
- **Consequence:** a frozen posting's résumé can lag its base. That is intended: it records what was sent.
- **Screening and Closed:** Screening (`review`) is frozen in code as well as by its toggle. Closed (`status-5ci3xo`) is not frozen: a Closed posting was never submitted, because it was unavailable or its owner closed it.

## D14 — Indeed is a third source, read in Russ's browser

**2026-10-12. Accepted after the pilot the same day** (two postings folded; findings in the spec). Postings also come from Indeed, searched and read on indeed.com in Russ's signed-in browser through Claude in Chrome. Like Jobgether (D10), they are staged in `../data/inbox/`, so the fold and everything after it run unchanged. Spec: the Indeed section of [`../specs/integrated-datasources-spec.md`](../specs/integrated-datasources-spec.md).

- **Why Indeed:** it is the largest US board, and since 2026-07-01 Glassdoor runs on Indeed's listings. Monster was sold in bankruptcy in 2025, offers only a partner API, and has little senior UX inventory.
- **Why not Indeed's own connector:** the official connector (`mcp__claude_ai_Indeed__*`, beta) returns the full description, but its ids change with every search, its detail tool rejects Indeed's own job key, and its search stops at 10 results with no date filter, sort or paging. Duplicate checks need a stable key, and incremental runs need a date filter.
- **The job key is the id:** `job_id` is the 16-character hex `jk` from each result card. `scripts/naming.py` accepts it alongside LinkedIn's numeric ids and Jobgether's 24-character ones.
- **Decoy cards:** each results page hides a card with a fake key. Only visible cards are read, and a hidden one is never opened.
- **Posted date** comes from the listing's JSON-LD `datePosted`, because the page text has none. Indeed shows no applicant count, so Indeed postings never get the 'Over 100' priority drop.
- **Manual and human-paced:** 8 seconds between page loads, enforced by an in-page timer (the pilot showed tool latency alone doesn't guarantee it). Stop at any Cloudflare or sign-in page. Indeed's terms reportedly bar scraping and automated access, and its robots.txt disallows `/jobs?q=` (both from third-party summaries, not checked against Indeed's own text). Russ uses it for his own job search, at a human pace, in his own browser: the same account-risk trade-off as LinkedIn (D1).
- **`get_resume` is never a source.** The connector can read Russ's Indeed profile, but `professional-profile.md` stays the only source of facts about him.

## D15 — UI/UX Jobs Board is a fourth source, read by a script

**2026-10-12. Accepted after the pilot the same day** (four postings folded; findings in the spec). Russ had accepted the route and the product-design scope before it. Postings also come from [UI/UX Jobs Board](https://uiuxjobsboard.com), a design-only board. Like D10 and D14, they are staged in `../data/inbox/`, so the fold and everything after it run unchanged. Spec: the UI/UX Jobs Board section of [`../specs/integrated-datasources-spec.md`](../specs/integrated-datasources-spec.md).

- **Why this board:** design roles only, including UX research and UX writing, with Apply links straight to the employer's ATS. In the probe, 1 of 50 remote-US postings already had a task, so it mostly adds new postings.
- **Why a script:** the board needs no sign-in and serves full HTML to a plain request, so `scripts/uiux_board.py` reads it and writes the staged note itself. That makes the verbatim rule mechanical instead of a model's job, and it ends the cost of a model retyping each description (D12). This goes past D2's 'no custom code' as the fold script already did: code does the I/O, and a model does the judgment (the job-fetcher's fit check).
- **Why not WebFetch or a browser:** WebFetch summarizes, so its text isn't verbatim. A browser (the Indeed route) isn't needed while plain requests work; it is the fallback if Cloudflare starts challenging them. The script names itself in its user agent and never works around a challenge.
- **The board's id is the id:** `job_id` is the numeric id in `/job/<id>-<slug>`, 7 digits so far. `scripts/naming.py` already accepts it, and it can't collide with LinkedIn's 10-digit ids in practice. The slug is required to open a job page, so search records keep each card's full path.
- **Posted date** comes from the job page's JSON-LD `datePosted`; cards show only an age. The board shows no applicant count, so these postings never get the 'Over 100' priority drop.
- **Manual and paced:** 5 seconds between requests, enforced by the script. The site sets no Crawl-delay. Any 403, 429, 5xx or Cloudflare page stops the run. The board's terms grant a licence for 'personal, non-commercial transitory viewing only' and say nothing about bots; Russ reads it for his own job search, by hand and at low volume, the same posture as the other sources.
- **Product designer is a target role** (Russ, 2026-10-12). It dominates this board, and since the job-fetcher's target list is shared, it now applies to every source.
- **Haiku runs the fit check for this source** (Russ, after the pilot). The script does the reading, so the job-fetcher only judges fit. In the pilot Haiku agreed with Sonnet on four of five postings and staged the fifth, which Sonnet skipped: it may stage more, never less. Other sources keep Sonnet.
- **Roles that require an active security clearance are skipped** (Russ, after the pilot), from every source. `professional-profile.md` lists none, and Haiku staged such a role in the pilot because the skip list didn't name it.

## D16 — LinkedIn is read by a script; Select is a script for every source

**2026-10-12. Accepted (Russ: 'implement all' on the token-efficiency review, F1).** Supersedes D2's 'MCP-native, no custom code' and the standing instruction of 2026-07-22 not to script LinkedIn retrieval. Evidence: [`token-efficiency-review.md`](token-efficiency-review.md).

- **What changes:** `scripts/linkedin_fetch.py` calls the same `linkedin` MCP server (`.mcp.json`, Russ's logged-in browser profile) over stdio. `search` runs `search_jobs` and writes the search record with a job table; `stage` runs `get_job_details` and writes `../data/inbox/<job_id>.md`. The job-fetcher only runs it and checks fit, on Haiku as for D15.
- **Why:** a description read by a model stays in its context for every later call in the batch. LinkedIn batches cost about 98k tokens per posting; the D15 shape costs 8–15k.
- **The hard rules carry over unchanged:** manual runs only, when Russ asks; `fetch_delay_seconds` before every call, the first included; `max_fetches_per_run` refused above the cap; a tool error, a login, captcha or security-check page, or two unreadable postings in a row stops the run, with no retries. The script closes its browser session when it ends. Claude Code's own LinkedIn session must be closed first, since both drive one browser profile.
- **Verbatim, mechanically:** the body is the text between LinkedIn's 'About the job' line and its '… more' line, with trailing spaces trimmed and blank-line runs folded. All 199 `get_job_details` results saved from earlier sessions (`../data/fixtures/linkedin/`) parse this way; on a posting the old job-fetcher staged, the words match except the header line and benefits list the model used to keep.
- **One Select rule set:** `scripts/select_candidates.py` replaces the four per-source dedupe procedures in the runbook (id, company and title with legal suffixes and '&' folded, title suffix, staged, repeats, `exclude_title_terms`, placeholder companies, UI/UX `exclude_types`). Subsidiaries and person-named companies still need a read.
- **Fallback:** if LinkedIn changes the page text so the script refuses postings, the old route (the job-fetcher calling `get_job_details`) is a revert of this decision, not a workaround.

## D17 — Packaged for others: sources are gated, paths become config

**2026-10-13. Accepted (Russ), the plan in [`handoffs/2026-10-13-plugin-packaging.md`](handoffs/2026-10-13-plugin-packaging.md).** Russ will publish this repo on GitHub as a Claude Code plugin whose skills are the entry points and whose `job-fetcher` stays a worker.

- **Sources are gated by `sources: <name>: { enabled }`** in `config/search-criteria.yaml`. API-based sources ship on (only Jobgether, a public search API) and scraping sources are opt-in (LinkedIn's logged-in browser, Indeed's Chrome route, the UI/UX Jobs Board's HTTP scraping), each with a terms-of-service notice. A missing entry is off, except Jobgether. `linkedin_fetch.py` and `uiux_board.py` refuse a disabled source on `search` and `stage`; the runbook tells the operator to skip a disabled Jobgether or Indeed section. Russ's own config turns all four on.
- **Stay in this repo**, but separate the profile and truth rules from what ships (steps 2a–2b of the plan).
- **Paths become config:** one root, set by an env var or a `paths:` key, with defaults that work outside Russ's vault (step 2c).
- **dotpm and Obsidian Project Manager are a documented requirement for now.** A swappable tracking backend is deferred.
- **Target roles are config (step 3):** the `fit:` block in `config/search-criteria.yaml` (targets, location, skip list) replaces the roles hard-coded in `job-fetcher.md`. The fetcher reads it through `naming.py fit`. `/job-setup` writes it from profile §13, and `scripts/setup_check.py` reports what an install still lacks.

## D18 — Résumés are rendered from a fixed template; no page limit

**2026-10-14. Accepted (Russ).** A posting's résumé is the fixed text in [`skills/resume-tailoring/template.md`](../skills/resume-tailoring/template.md) plus a few bounded slots, each a word or phrase defined in the template's `slots:` frontmatter. Tailoring fills the slots and writes no narrative. Integrating the template into the skill and scripts is tracked in the Resumé project in `goals/`.

- **The two-page limit is deprecated.** The template sets the content, so length is no longer a tailoring lever. The skill no longer checks pages, `derive_posting_resumes.py` no longer warns, and `render_pdf.py` renders at 10pt without shrinking unless a caller passes `max_pages`. `render.pdf_pages` is still recorded.
- **Cover letters keep their one-page rule** until their own template is integrated.

## D19 — Interest statements: their own skill, gated on a match report

**2026-10-16. Accepted (Russ).** Application forms often ask 'Why are you interested in this role, company, and industry?'. The [`interest-statement`](../skills/interest-statement/SKILL.md) skill answers it in 3-5 sentences per posting (`why-interested.md`), drafted from a brief (`interest.md`) kept beside the match report.

- **Three passes, each on the model the pilot chose.** Brief by Sonnet; draft by Opus, picked over Haiku and Sonnet on Nava (Sonnet used the gap term 'tax' and overstated the Bixal work; Haiku listed rather than argued and put the trial's figures next to 'I designed'); claim check by Sonnet, a different agent from the drafter. In the pilot the check flagged an overstatement in all five drafts, so it stays.
- **Company facts come from the job description only.** No company lookup.
- **Written independently of the cover letter**, which the skill doesn't read.
- **Silent on gaps.** A gap term is never written, even to describe the role.
- **A match report is required; there is no fallback.** Its absent rows are the gap list that keeps the statement honest. The résumé's own `gaps` is too thin (Nava: one term against the report's four), so a JD-plus-résumé fallback would let gap terms through.
- **Only postings at Prospect.** Narrowed on 2026-10-16 (Russ) from Prospect, Preparing or Blocked: the statement is written while the package is assembled, before the posting moves on. Statuses are resolved by label (`naming.interest_statuses()`), never by id: the id `blocked` is labeled Applied and is frozen (D13).

## D20 — The résumé skill fills slots only; Russ approves the match report before render

**2026-10-19. Accepted (Russ).** A run takes one posting and is the résumé half of the application package (`journeys/application creation.canvas`). Supersedes the cluster base and derive step (D7's `master.md`) for new résumés.

- **The skill's only edit is slot values.** Keyword-matching steps 4-5 are proposals in the match report. Russ tunes the template's fixed text himself (the tune loop); that is how the 25-35 term count is reached (Nava: 28 of 31).
- **Gaps don't halt.** Absent terms and any shortfall are recorded in the match report, which is the single review stop.
- **Approval gate.** Russ sets the match report's `status: approved`; `scripts/render_resume.py` refuses anything else, and fills `job_title` and `job_title_article` itself. _Superseded by D22: approval is now the task's Matching approved checkbox._
- **Fit is out of scope for the skill** until the package output is confirmed. Fit stays on [`fit-rubric.md`](fit-rubric.md); `specs/calculate-fit-score-spec.md` is a draft for later.
- **Honesty review skipped for now** (Russ). The truth rules still bind slot values.
- **Retired 2026-10-29:** `derive_posting_resumes.py` was deleted; `render_docx.py` now holds the shared renderer.

## D21 — Script sources stage in one background run; fit check off for now

**2026-10-20. Accepted (Russ).** Amends D12 for LinkedIn and UI/UX Jobs Board only. Plan and findings: the Automation task 'Speed up job retrieval'.

- **The main session runs the stage scripts.** `linkedin_fetch.py stage` and `uiux_board.py stage` take `<search>=<id>` (or `<search>=<path>`), so one call stages a source's whole selection across searches with one server and one browser. They print one line per posting and no description text, so D12's goal still holds: no description enters the main context. `batch_size` and the per-batch `job-fetcher` now apply to the Chrome sources only.
- **In the background, overlapping the Chrome sources.** The LinkedIn server drives its own Patchright profile (`~/.linkedin-mcp/profile/`; `.mcp.json` passes no `--chrome-path`), and the board is plain HTTP, so neither shares the operator's Chrome. Never two LinkedIn processes at once. A background exit 1 stops the whole run. Fold once, at the end.
- **Fit check off for now** (`selection: fit_check: false`; `naming.py fit` reports it). Every fetched posting is staged; misfits are scored low at the next Fit batch, at the cost of more tasks to triage. When back on, the `job-fetcher` checks script-staged notes with `source: staged`.
- **Second pass in a day: `search --incremental`**, which lays `incremental:` (`past_24_hours`, 1 page) over `defaults:`. To be verified against a full pass before it's relied on.
- **One confirmation per run** (Russ chose option A). Every enabled search runs first, then `select_candidates.py` once over all the run's records, then one shortlist grouped by source. Russ's approval covers every source's fetch in that run; picks added afterwards need a new one. Replaces the per-batch and per-source confirmations. _Amended by D30 (2026-10-28): one confirmation per slice._
- Pacing (8, 5 and 2 seconds), `max_fetches_per_run` and the hard stops are unchanged.
- **Source order** (2026-10-21, Russ). `select_candidates.py` reads the run's records cheapest-description first: Fantastic, TheirStack, UI/UX Jobs Board, Jobgether, Indeed, LinkedIn. A job listed by several sources is kept from the first and dropped as a repeat from the rest, so LinkedIn, the riskiest fetch, is fetched only for jobs no other source returned. LinkedIn still searches every run: its value is coverage. The order is in the script, not the argument list.

## D22 — Match-report approval is a checkbox on the task

**2026-10-20. Accepted (Russ).** Amends D20's approval gate.

- **The gate is the task's Matching approved field**, a dotpm `checkbox` custom field on Application Tracking tasks (`true` when checked). `scripts/render_resume.py` renders only when it is `true`; the match report's own `status` is no longer read, and new reports don't carry one.
- **Context:** Russ asked for it on 2026-10-20, after an agent's attempt to set `status: approved` on nine reports at his instruction was blocked by the session's permission check. The checkbox sits on the task in Obsidian, beside the stage and Fit.
- **Agents never check it.** Only Russ does, after reviewing the report. The field id is resolved by name (`naming.field_ids()["Matching approved"]`), never hard-coded. The fold keeps it, as it keeps every field defined by hand.
- **Existing reports at `status: approved` are not migrated.** Their postings render again only after the box is checked.

## D23 — Fantastic.jobs is a fifth source, read by a paid API

**2026-10-21. Accepted (Russ).** Terms accepted; MVP returns 10 results a call while Russ judges quality. Evaluation: [implementation plan](implementation-plan.md) item 19.

- **Why:** it adds postings from company career pages (ATS), which no other source reaches, and could take LinkedIn retrieval off Russ's logged-in browser if quality holds.
- **One paid call, then offline.** The API returns full descriptions with each search result and bills per job returned. `search --write` is the only command that calls it. It saves the raw response beside the search record, and `stage` writes inbox notes from that file. A dry-run `search` prints the request and spends nothing.
- **Ids.** ATS jobs are `fj<id>`, Fantastic's internal id with a prefix so it can't collide with a LinkedIn id. Job-board rows from LinkedIn use their `linkedin_id`, so they dedupe against existing LinkedIn tasks. `naming.JOB_ID` accepts `fj` ids.
- **Verbatim:** the body is the API's `description_text` unchanged. `work_type` maps the API's AI-derived `ai_work_arrangement` (Remote Solely or Remote OK → remote, Hybrid → hybrid, On-site → onsite).
- **Only the last 24 hours** (2026-10-21, Russ). The API's `time_frame` counts active listings, not post age, so the script drops jobs posted before `max_age_hours` (24) ago. It sends `date_posted_gte` as the start of the cutoff's day, so off-window jobs mostly aren't billed. Then it applies the exact cutoff, comparing date-only postings (midnight UTC) by date so jobs posted earlier that day aren't lost. Dropped ids are listed under `dropped_old` in the saved response and are never staged.
- **Query and limit** (2026-10-21): the pilot's 10 were 4 on target, 1 borderline and 5 off (learning experience, instructional design, sales, solution design). `title_advanced` now excludes those words, which cut the 24-hour count from 21 to 11. `limit` is 25.
- **Cost:** the cheapest plan is Starter-20k, $95 a month for 20,000 jobs and 10,000 requests. Raise `limit` only after the MVP shows the results are worth it.

## D24 — TheirStack is a sixth source, read by a paid API

**2026-10-21. Accepted (Russ).** Terms accepted; free trial, with Fantastic's limits (`limit: 25`, last 24 hours). Evaluation: [implementation plan](implementation-plan.md) item 20.

- **Why:** its value is jobs Fantastic doesn't return. TheirStack aggregates job boards (Indeed and LinkedIn are its largest sources) and company career pages.
- **Same shape as D23.** One paid call, then offline: `search --write` is the only command that calls the API (`POST /v1/jobs/search`, one credit per job returned). It saves the raw response beside the search record, and `stage` writes inbox notes from that file.
- **Ids.** A job TheirStack read from LinkedIn (`source_url`) uses the LinkedIn id, and one read from Indeed uses the Indeed `jk`, so both dedupe against existing tasks. Every other job is `ts<id>`. `naming.JOB_ID` accepts `ts` ids.
- **Verbatim:** the body is the API's `description` (markdown) unchanged. `work_type` maps the `remote` and `hybrid` booleans.
- **Only the last 24 hours.** `date_posted` is a date with no time, so `posted_at_max_age_days: 1` (today and yesterday) matches Fantastic's day-based cutoff. The API filters it before billing; the script needs no cutoff of its own.
- **Overlap with Fantastic** is caught by `select_candidates.py`, which drops a job whose company and title appeared earlier in the run. `select_candidates.py` reads Fantastic first (D21, source order).
- **Cost:** the cheapest plan is $49 a month for 1,500 credits; unused credits roll over for 12 months. The free tier allows 50 requests an hour and 400 a day.

## D25 — LinkedIn keywords are semantic; content strategy leaves LinkedIn

**2026-10-23. Accepted (Russ).** Evidence: the Automation task 'Tighten the LinkedIn search keywords' (test records `../data/searches/2026-10-23--kwtest-*`).

- **Why:** the redesigned search page reads keywords as a semantic query. Quotes and NOT had no effect, and OR is unproven. Wording can't filter out marketing roles.
- **`ux-content-strategy-remote` is retired.** Every content variant scored 22-34% on target, mostly content, product and growth marketing. Jobgether, Indeed and the paid sources still search content design with real filters.
- **`design-manager` searches 'product design manager'**, dropping 'experience', which matched customer-experience and generic product managers.

## D26 — Retrieval runs from one command; Jobgether is searched by script

**2026-10-26. Proposed (POC, awaiting Russ's review).** Phase 1 of [`package-efficiency-plan.md`](package-efficiency-plan.md); Automation task 'Cut time and tokens per application package'.

- **`scripts/retrieve.py search`** runs every enabled script source's search concurrently, one worker per source (LinkedIn in its own process with its own pacing; the UI/UX board's searches one after another, 5 seconds apart), merges titles, runs Select over the records this run wrote, and prints one shortlist grouped by source. **`retrieve.py stage`** sends each approved pick to its source's script and prints job-fetcher lines for the Chrome sources. Both print a plan and call nothing without `--write`, because LinkedIn's and the board's own dry runs still fetch. Fantastic and TheirStack are called only with `--paid` as well.
- **Hard stops carry over:** a script that exits 1 stops the run. The others get SIGINT, so their cleanup runs (LinkedIn closes its browser session), and no queued command starts. Pacing, caps and the one confirmation (D21) are unchanged.
- **Jobgether's search is a script** (`scripts/jobgether_fetch.py`): the same public `searchJobs` tool, called as JSON-RPC over HTTP, 2 seconds apart. Its results no longer enter the main context, and the model no longer writes the record. Listing pages stay in Russ's Chrome (D10). `max_age_days: 3` replaces the hand filter the 2026-10-23 record applied; a search with no jobs in that window writes no record.
- **Why:** the 2026-10-23 search step took about 25 main-session calls, with seven `searchJobs` results (about 22k characters) in an Opus context and a hand-written record.
- **Fallback:** the per-source commands in the runbook are unchanged and still work.

## D27 — Triage before match reports: the fold sets priority, reports go to critical Prospects only

**2026-10-26. Accepted (Russ: 'Triage task approved', option A).** Phase 1, step 1.5 of [`package-efficiency-plan.md`](package-efficiency-plan.md).

- **Why:** on 2026-10-23, 11 of 40 match reports were never rendered (9 over-100 postings moved to medium, a repost, a posting moved to a custom stage), about 1.0M weighted tokens. Priority was set by hand after the fold, but the reports were written for every folded posting.
- **The fold sets a new task's priority:** critical, or medium when the LinkedIn note carries `over100: true`. `linkedin_fetch.py stage` now writes that key when the posting's header says 'Over 100 applicants'. An existing task keeps its priority. This replaces setting priority by hand from the stage output, and the fold's old 'medium' default.
- **Batch match reports take `naming.py reports`:** Prospects at priority critical with no report yet. Lower priorities are skipped. Duplicates are dropped at the shortlist confirmation (D21) and by `select_candidates.py`. A posting Russ names gets a report whatever its priority.
- **Not chosen:** turning the fit check back on (option B; D21 keeps it off).

## D28 — Package agents read packets, run flat, and get lexicon hints only on request

**2026-10-26. Accepted, as amended below, under Russ's delegation ('I trust your judgment on what the results indicate and the best approach forward').** Phase 2 of [`package-efficiency-plan.md`](package-efficiency-plan.md).

- **Packets** (`scripts/match_packet.py report|letter|interest <ids>`): two files per batch, a fixed file (named by a content hash, so batches reuse it) and a batch file. Agents Read them instead of slicing the skill, reading the profile, `naming.py`, the renderer or earlier letters, and computing folder names. On 2026-10-23 that discovery was 8-10 of each agent's 12-27 calls. Each mode applies its gate (frozen, no résumé, D19's Prospect rule) and lists refused postings.
- **The letter's header, date line, salutation and sign-off** are stated in the letter packet, exactly as all 60 letters to date have them. The skill's `template.md` is Russ's draft with a different header; that choice stays open (handoff 2026-10-20).
- **Flat waves:** the main session spawns every agent with an explicit `model`, and no agent spawns another. Per batch of five: letters (Opus) beside the interest brief (Sonnet), then the draft (Opus), then the check (Sonnet, a different agent, D19).
- **Lexicon** (`scripts/keyword_lexicon.py build`, `../data/lexicon.json`): verdicts that repeat across reports, kept fresh by checking each entry's quoted template wording. Built from reports before 2026-10-23 and tested on that day's 40, verdicts agree 94% where agent and lexicon both list a term. But only 31% of lexicon terms found in a JD were terms the agent chose, so pre-filling rows would bloat the reports and their counts. Entries are therefore **hints** (`match_packet.py report --lexicon`), never rows, and the skill uses them only when Russ says so.
- **Amended by the blind test** (research: 'Experiment - Blind test of match-report models and lexicon hints'). Hints are **on by default** for report batches: Opus with hints ranked first for all three postings, with no verdict errors, against 1 for Opus alone and 2 and 5 for Sonnet with and without hints. Hints didn't save tokens (Opus +28%), so they are kept for accuracy, not cost. `match_packet.py --lexicon` rebuilds the lexicon when a report is newer. Match reports stay on **Opus**: Sonnet costs about 40% less, but it made more verdict errors and drifted from the report shape. Reports gain a **Flags** step (location against 'Baltimore, MD + remote', stated pay, contract, clearance, travel, degrees), because no test report flagged CareSource's Ohio location or salary range.
- **Measured live 2026-10-27** (15 packages, [`implementation-plan.md`](implementation-plan.md) item 22): calls per report agent 4–9, within target, but weighted tokens fell only about 7% (about 88k per report, 241k per package, against targets of 50k and 150k). Per-agent startup cost, not discovery calls, is now the main cost.

## D29 — Paid searches flag capped calls; paid sources run once a day; reports drop Slot choices and write Gaps as bullets

**2026-10-27. Accepted by Russ** (research recommendations: 'Flag capped responses in paid search records', 'Run each paid source once a day', 'Shorten match reports to cut output cost').

- **Capped flag:** `fantastic_fetch.py` and `theirstack_fetch.py` print a WARNING and write `capped: true|false` in the search record (and the raw response) when a call returns exactly its `limit`. Overflow from a capped call is not read as new postings later.
- **Once a day:** the same-day guard stays the default for Fantastic and TheirStack. Keep `limit` above the day's expected count; a second daily run waits for the Daily volume experiment.
- **Shorter reports:** no Slot choices prose (the Fields table is the record), and Gaps are one-line bullets. Russ also asked for a cap of 20 Keywords rows, **not applied**: it conflicts with the 25-35 present-term target, which needs at least 25 rows, and the conflict is unresolved.

## D30 — Streamed slices: one confirmation per slice, paid and fast sources first

**2026-10-28. Accepted (Russ, on the whiteboard: 'Agree' to the 5c amendment and to a continuous sitting of about 25 minutes).** Amends D21's one confirmation per run. Step 5 of [`elapsed-time-plan.md`](elapsed-time-plan.md).

- **One confirmation per slice**, slices in source order, at most three a run: slice 1 is the fast sources (Fantastic, TheirStack, UI/UX Jobs Board, Jobgether), slice 2 is LinkedIn, and slice 3 is Indeed if it is ever re-enabled. D21's rationale stands: no per-batch and no per-posting confirmations. A slice's approval covers every fetch in that slice; picks added afterwards need a new one.
- **Why:** the 2026-10-27 run took 127 minutes to 15 packages, 74% of it operator pauses (46 minutes between the free and paid searches). The streams model (research: 'Model of time to first package under per-source streams') projects the first package at 22-25 minutes and the last at 28-30, against 45-50 for one wave. Paid sources return in 18 seconds, stage offline and keep 68% of their rows. LinkedIn is pacing-bound (about 4 minutes, D16) and runs in the background.
- **Cost accepted:** a second confirmation, and one continuous sitting of about 25 minutes instead of two sittings.
- **Implemented the same day.** `select_candidates.select(records, only=...)` reads the whole day's records, so a later slice lists only rows new to it. `retrieve.py search` restricts records to the sources of the call. Runbook Step 1 and the `/job-retrieval` skill describe the streamed run. One call with no `--sources` still gives a single shortlist and one confirmation.
- **Unchanged:** LinkedIn pacing and stops (D16), frozen material (D13), the match-report gate (D20, D22), the independent interest checker (D19), source order and dedupe (D21), paid sources once a day (D29).
- **`--paid` is standard** (step 2a): it is part of the standard search line.
- **One retrieval run and its package wave per session** (step 2b), replacing one run per session. A split session cost a 28-minute boundary and a second prime.
- **Indeed is disabled** (`indeed: enabled: false`): 2 of 74 cards were folded on 2026-10-27. D14 stands for when it returns.
- **Interest briefs start when the match report lands** (step 3): the packet reads the match report only.
- **Test, not yet measured:** `--timeline` on the next run shows the first package ready at or under 25 minutes from `/job-retrieval`, all at or under 30, two or three confirmations, and tokens per package no higher than about 241k weighted.

## D31 — Honcho is standalone: the Portfolio automation retires, no data is copied in, dotpm stays

**2026-11-02. Decided by Russ** (whiteboard; revises decisions 2 and the copy stage of `migration-plan.md`).

- **Standalone:** Honcho is a separate project, not a new home for the old automation's data. The automation in the Portfolio vault (`business development/automation`, its `data/`, `source/` and `goals/Application Tracking/`) is deprecated. Code and docs are ported from it; nothing reads from it.
- **No data copied in:** Honcho's tasks, packages and run records start with its own runs (the first on 2026-10-31). **Cost accepted:** Select dedupes only against Honcho's tasks, so a posting tracked only in the old project's 623 tasks can come back (39 of the 10-31 keeps matched old Job IDs).
- **dotpm stays:** postings are tracked in Honcho's own dotpm project, `applications/DEFAULT.md` with `applications/_tasks/`. The plan to replace dotpm with plain notes (migration stage 3) is cancelled. D13's frozen check keeps reading dotpm's 'done' toggle.

## D32 — One path layer: the run profile names every input; `naming.py` resolves every path

**2026-11-02. Accepted by Russ.**

- `honcho.yaml` (gitignored) names the run profile, `profiles/<name>.md`; `HONCHO_PROFILE` overrides it for one run. The profile's frontmatter names one file per input kind under `applicant/` (dossier, rules, criteria, résumé and letter templates, questions, style, project), matched by stem, case-insensitively.
- `naming.py` resolves every path from the repo root and the profile: inputs, `applications/`, `logs/` (inbox, searches, runs, fit, fixtures, lexicon). `python3 pipeline/scripts/naming.py paths` prints them. Scripts import them, and skills and the job-fetcher name an input by its role plus that label instead of hardcoding a file.
- Env overrides are `HONCHO_*` (`HONCHO_PROFILE`, `HONCHO_LOGS`, `HONCHO_APPLICATIONS`, `HONCHO_BACKUPS`, `HONCHO_LEXICON`), replacing `AUTOMATION_*`.

## D33 — The repo ships generic DEFAULT inputs; an install's own content stays gitignored

**2026-11-02. Accepted by Russ.**

- Every `applicant/<kind>/DEFAULT.*` is a generic template with `<placeholder>` text. An install copies it to `<profile>.*` and points its profile there. The renderers refuse `< >` (D9), so a placeholder left in a résumé or letter stops the render.
- Russ's résumé template, letter template and truth rules moved to `applicant/<kind>/russ.md`. The skill folders no longer hold `template.md` copies.
- No personal content in code: `match_packet.py` reads the letter header from the profile's letter template and the sign-off name from the dossier's `name:`, and résumé metadata records the template path it used.

## D34 — Scripts live in three folders and share their common code

**2026-11-02. Accepted by Russ** (three folders, shared source code, delete the Fit script).

- **Layout.** `pipeline/scripts/` keeps the path layer and the cross-cutting commands at its root (`naming.py`, `retrieve.py`, `setup_check.py`, `measure_sessions.py`). The job-board scripts are in `sources/`. Select, the titles index, the fold and the task links are in `tracking/`. Packets, the lexicon, the renderers and the charset lint are in `package/`. Every documented command path was updated. Paths in D1 to D33 are history.
- **Shared code, one copy each.** The five source scripts import `sources/common.py`: Stop and Fail with their exit codes 1 and 2, `q`, `safe_write`, `find_search`, the `sources:` opt-in check (D17) and the API key reader. Pacing, parsing and hard stops stay in each script. `naming.py` holds the one frontmatter reader (`split`) and YAML quoting (`q`). `package/match_report.py` holds the match-report table readers, so the packets and the lexicon no longer import a renderer and build without python-docx or reportlab.
- **Removed.** `apply_fit_scores.py`, the CLI for D6's Fit batches: `logs/fit/` and `fit-rubric.md` were not migrated, and Fit is out of scope (D20). Its `set_values` helper, the only part in use, moved to `tracking/fold_jobs_into_tasks.py`. The Fit custom fields stay on the tasks. Also removed: `render_docx.py`'s unreachable `main()` (left from the derive script, D13) and `safe_name`, a wrapper for `naming.safe`.
- **Fixed on the way.** `measure_sessions.py` did not parse below Python 3.12, and its model-name shortening never matched. `charset.py` now lints `questions.md` (CLAUDE.md's form-safe rule) and no longer walks `applicant/resumes/`, whose templates hold `{{ slot }}` markers.

## D35 — The criteria file groups by concern: fit, selection, then one block per source

**2026-11-03. Requested by Russ** (the old structure hurt DX).

- **Before.** LinkedIn's `defaults`, `incremental`, `searches` and `selection` sat at the top level beside the other sources' blocks; the top-level `selection:` mixed LinkedIn's pacing with policy every source shares; `fit_check` sat in `selection` away from `fit`; each source's on/off flag sat in a separate `sources:` list, away from its settings.
- **After.** Three groups. `fit:` holds the check and its prose (`check` replaces `selection: fit_check`). `selection:` holds only what every source shares (`batch_size`, `exclude_title_terms`). `sources: <source>:` holds everything about one source: `enabled`, `pacing` (`max_fetches_per_run`, `fetch_delay_seconds`), `defaults`, `searches`, and what only it has (LinkedIn's `incremental`, UI/UX's `exclude_types`). Values did not change.
- **Callers.** `sources/common.py` returns the source's block for every source (LinkedIn's special case is gone) and adds `block` and `pacing`; `retrieve.py`, `naming.py fit`, `setup_check.py` and `select_candidates.py` read the new paths. A file in the old layout is refused by the source scripts and reported by `setup_check.py`, not silently misread. Specs keep the old key paths as history.

## D36 — The Résumé variant field is retired

**2026-11-03. Requested by Russ** (a stale property left over from the first proof of concept).

- **Removed.** The task's _Résumé variant_ custom field: its definition in the project note, the "Ready for submission" view's condition on it, and its kanban cards. Its row in `fold_jobs_into_tasks.py`'s field mapping and its values on the 13 tasks that had one were removed too. `render_resume.py` no longer writes it.
- **The résumé link lives in the links block.** The task's `<!-- links -->` block (`task_links.py`) already links the `.docx` from the files on disk, and the render refreshes it. "Ready for submission" keeps its meaning through its Cover letter condition: a letter can't render without the résumé.
- Supersedes D7's 'The Résumé variant field links the `.docx` only' and the field's place in D5's mapping. The _Cover letter_ field stays.

## D37 — The Portfolio applications are migrated into Honcho

**2026-11-03. Requested by Russ** (reverses D31's 'No data copied in'; the rest of D31 stands).

- **Copied once, Portfolio only read.** All 623 tasks from the old `goals/Application Tracking/_tasks/` and the 402 packages from `business development/data/applications/` that belong to them. Not copied: run records, `lexicon.json` (`keyword_lexicon.py build` rebuilds it from the match reports), interview transcripts, and two loose files in the packages folder (`README.md`, `Capital One - Senior Manager, Product Design.md`). Select now dedupes against all 665 tasks, so the cost D31 accepted is gone.
- **dotpm needs no conversion.** Honcho's project note was cloned from the old one: same custom-field ids, same `config.statuses`. dotpm owns a task by its file's folder (`_tasks/`, with `_tasks/Archive/` archived) and keys it by its frontmatter `id`; `taskIds` only orders. No ids collided. Each task's `projectId` and body `Project:` link were repointed at `applications/DEFAULT`; the new tasks were appended to `taskIds` in the old project's order.
- **Same Job ID in both trackers (5): the Portfolio task wins.** Talkiatry, UpMetrics, ECP (Applied) and Lingraphica, Consertus (Won't Do) replaced Honcho's bare Prospect duplicates.
- **Same name, different posting (8): the Portfolio task takes the collision id** (`<Company> (<job_id>) - <Job title>`, `unique_title`'s rule), and its package folder follows: Haystack, Vanta, UnitedHealth Group, CVS Health, Dandy, ParentSquare, HighLevel, Custom Ink. The two old Custom Ink tasks shared one package; it went to 4478611390 (Applied), whose id its match report and letter carry. The package's `resume.md` carries the other id, and it is frozen, so it was left as is.
- **Fields.** `task_links.py` rebuilt the links blocks. The _Cover letter_ field was repointed at Honcho's package folders (every target checked). The retired _Résumé variant_ values (D36) were dropped from the 366 tasks that had one.

## D38 — Each task's progress counts four package files

**2026-11-03. Requested by Russ** (whiteboard: a rough measure of progress per application, for task-management UX).

- **Four dotpm checkbox fields** in the project note: _Has résumé_ (the résumé `.docx` and `.pdf` together count as one), _Has cover letter_ (the letter's `.docx`), _Has match report_ (`match-report.md`), _Has questions_ (`questions.md`, or the legacy `application-questions.md`). They default to false.
- **`progress`** (dotpm's own field, an integer percent it shows as 'N%') is the share checked: 0, 25, 50, 75 or 100. dotpm never computes it, so the script owns it.
- **One owner: `task_links.py`.** Its `refresh()` already reads each posting folder for the links block, so it now also sets the four boxes and `progress`. The fold and both renderers call it, so a résumé or letter render updates the task. Match reports and questions are written by agents, so their skills run `task_links.py --write <job_id>...` (new: job ids limit the run to those tasks) after writing.
- **Views.** The kanban cards that showed the retired Résumé variant now show `progress`. In the same edit, D36's removals from the project note were applied again.
- **Edit the project note with the vault open, never closed.** dotpm keeps no cache of its own, but at startup it loads the project from Obsidian's metadata cache (IndexedDB), which can still hold the old frontmatter, and writes that back. That is how D36 came undone, and how the first edit of these fields was lost when the vault reopened. With the vault open, Obsidian re-indexes the outside edit straight away. Better still, add custom fields in dotpm's settings: its API can't.
