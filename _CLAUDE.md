---
title: "Honcho — Claude Code Entrypoint"
description: "Work in progress: Claude Code entrypoint for the Honcho job-retrieval and résumé-tailoring automation."
type: index
status: draft
tags:
  - entrypoint
  - automation
---

# Honcho — Claude Code Entrypoint

Job-search automation: retrieve posts from job boards by criteria, read their contents, and generate résumés tailored to the particulars of the posts. Scripts do the mechanical work: searching every source, pacing, staging, folding and rendering (`pipeline/scripts/retrieve.py` runs retrieval end to end). You run the judgment steps: confirming the shortlist with the operator, sending Chrome sources to the `job-fetcher` subagent, and writing match reports, résumés, cover letters and interest statements through the skills. The session never calls a job board's MCP tools directly; the scripts do.

The vault's [`../../CLAUDE.md`](../../CLAUDE.md) auto-loads. Its **Session start** steps (content-strategy handoffs and memory) don't apply here, so skip them.

## Repo and workspace boundaries

This folder is its own git repo (`datainkio/automation`). Run git from here. Its siblings are **not in any repo**, so edits to them have no history and can't be undone with git:

| Path (from here)                    | Role                                                                                                                                                   | In git? |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------- |
| `.`                                 | Runbook, config, scripts, skills, decisions                                                                                                            | yes     |
| `../data/searches/`                 | One record per search run, plus `titles-index.md`                                                                                                      | no      |
| `../data/inbox/`                    | Staged `<job_id>.md` waiting to be folded (transient)                                                                                                  | no      |
| `../data/resumes/<title-slug>/`     | Cluster **base** `master.md` (shared tailoring, never submitted)                                                                                       | no      |
| `../data/applications/<task name>/` | One posting's folder (1:1): `resume.md` + `Russell Lebo - <Title>.docx` + `.pdf`, and `cover-letter.md` + `Russell Lebo - <Title> - Cover Letter.docx` | no      |
| `../source/professional-profile.md` | The **only** allowed source of facts about Russ                                                                                                        | no      |
| `../vocabulary/`                    | Controlled vocabulary (read-only copy, authored upstream in content strategy)                                                                          | no      |
| `../../goals/Application Tracking/` | One dotpm task per posting: `_tasks/<Company> - <Job title>.md`                                                                                        | no      |

Since D5 (2026-10-06), the tasks are the **only** copy of each job description. Before a bulk edit to `_tasks/`, copy the affected files to the scratchpad.

## Context load tier

- **Session start** (continuing earlier work): read the handoff marked `status: active` in [`context/handoffs/`](context/handoffs).
- **Fast path** (lookup, quick edit, question): this file, then the one target file.
- **Retrieval run**: [`runbook.md`](runbook.md), [`config/search-criteria.yaml`](config/search-criteria.yaml), [`config/README.md`](config/README.md), [`../data/README.md`](../data/README.md) (schemas). LinkedIn and UI/UX Jobs Board are read by scripts (D15, D16), which the main session runs in the background for the whole selection (D21). `pipeline/scripts/retrieve.py` runs every script source's search, then stage, as one command each (D26, POC). Chrome sources are fetched by the [`job-fetcher`](./.claude/agents/job-fetcher.md) subagent, never in the main session (D12). The fit check is off for now (`selection: fit_check`).
- **Résumé tailoring**: the `resume-tailoring` skill, which is the only operational authority. Don't read its spec, [`specs/resume-tailoring-skill-spec.md`](specs/resume-tailoring-skill-spec.md), to run it: the spec holds only rationale, ATS research and history.
- **Cover letters**: the `cover-letter-writing` skill, the only operational authority (its spec, [`specs/cover-letter-skill-spec.md`](specs/cover-letter-skill-spec.md), is rationale only). It needs the posting's résumé to exist first. Up to five letters per agent, one render call per batch.
- **Interest statements**: the `interest-statement` skill, the only operational authority (the why is D19). It needs the posting's match report, and writes only for postings at Prospect.
- **Why something is the way it is**: [`context/decisions.md`](context/decisions.md). D5 supersedes D3 and D4.
- **Current state and the fix list**: [`context/implementation-plan.md`](context/implementation-plan.md). Update it when you close an item.

