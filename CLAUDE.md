---
title: Honcho — Claude Code Entrypoint
description: Claude Code entrypoint for the Honcho job-retrieval and résumé-tailoring automation.
type: entrypoint
status: draft
tags:
  - entrypoint
  - automation
---

# Honcho — Claude Code Entrypoint

Job search and tailored resume automation.
Retrieve posts from job boards by criteria, read their contents, and generate application materials tailored to the particulars of the posts. Scripts do the mechanical work: searching every source, pacing, staging, folding and rendering (`pipeline/scripts/retrieve.py` runs retrieval end to end). You run the judgment steps: confirming the shortlist with the operator, sending Chrome sources to the `job-fetcher` subagent, and writing match reports, résumés, cover letters and interest statements through the skills. The session never calls a job board's MCP tools directly; the scripts do.
This project is inspired by but separate from the work done in the portfolio.

## Repo and workspace boundaries

This folder is its own git repo (`datainkio/honcho`). Run git from here.

## Context load tier

## Session habits

Continuing work? Read the handoff marked `status: active` in [`context/handoffs/`](context/handoffs).
One retrieval run and its package wave per session, then handoff, `/clear`.
Optimize for token efficiency when assigning work. Sonnet for retrieval, config and docs; Opus for résumé bases, cover letters, specs and decisions.

### Fast path

Lookup, quick edit, question: this file, then the one target file.

## Retrieval

the `job-retrieval` skill, which is the only operational authority.

## Résumé tailoring

the `resume-tailoring` skill, which is the only operational authority.

## Cover letter writing

the `cover-letter-writing` skill, the only operational authority. It needs the posting's résumé to exist first. Up to five letters per agent, one render call per batch.

## Interest statement

the `interest-statement` skill, the only operational authority. It needs the posting's match report, and writes only for postings at Prospect status. Deprecate in favor of question-answers.

## Question answers

the question-answers skill, the only operational authority. It needs the posting's match report, and writes only for postings at Prospect status. Replaces interest-statement.

## Hard rules

### Interacting with job boards as datasources

Job boards have different policies and different degrees of openness when exposing data. Retrieving that data requires a range of methods from accessing open APIs to human emulation in-browser. The list below provides a high-level view of how each datasource is implemented.

#### LinkedIn

The server drives the operator’s real logged-in browser and has no rate limiting. `pipeline/scripts/sources/linkedin_fetch.py` enforces `selection.max_fetches_per_run` and waits `fetch_delay_seconds` before every call to emulate human behavior to avoid automation warnings. If it stops on an automation warning or a login, captcha or security-check page, stop: don't retry.
Close this session's LinkedIn tools first (`mcp__linkedin__close_session`) if any were used.

#### Jobgether

Search runs by script (`pipeline/scripts/sources/jobgether_fetch.py`), which keeps 2 seconds between requests. Read listing pages only through the operator’s Chrome

#### Indeed

Searched and read only on indeed.com through Chrome. Wait 8 seconds between every page load. Read search results only from visible cards. Never open the hidden decoy cards. Stop on any Cloudflare check, sign-in wall or unusual-traffic message. Indeed offers its own connector (`mcp__claude_ai_Indeed__*`), but it is not used here: its ids aren't stable.

#### UI/UX Jobs Board

Searched and read only through `pipeline/scripts/sources/uiux_board.py` (plain HTTP, 5 seconds between requests, enforced by the script). Never fetch it with WebFetch, curl or a browser outside that script. If the script stops on a Cloudflare page, a block or an error status, don't retry. The fallback is the Chrome route.

#### Fantastic.jobs

A paid API read only through `pipeline/scripts/sources/fantastic_fetch.py`. It bills per job returned, and so limits are imposed here. Only `search --write` calls it, and `limit` caps every call. Never raise `limit` or add searches without operator approval. If the script stops on a 401, 402, 403, 429 or 5xx, don't retry.

#### TheirStack

A paid API read only through `pipeline/scripts/sources/theirstack_fetch.py`. One credit per job returned. Only `search --write` calls it, and `limit` caps every call. Never raise `limit` or add searches without operator approval. If the script stops on a 401, 402, 403, 429 or 5xx, don't retry.

