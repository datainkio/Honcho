---
title: "Runbook — Job Retrieval"
description: "Operating procedure for one retrieval session: search each source by criteria, select, stage job descriptions, then fold them into Application Tracking tasks."
type: runbook
status: active
tags:
  - automation
  - linkedin
  - runbook
  - jobgether
date: 2026-10-29
---

# Runbook — Job Retrieval

> **The `/job-retrieval` skill ([`pipeline/skills/job-retrieval/SKILL.md`](skills/job-retrieval/SKILL.md)) is now the operational authority for a retrieval run**, with one reference file per source. This runbook keeps the full history and the shared rationale. If they disagree, the skill wins.

Operating procedure for one retrieval session. Followed by an operator or an agent with the `linkedin` MCP server connected. Both steps are read-only against LinkedIn (`search_jobs`, `get_job_details` are `readOnlyHint`).

## Preconditions

1. `uvx mcp-server-linkedin@latest --login` has been run and the session is valid (`uvx mcp-server-linkedin@latest --status` reports OK, or the first tool call opens a login window).
2. Only one active LinkedIn session for this account (the server serializes calls on a single browser). `pipeline/scripts/sources/linkedin_fetch.py` starts its own server, so if this Claude Code session has called a `mcp__linkedin__*` tool, call `mcp__linkedin__close_session` first.
3. `.env` exists (copied from `.env.example`) if you want to override defaults.

## Step 1 — Retrieve jobs fitting the criteria

**One command per slice (D26, D30):** `python3 pipeline/scripts/retrieve.py search --write --paid [--sources a,b]` runs the named sources' searches (default: every enabled script source) concurrently, merges the titles, runs Select over the day's records and lists only the rows from this call's records, one shortlist grouped by source (saved as `logs/runs/<stamp>-search/shortlist.tsv`). Streamed run: start `--sources linkedin` in the background, run `--sources fantastic,theirstack,uiux,jobgether --paid` in the foreground, confirm that slice 1 and stage, fold and start its package wave, then do the same for LinkedIn when it finishes (at most three confirmations; D30). `--paid` stays explicit: nothing paid runs without it, but it is part of the line, not a decision after the free shortlist. A single call with no `--sources` gives one shortlist. Add `--incremental` for a same-day LinkedIn pass. After approval, `python3 pipeline/scripts/retrieve.py stage --write --shortlist <tsv> [--only …] [--except …]` stages every script source and prints the job-fetcher lines for Chrome picks. Without `--write` both print the plan and call nothing. Indeed is off (2026-10-28). The steps below are what it runs, and the fallback.

**Check `sources:` in the criteria file (`naming.py paths`, row `criteria`) first (D17).** Run a source only if its `enabled` is true; a missing entry means off, except Jobgether, which defaults on. `linkedin_fetch.py` and `uiux_board.py` refuse a disabled source themselves. For Jobgether and Indeed, which run through MCP and Chrome, the check is yours: skip the section when disabled.

Run the searches with the script (D16), never by calling `search_jobs` in the session:

```bash
python3 pipeline/scripts/sources/linkedin_fetch.py search --all --write --quiet     # or name searches instead of --all
python3 pipeline/scripts/tracking/unique_titles.py --write
```

It merges each entry of the criteria file (`naming.py paths`, row `criteria`) with `defaults:`, calls `search_jobs` 4 seconds apart (mapping: [`applicant/criteria/README.md`](../applicant/criteria/README.md)), and writes `logs/searches/YYYY-MM-DD--<search-name>.md` with `type: linkedin-search-run` and the table of returned jobs. `--quiet` prints only a count per search: read the shortlist in Step 2, not the results. Exit 1 means it stopped on a hard rule; don't retry.

**Acceptance (MVP criterion 1):** a search run produces a non-empty `job_ids` list, recorded to `logs/searches/`.

## Step 2 — Retrieve job-description content for local analysis