## Hard rules

- **Human-paced LinkedIn only.** The server drives Russ's real logged-in browser and has no rate limiting. LinkedIn is read only through `pipeline/scripts/linkedin_fetch.py` (D16), which enforces `selection.max_fetches_per_run` and waits `fetch_delay_seconds` before every call. If it stops on an automation warning or a login, captcha or security-check page, stop: don't retry. Close this session's LinkedIn tools first (`mcp__linkedin__close_session`) if any were used. Never schedule unattended or high-frequency runs. Confirm with Russ once per run, on the combined shortlist of every source, before any fetch (D21).
- **Jobgether is a second source (D10)**, run by hand like LinkedIn: see the runbook's Jobgether section. Its search runs by script (`pipeline/scripts/jobgether_fetch.py`, D26), which keeps 2 seconds between requests. Read listing pages only through Russ's Chrome.
- **Indeed is a third source (D14)**, searched and read only on indeed.com in Russ's Chrome: see the runbook's Indeed section. Wait 8 seconds between every page load. Read search results only from visible cards and never open the hidden decoy card. Stop on any Cloudflare check, sign-in wall or unusual-traffic message. Indeed's own connector (`mcp__claude_ai_Indeed__*`) is not used: its ids aren't stable.
- **UI/UX Jobs Board is a fourth source (D15)**, read only through `pipeline/scripts/uiux_board.py` (plain HTTP, 5 seconds between requests, enforced by the script): see the runbook's UI/UX Jobs Board section. Never fetch it with WebFetch, curl or a browser outside that script. If the script stops on a Cloudflare page, a block or an error status, don't retry. The fallback is the Chrome route, which needs a spec change.
- **Fantastic.jobs is a fifth source (D23)**, a paid API read only through `pipeline/scripts/fantastic_fetch.py`: see the runbook's Fantastic.jobs section. It bills per job returned. Only `search --write` calls it, and `limit` caps every call. Never raise `limit` or add searches without Russ. If the script stops on a 401, 403, 429 or 5xx, don't retry.
- **TheirStack is a sixth source (D24)**, a paid API read only through `pipeline/scripts/theirstack_fetch.py`: see the runbook's TheirStack section. One credit per job returned. Only `search --write` calls it, and `limit` caps every call. Never raise `limit` or add searches without Russ. If the script stops on a 401, 402, 403, 429 or 5xx, don't retry.
- **Verbatim JDs.** The staged body is the description as the source returned it (for LinkedIn and UI/UX Jobs Board, cut and written by the script). Never invent structure, fields, or values the tool didn't return. The one exception is the `<!-- links -->` block under each task's title (Posting, Résumé, Cover letter). `pipeline/scripts/task_links.py` owns it, and the fold script re-inserts it after every write. Don't edit it by hand.
- **Honest tailoring.** A résumé changes emphasis and language, never facts. Every claim must trace to `professional-profile.md`. A required JD term with no backing goes on the gap list, not into the résumé. The binding truth rules are in the skill (M.S. is candidate status, program-scale numbers are never personal outcomes, MUSE → MoAR, no invented metrics).
- **dotpm field ids are opaque.** `customFields` values are keyed by id. Look ids up by name in the `Application Tracking.md` project note and never hard-code them. Renaming a field is safe. Deleting and recreating one orphans its values.
- **Form-safe text.** Résumé and cover-letter text never contains `< > { } "` (or curly `“ ”`): application forms reject them and block submission. Write `p under 0.10`, not `p<0.10`, and quote JD phrases with single quotes. The renderers refuse a body that has one; `python3 pipeline/scripts/charset.py` lints every master (D9).
- **Application Tracking statuses mean hiring stages**, not the standard workflow: `todo` = Prospect, `in-progress` = Preparing, `blocked` = Applied, `review` = Screening, `done` = Interviewing, `cancelled` = Finalist, and `status-*` are custom stages. Never change a posting's stage unless Russ asks. The fold script keeps existing status.
- **Submitted material is frozen (D13).** Never edit, re-derive or re-render the résumé or cover letter of a posting at Applied (`blocked`), Screening (`review`), or any status with dotpm's "done" toggle (`complete: true` in the project note's `config.statuses`). `naming.frozen_statuses()` reads the toggle live; `render_resume.py` and `render_cover_letter.py` refuse them. Hand edits follow the same rule.
- **Vocabulary values are conceptIds** (filenames in `../vocabulary/concepts/`), never labels. Terms that don't exist yet go in `../vocabulary/candidates.md`. Never create concepts here.
- No credentials in the repo. The LinkedIn session lives in `~/.linkedin-mcp/`, and `.env` is gitignored.