### Job Descriptions

The staged body is the description as the source returned it (for LinkedIn and UI/UX Jobs Board, cut and written by the script). Never invent structure, fields, or values the tool didn't return. The one exception is the `<!-- links -->` block under each task's title (Posting, Résumé, Cover letter, Questions). `pipeline/scripts/tracking/task_links.py` owns it, and the fold script re-inserts it after every write. Don't edit it by hand.

### Honest tailoring

A tailored résumé changes emphasis and language, never facts. Every claim must trace to the dossier specified by the operator. A required job description term with no backing goes on the gap list for review by the operator, not into the résumé. The binding truth rules are in the skill.

### Form-safe text

`python3 pipeline/scripts/package/charset.py` lints every master resume, cover letter, and questions file. Résumé, cover letter, and questions text never contains `< > { } "` (or curly `“ ”`): application forms reject them and block submission. Write `p under 0.10`, not `p<0.10`, and quote job description phrases with single quotes.

### Tracking statuses

The status values for tracking a job application do not map onto traditional workflows:

Never change a posting's stage unless Russ asks. The fold script keeps existing status.

### Submitted material is frozen

Never edit, re-derive or re-render the résumé, cover letter, or questions text of a posting at Applied (`blocked`), Screening (`review`), or any status with dotpm's "done" toggle (`complete: true` in the project note's `config.statuses`). `naming.frozen_statuses()` reads the toggle live; `render_resume.py` and `render_cover_letter.py` refuse them. Hand edits follow the same rule.

### Credentials

No credentials in the repo. `.env` is gitignored.

## Key commands

```bash
uvx mcp-server-linkedin@latest --status     # check the session before a run
uvx mcp-server-linkedin@latest --login      # re-auth (opens a real browser; Russ solves captcha/2FA)

python3 pipeline/scripts/tracking/fold_jobs_into_tasks.py                    # dry run: inbox → tasks report
python3 pipeline/scripts/tracking/fold_jobs_into_tasks.py --write --consume  # apply, then delete the staged notes
python3 pipeline/scripts/tracking/task_links.py [--write]                    # refresh each task's Posting / Résumé / Cover letter links (from files on disk)
python3 pipeline/scripts/package/render_resume.py <job_id> [--write]       # match report, once Matching approved is checked → resume.md, .docx, .pdf, Résumé variant link (D20, D22)
python3 pipeline/scripts/package/charset.py                                 # lint résumé/cover-letter masters for < > { } " “ ” (exit 1 if any)
python3 pipeline/scripts/retrieve.py search [--write] --paid [--incremental]   # every enabled script source's search at once, paid ones included, then Select: one shortlist by source (D26); plan only without --write
python3 pipeline/scripts/retrieve.py stage [--write] --shortlist <tsv> [--only <id>…] [--except <id>…]   # stage approved picks per source, print job-fetcher lines, fold dry run
python3 pipeline/scripts/sources/jobgether_fetch.py search --all [--write] [--quiet]   # Jobgether searchJobs over HTTP, 2 s apart → logs/searches/YYYY-MM-DD--jg-<name>.md
python3 pipeline/scripts/sources/linkedin_fetch.py search --all [--write] [--quiet]               # LinkedIn search_jobs → logs/searches/YYYY-MM-DD--<name>.md (D16)
python3 pipeline/scripts/sources/linkedin_fetch.py search --all --incremental [--write]          # same-day second pass: last 24 hours, 1 page
python3 pipeline/scripts/sources/linkedin_fetch.py stage [--write] <search>=<job_id>...           # get_job_details → logs/inbox/<id>.md, whole selection in one run; one line per posting
python3 pipeline/scripts/sources/uiux_board.py search <name> [--write]                    # UI/UX Jobs Board list page(s) → rows; --write saves logs/searches/YYYY-MM-DD--<name>.md
python3 pipeline/scripts/sources/uiux_board.py stage [--write] <search>=<path>...          # job pages → logs/inbox/<id>.md; one line per posting, no description text
python3 pipeline/scripts/sources/uiux_board.py check <file.html>...                       # offline parser check on saved pages
python3 pipeline/scripts/sources/fantastic_fetch.py search <name> [--write]           # dry run prints the request; --write makes the paid call, saves logs/searches/YYYY-MM-DD--fj-<name>.json + .md (D23)
python3 pipeline/scripts/sources/fantastic_fetch.py stage [--write] <search>=<job_id>...   # inbox notes from the saved response; no network, no credits
python3 pipeline/scripts/sources/theirstack_fetch.py search <name> [--write]          # dry run prints the request; --write makes the paid call, saves logs/searches/YYYY-MM-DD--ts-<name>.json + .md (D24)
python3 pipeline/scripts/sources/theirstack_fetch.py stage [--write] <search>=<job_id>...  # inbox notes from the saved response; no network, no credits
python3 pipeline/scripts/tracking/unique_titles.py [--write]                 # merge new titles into logs/searches/titles-index.md (keeps Fit)
python3 pipeline/scripts/tracking/select_candidates.py <search records…>     # Select step, every source: drop tracked/staged/repeat/excluded jobs; prints keep/drop lines
python3 pipeline/scripts/naming.py ids                              # dotpm custom-field ids by name (never read the project note for them)
python3 pipeline/scripts/naming.py fit                              # the config's fit block, as the job-fetcher reads it, or 'Fit check: off'
python3 pipeline/scripts/naming.py interest                         # postings with a match report: ok / skip and whether a statement exists (D19)
python3 pipeline/scripts/naming.py reports                          # Prospects without a match report: due (critical) / skip (D27); batches write only the due rows
python3 pipeline/scripts/package/match_packet.py report|letter|interest <ids>   # two files an agent Reads instead of discovering its inputs (D28); reports: --due --lexicon
python3 pipeline/scripts/package/keyword_lexicon.py build|show              # repeat keyword verdicts → logs/lexicon.json; hints, never rows (D28); match_packet rebuilds it when stale
python3 pipeline/scripts/measure_sessions.py [--since YYYY-MM-DD]     # tokens, weighted cost and minutes per session from the transcripts; --session <id> lists its agents; --timeline <id> [--gap MIN] prints calls, operator pauses and agent spans against the clock
python3 pipeline/scripts/setup_check.py                             # install readiness: paths, profile, truth rules, config, tracking, Python modules (exit 1 if missing)
```