A full description costs about 3.5k tokens, so select before fetching, from the titles and companies in the search `sections`. Apply the `selection:` policy from the criteria file:

1. Run `python3 pipeline/scripts/tracking/select_candidates.py logs/searches/<this run's records>.md`. It drops every job that already has a task (by Job ID, or by company and title with legal suffixes, '&'/'and' and a trailing title suffix ignored; reposts get a new `job_id`), is already staged, repeats within the run, or has an `exclude_title_terms` title. It reads the records in a fixed source order, paid APIs first and LinkedIn last, so a job several sources list is kept from the source whose description is cheapest to get and the LinkedIn fetch is skipped (D21). It prints one `keep` or `drop` line per job. Read its `keep` lines, not the search results. The same command serves every source below.
2. Subsidiaries and person-named companies still slip past it (Counterpart Health is Clover Health's role); check those by eye.
3. Choose the most plausible fits from the rest (judgment against the profile/résumé source; full fit-scoring is out of MVP scope). Fetch an ambiguous title rather than guess. Cap at `max_fetches_per_run`.

Since D21 (2026-10-20) the main session stages the whole LinkedIn selection with one background call, written `<source_search>=<job_id>` so it spans every search: `python3 pipeline/scripts/sources/linkedin_fetch.py stage --write <search>=<job_id> …`. It calls `get_job_details` 4 seconds apart and stages `logs/inbox/<job_id>.md`: frontmatter + the **verbatim** description as the body. It prints one line per posting (`id | company | title | staged or skipped: reason | over100 or -`) and no description text. The fit check is off for now (`selection: fit_check: false`); when on, one `job-fetcher` agent ([`pipeline/agents/job-fetcher.md`](agents/job-fetcher.md)) checks the staged notes. The skill's Step 3 has the ordering.

Record the skips in the search-run record. The fold sets each new task's priority (D27): critical, or medium when the LinkedIn note carries `over100: true`. Don't set it by hand; change one only when Russ asks. If a subagent reports an automation warning, stop the run.

After the last batch, fold the inbox into Application Tracking tasks — dry run first, then apply:

```bash
python3 pipeline/scripts/tracking/fold_jobs_into_tasks.py
python3 pipeline/scripts/tracking/fold_jobs_into_tasks.py --write --consume
```

Each staged note becomes (or refreshes) the task `<Company> - <Job title>.md`: frontmatter → dotpm custom fields, JD text → task description. The staged note is deleted once folded. An existing task keeps its status and history. A new task's `due` date is set to its retrieved date.

**Acceptance (MVP criterion 2):** `applications/_tasks/<Company> - <Job title>.md` exists, its custom fields are filled, and its description is the JD text. Ranked view: [`Priority.md`](../../goals/Application%20Tracking/Priority.md).

## Jobgether (second source)

Jobgether searches across companies with no login. It joins the flow at the inbox, so everything from the fold on is the same as above. Design and field mapping: [`specs/integrated-datasources-spec.md`](specs/integrated-datasources-spec.md). Manual runs only.

1. **Search.** `python3 pipeline/scripts/sources/jobgether_fetch.py search --all --write --quiet` (D26) calls the same `searchJobs` tool over HTTP, 2 seconds apart, and writes `logs/searches/YYYY-MM-DD--jg-<name>.md` (`type: jobgether-search-run`) for each search that found jobs within `max_age_days`. A search with none writes no record. `retrieve.py search` runs it for you. Don't call `mcp__jobgether__searchJobs` in the session: its results would enter the context.
2. **Select.** Run `python3 pipeline/scripts/tracking/select_candidates.py` on the record (Step 2 above): it also drops placeholder companies such as "Our Team!". Then apply the `selection:` policy.
3. **Fetch and stage** through the `job-fetcher` subagent ([`pipeline/agents/job-fetcher.md`](agents/job-fetcher.md)), with `source: jobgether`. It opens each `url` in Russ's Chrome (`navigate`, then `get_page_text` as a separate call), 2 seconds apart, and keeps only the `Job description` section (up to `More` / `About the company`); the rest of the page is Jobgether's own material. The API has no description, and scripted requests to listing pages get 403. A page that says "Offer not found" is skipped, not retried. Staged notes are `logs/inbox/<id>.md` with `type: jobgether-job` and `source_search: jg-<name>`. Then fold as in Step 2 above.

## Indeed (third source)

**Disabled since 2026-10-28** (`indeed: enabled: false`): it folded 2 of 74 cards on 2026-10-27. Skip this section and the job-fetcher Indeed lines until Russ turns it back on; D14 stands.

Indeed is searched and read on indeed.com in Russ's signed-in Chrome (Claude in Chrome), and since 2026-07-01 it carries Glassdoor's listings too. It joins the flow at the inbox, so everything from the fold on is the same as above. Design and field mapping: [`specs/integrated-datasources-spec.md`](specs/integrated-datasources-spec.md) (D14). Manual runs only. Wait 8 seconds between page loads, search and listing pages alike: run `await new Promise(r => setTimeout(r, 8000))` with `javascript_tool` before each `navigate` after the first.

1. **Search.** For each entry under `indeed: searches:` in the criteria file (`naming.py paths`, row `criteria`) (merging `indeed: defaults:`), `navigate` to `https://www.indeed.com/jobs?q=<keywords>&l=Remote&fromage=<fromage>&sort=date`. Then read the cards with `javascript_tool`, never with `get_page_text`:

   ```js
   const seen = new Set(), rot = '0123456789abcdef'.repeat(2);
   [...document.querySelectorAll('a[data-jk]')]
     .filter(a => !a.closest('[aria-hidden="true"]') && a.offsetWidth > 0 && a.offsetHeight > 0)
     .map(a => { const c = a.closest('li') || a.parentElement;
       return { jk: a.dataset.jk, title: a.innerText.trim(),
         company: c.querySelector('[data-testid="company-name"]')?.innerText.trim() ?? '',
         location: c.querySelector('[data-testid="text-location"]')?.innerText.trim() ?? '' }; })
     .filter(r => /^[0-9a-f]{16}$/.test(r.jk) && !rot.includes(r.jk) && r.company && !seen.has(r.jk) && seen.add(r.jk))
   ```

   It keeps visible cards only and drops the hidden decoy card, whose key is a run of consecutive hex digits. It also drops the 'Positions in …' carousel cards, which show no company or location and ignore the search filters. One page per search is enough: with `fromage` at 14 or less, no pager appears. **Never open a decoy key.** Write `logs/searches/YYYY-MM-DD--ind-<name>.md` with `type: indeed-search-run` and the usual table (`jk` in the `job_id` column).
2. **Select.** Run `python3 pipeline/scripts/tracking/select_candidates.py` on the record (Step 2 above). Indeed often lists the same posting as LinkedIn, with legal suffixes added ('Conservice LLC'); the script strips them. Then apply the `indeed: selection:` policy. The picks join the run's one combined shortlist (D21).
3. **Fetch and stage** through the `job-fetcher` subagent with `source: indeed`. It opens `https://www.indeed.com/viewjob?jk=<jk>` (`navigate`, then a separate call), reads only the description with `javascript_tool` (`document.querySelector('#jobDescriptionText')?.innerText`) and falls back to `get_page_text`, cut from the `Full job description` heading to `Report job`, only when that returns null, and reads `posted` from the page's JSON-LD `datePosted` with `javascript_tool`. Staged notes are `logs/inbox/<jk>.md` with `type: indeed-job` and `source_search: ind-<name>`. Then fold as in Step 2 above.

**Stop the run** on a Cloudflare page ('Verify you are human', 'Just a moment'), a sign-in wall, or any message about unusual traffic. Don't retry.

## UI/UX Jobs Board (fourth source)

UI/UX Jobs Board (uiuxjobsboard.com) is a design-only board. Unlike the other sources it is read by a script, `pipeline/scripts/sources/uiux_board.py`, over plain HTTP, with no browser and no sign-in. It joins the flow at the inbox, so everything from the fold on is the same as above. Design and field mapping: [`specs/integrated-datasources-spec.md`](specs/integrated-datasources-spec.md#uiux-jobs-board-2026-10-12) (D15). Manual runs only, when Russ asks. The script waits 5 seconds between requests, list and job pages alike.

1. **Search.** For each entry under `uiux: searches:` in the criteria file (`naming.py paths`, row `criteria`) (merging `uiux: defaults:`), run `python3 pipeline/scripts/sources/uiux_board.py search <name> --write`. It saves `logs/searches/YYYY-MM-DD--uiux-<name>.md` with `type: uiux-search-run`. Zero cards on page 1 is an error, never 'nothing new'. Then run `python3 pipeline/scripts/tracking/unique_titles.py --write`.
2. **Select.** Run `python3 pipeline/scripts/tracking/select_candidates.py` on the record (Step 2 above). It also drops `exclude_types` (Internship) and marks Featured cards `check:` so you can confirm they're in the search's location. Skip companies that are a person's name by eye. Then apply the `uiux: selection:` policy and plausibility judgment. The picks join the run's one combined shortlist (D21).
3. **Fetch and stage** yourself, in the background (D21): `python3 pipeline/scripts/sources/uiux_board.py stage --write uiux-<name>=<path> …`, once for the whole selection, with each job's `path` from the search record (a bare id returns 404). The fit check follows `selection: fit_check` (off for now). Staged notes are `logs/inbox/<id>.md` with `type: uiux-job` and `source_search: uiux-<name>`. Then fold as in Step 2 above: dry run, then `--write --consume`.

**Stop the run** when the script exits 1: a list-page error, a 403, 429 or 5xx, a Cloudflare page ('Just a moment', 'Attention Required', 'Verify you are human'), or two job pages in a row missing markers (the layout has probably changed). Don't retry. Exit 2 is a usage or config error, such as a search with zero cards on page 1. If Cloudflare starts challenging plain requests, the fallback is the Chrome route, as for Indeed. That is a spec change, not a workaround in the script.

## Fantastic.jobs (fifth source)

Fantastic.jobs is a paid API (D23) over company career pages (Greenhouse, Lever, Workday, Ashby and about 55 more applicant-tracking systems) and job boards. It is read by `pipeline/scripts/sources/fantastic_fetch.py`, and it is billed per job returned, so `limit` in the `fantastic:` config block caps each call's cost (10 during the MVP). The key is `FANTASTIC_JOBS_API_KEY` in `.env`. Manual runs only, when Russ asks.

1. **Search.** `python3 pipeline/scripts/sources/fantastic_fetch.py search <name>` prints the request and makes no call. Add `--write` to make the paid call. It saves the raw response as `logs/searches/YYYY-MM-DD--fj-<name>.json` and the record as `…--fj-<name>.md` (`type: fantastic-search-run`). It refuses a second call for the same search on the same day. Then run `python3 pipeline/scripts/tracking/unique_titles.py --write`.
2. **Select.** Run `select_candidates.py` on the record, as for every source. Its picks join the run's one combined shortlist (D21).
3. **Stage.** `python3 pipeline/scripts/sources/fantastic_fetch.py stage --write fj-<name>=<job_id> …` writes `logs/inbox/<job_id>.md` (`type: fantastic-job`) from the saved response. It makes no network call and uses no credits. Then fold as above.

**Stop the run** when the script exits 1: a 401, 403, 429 or 5xx, or a network error. Don't retry. A 401 or 403 usually means a bad key or an exhausted plan.

## TheirStack (sixth source)

TheirStack is a paid API (D24) over job boards (mostly Indeed and LinkedIn) and company career pages. It is read by `pipeline/scripts/sources/theirstack_fetch.py` and costs one credit per job returned, so `limit` in the `theirstack:` config block caps each call's cost. The key is `THEIRSTACK_API_KEY` in `.env`. Manual runs only, when Russ asks.

1. **Search.** `python3 pipeline/scripts/sources/theirstack_fetch.py search <name>` prints the request and makes no call. Add `--write` to make the paid call. It saves the raw response as `logs/searches/YYYY-MM-DD--ts-<name>.json` and the record as `…--ts-<name>.md` (`type: theirstack-search-run`). It refuses a second call for the same search on the same day. Then run `python3 pipeline/scripts/tracking/unique_titles.py --write`.
2. **Select.** Run `select_candidates.py` on the record with the run's other records. It reads Fantastic before TheirStack and both before every other source, so jobs Fantastic already returned drop as repeats, and LinkedIn jobs TheirStack returned need no LinkedIn fetch. Its picks join the run's one combined shortlist (D21).
3. **Stage.** `python3 pipeline/scripts/sources/theirstack_fetch.py stage --write ts-<name>=<job_id> …` writes `logs/inbox/<job_id>.md` (`type: theirstack-job`) from the saved response. It makes no network call and uses no credits. Then fold as above.

**Stop the run** when the script exits 1: a 401, 402, 403, 429 or 5xx, or a network error. Don't retry. A 401, 402 or 403 usually means a bad key or no credits left.

## Session and token habits

Measured in [`context/token-efficiency-review.md`](context/token-efficiency-review.md) (F2, F8).

- **One retrieval run and its package wave per session (2026-10-28).** Run retrieval, then the package wave (`naming.py reports`, the resume-tailoring batch steps, letters and interest statements) in the same session; write the handoff, then `/clear` and `/prime` after the wave. A split session cost a 28-minute boundary and a second prime. Start the next task fresh.
- **Model per task type.** Run retrieval, config edits and doc updates on Sonnet (`/model sonnet`). Keep Opus for résumé bases, cover letters, specs and decisions.
- **Overlap the sources.** Start the LinkedIn and UI/UX stage commands in the background, then work the Chrome sources (Jobgether, Indeed) while they run. They share no browser. Fold once, at the end.
- **Second pass in a day: `search --all --incremental`** (last 24 hours, 1 page).
- **Chrome-driven fetches write, then forget.** The job-fetcher writes each description straight to its inbox note and never quotes it back. Read only the description element, not the whole page, where the source allows it (Indeed above).
- **Read the shortlist, not the results.** Read `select_candidates.py`'s `keep` lines, never the raw `search_jobs` output or the full record table.

## Guardrails

- Respect `max_fetches_per_run`. If LinkedIn shows an automation warning, stop and reduce volume.
- UI/UX Jobs Board is read only through `pipeline/scripts/sources/uiux_board.py`. Never fetch it any other way.
- Do not run unattended on a tight schedule. Targeted searches beat broad sweeps.
- If a tool call returns a setup/auth-in-progress error, wait for browser setup or re-run `--login`, then retry.
- Timeouts: raise `TOOL_TIMEOUT` (seconds) for cold starts / multi-page searches; raise `TIMEOUT` (ms) for slow page ops.

## Troubleshooting

| Symptom                            | Action                                                                                        |
| ---------------------------------- | --------------------------------------------------------------------------------------------- |
| "setup/authentication in progress" | Wait for Chromium prep; or `uvx mcp-server-linkedin@latest --login`, then retry               |
| Captcha on login                   | `--login` opens a real browser — solve it manually                                            |
| Empty `job_ids`                    | Loosen filters (wider `date_posted`, more `work_type`/`experience_level`, higher `max_pages`) |
| Tool call times out                | Increase `TOOL_TIMEOUT`; reduce `max_pages`                                                   |
| Session expired                    | Re-run `--login` (one active session at a time)                                               |