## Key commands

```bash
uvx mcp-server-linkedin@latest --status     # check the session before a run
uvx mcp-server-linkedin@latest --login      # re-auth (opens a real browser; Russ solves captcha/2FA)

python3 pipeline/scripts/fold_jobs_into_tasks.py                    # dry run: inbox → tasks report
python3 pipeline/scripts/fold_jobs_into_tasks.py --write --consume  # apply, then delete the staged notes
python3 pipeline/scripts/task_links.py [--write]                    # refresh each task's Posting / Résumé / Cover letter links (from files on disk)
python3 pipeline/scripts/render_resume.py <job_id> [--write]       # match report, once Matching approved is checked → resume.md, .docx, .pdf, Résumé variant link (D20, D22)
python3 pipeline/scripts/charset.py                                 # lint résumé/cover-letter masters for < > { } " “ ” (exit 1 if any)
python3 pipeline/scripts/retrieve.py search [--write] --paid [--incremental]   # every enabled script source's search at once, paid ones included, then Select: one shortlist by source (D26); plan only without --write
python3 pipeline/scripts/retrieve.py stage [--write] --shortlist <tsv> [--only <id>…] [--except <id>…]   # stage approved picks per source, print job-fetcher lines, fold dry run
python3 pipeline/scripts/jobgether_fetch.py search --all [--write] [--quiet]   # Jobgether searchJobs over HTTP, 2 s apart → ../data/searches/YYYY-MM-DD--jg-<name>.md
python3 pipeline/scripts/linkedin_fetch.py search --all [--write] [--quiet]               # LinkedIn search_jobs → ../data/searches/YYYY-MM-DD--<name>.md (D16)
python3 pipeline/scripts/linkedin_fetch.py search --all --incremental [--write]          # same-day second pass: last 24 hours, 1 page
python3 pipeline/scripts/linkedin_fetch.py stage [--write] <search>=<job_id>...           # get_job_details → ../data/inbox/<id>.md, whole selection in one run; one line per posting
python3 pipeline/scripts/uiux_board.py search <name> [--write]                    # UI/UX Jobs Board list page(s) → rows; --write saves ../data/searches/YYYY-MM-DD--<name>.md
python3 pipeline/scripts/uiux_board.py stage [--write] <search>=<path>...          # job pages → ../data/inbox/<id>.md; one line per posting, no description text
python3 pipeline/scripts/uiux_board.py check <file.html>...                       # offline parser check on saved pages
python3 pipeline/scripts/fantastic_fetch.py search <name> [--write]           # dry run prints the request; --write makes the paid call, saves ../data/searches/YYYY-MM-DD--fj-<name>.json + .md (D23)
python3 pipeline/scripts/fantastic_fetch.py stage [--write] <search>=<job_id>...   # inbox notes from the saved response; no network, no credits
python3 pipeline/scripts/theirstack_fetch.py search <name> [--write]          # dry run prints the request; --write makes the paid call, saves ../data/searches/YYYY-MM-DD--ts-<name>.json + .md (D24)
python3 pipeline/scripts/theirstack_fetch.py stage [--write] <search>=<job_id>...  # inbox notes from the saved response; no network, no credits
python3 pipeline/scripts/unique_titles.py [--write]                 # merge new titles into ../data/searches/titles-index.md (keeps Fit)
python3 pipeline/scripts/select_candidates.py <search records…>     # Select step, every source: drop tracked/staged/repeat/excluded jobs; prints keep/drop lines
python3 pipeline/scripts/naming.py ids                              # dotpm custom-field ids by name (never read the project note for them)
python3 pipeline/scripts/naming.py fit                              # the config's fit block, as the job-fetcher reads it, or 'Fit check: off'
python3 pipeline/scripts/naming.py interest                         # postings with a match report: ok / skip and whether a statement exists (D19)
python3 pipeline/scripts/naming.py reports                          # Prospects without a match report: due (critical) / skip (D27); batches write only the due rows
python3 pipeline/scripts/match_packet.py report|letter|interest <ids>   # two files an agent Reads instead of discovering its inputs (D28); reports: --due --lexicon
python3 pipeline/scripts/keyword_lexicon.py build|show              # repeat keyword verdicts → ../data/lexicon.json; hints, never rows (D28); match_packet rebuilds it when stale
python3 pipeline/scripts/measure_sessions.py [--since YYYY-MM-DD]     # tokens, weighted cost and minutes per session from the transcripts; --session <id> lists its agents; --timeline <id> [--gap MIN] prints calls, operator pauses and agent spans against the clock
python3 pipeline/scripts/setup_check.py                             # install readiness: paths, profile, truth rules, config, tracking, Python modules (exit 1 if missing)
```