## Definition of done

| Task                 | Verify                                                                                                                                                                                                                                                                                  |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Search run           | `logs/searches/YYYY-MM-DD--<name>.md` exists, matches the schema, and lists a non-empty `job_ids` table. Name incremental runs `…-incremental.md`. Then run `unique_titles.py --write`.                                                                                                 |
| JD retrieval         | The fold dry run shows the expected jobs. After `--write --consume`, each `<Company> - <Job title>.md` has its custom fields filled, its body is the JD, and `logs/inbox/` is empty.                                                                                                    |
| Résumé (per posting) | Meets the skill's acceptance criteria: the match report has its count and gaps and the operator has checked the task's Matching approved box, `First Last - <Title>.docx` and `.pdf` render, `charset.py` exits 0, and the task's Résumé variant links the `.docx` (never `resume.md`). |
| Questions            | The posting passes `naming.py questions; `questions.md`holds the brief and a`## Check`; `questions.md`is 2-3 short, concise sentences for each question;`charset.py` exits 0.                                                                                                           |
| Script change        | Dry run against the real inbox/tasks shows no unintended diffs before any `--write`.                                                                                                                                                                                                    |
| Docs                 | Links resolve from the file's own location. Update `context/decisions.md` when a decision changes.                                                                                                                                                                                              |
|                      |                                                                                                                                                                                                                                                                                         |

Commits use conventional prefixes (`feat|fix|docs|chore|refactor…`).

## Searching

The corpus is small (~20k words) and fits one context window, so a plain `rg` over this folder (staged notes and run records are under `logs/`) answers cross-file questions. The tasks folder (`applications/_tasks/`) may have more than 100 files, so grep frontmatter rather than reading files:

```bash
ls "applications/_tasks/<Company> - <Job title>.md"          # tasks are named by company and title; find one by id with: rg -l "<job_id>" "applications/_tasks"
grep -lE '^status: "?todo' "applications/_tasks/"*.md         # Prospects (quoted or unquoted)
```