Both scripts are idempotent, and both do a dry run unless given a flag. `unique_titles.py` merges: it keeps hand-scored Fit values and frontmatter and adds new titles unscored. Escape a literal `|` in a run-table title as `\|`.

The fold also creates any missing field definitions on the project note.

MCP tools: retrieval no longer calls `mcp__linkedin__search_jobs` or `get_job_details` in a session (D16): `linkedin_fetch.py` calls them through its own server. `python3 pipeline/scripts/linkedin_fetch.py check ../data/fixtures/linkedin/*.json` tests its parser offline. Never use the messaging or connection tools (`send_message`, `connect_with_person`) without an explicit request.

## Session habits

One retrieval run and its package wave per session, then handoff, `/clear`, `/prime`. Sonnet for retrieval, config and docs; Opus for résumé bases, cover letters, specs and decisions. Details: the runbook's 'Session and token habits'.

## Definition of done

| Task                 | Verify                                                                                                                                                                                                                                                                                  |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Search run           | `../data/searches/YYYY-MM-DD--<name>.md` exists, matches the schema, and lists a non-empty `job_ids` table. Name incremental runs `…-incremental.md`. Then run `unique_titles.py --write`.                                                                                              |
| JD retrieval         | The fold dry run shows the expected jobs. After `--write --consume`, each `<Company> - <Job title>.md` has its custom fields filled, its body is the JD, and `../data/inbox/` is empty.                                                                                                 |
| Résumé (per posting) | Meets the skill's acceptance criteria: the match report has its count and gaps and Russ has checked the task's Matching approved box (D22), `Russell Lebo - <Title>.docx` and `.pdf` render, `charset.py` exits 0, and the task's Résumé variant links the `.docx` (never `resume.md`). |
| Interest statement   | The posting passes `naming.py interest`; `interest.md` holds the brief and a `## Check`; `why-interested.md` is 3-5 sentences with every check finding applied or dropped; `charset.py` exits 0.                                                                                        |
| Script change        | Dry run against the real inbox/tasks shows no unintended diffs before any `--write`.                                                                                                                                                                                                    |
| Docs                 | Links resolve from the file's own location. Update `decisions.md` when a decision changes.                                                                                                                                                                                              |

Commits use conventional prefixes (`feat|fix|docs|chore|refactor…`). Never break a line mid-sentence in a commit message: each sentence or bullet stays on one line, however long.

## Searching

The corpus is small (~19k words) and fits one context window, so a plain `rg` over this folder plus `../data` answers cross-file questions. This repo has no knowledge graph (the one built 2026-10-06 was deleted 2026-10-29 as stale). The JD corpus has one, in `goals/Application Tracking/`, with its build and cost rules in [`context/jd-graph-insights.md`](context/jd-graph-insights.md). The task folder has ~180 files, so grep frontmatter rather than reading files:

```bash
ls "../../goals/Application Tracking/_tasks/<Company> - <Job title>.md"          # tasks are named by company and title; find one by id with: rg -l "<job_id>" "../../goals/Application Tracking/_tasks"
grep -lE '^status: "?todo' "../../goals/Application Tracking/_tasks/"*.md         # Prospects (quoted or unquoted)
```
