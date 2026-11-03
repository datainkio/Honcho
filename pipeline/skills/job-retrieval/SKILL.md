---
name: job-retrieval
description: Run one job-retrieval session. Searches the enabled sources, selects fits, stages descriptions through the job-fetcher agent and folds them into tracking tasks. Manual runs only.
disable-model-invocation: true
model: sonnet
---

# /job-retrieval

One retrieval session: search, select, fetch, fold. You are the runner. Work from the Honcho repo root, where `python3 pipeline/scripts/…` resolves. The search criteria are the active profile's `criteria` file, (`naming.py paths`, row `criteria`); `python3 pipeline/scripts/naming.py paths` lists every resolved path. Run `python3 pipeline/scripts/setup_check.py` first if you haven't set up this install (`/job-setup`).

**One retrieval run and its package wave per session.** After Step 4, run Step 5; finish with a handoff, then `/clear`. Run on Sonnet; the job-fetcher runs on Haiku.

## Rules

- **One confirmation per run (D21).** Present the run's combined shortlist once, grouped by source, and fetch nothing until the operator approves it. That approval covers every source's fetch in the run; a run that adds picks afterwards asks again. Runs are manual and human-paced. Never schedule one, and never run unattended.
- **Check `sources:` in the criteria file first (D17).** Run a source only if its `sources: <source>: enabled` is true. A missing entry means off, except Jobgether, which defaults on. The LinkedIn and UI/UX scripts refuse a disabled source themselves. For Jobgether and Indeed the check is yours.
- **Load only the reference for the source you are running.** Don't read the other sources' references.
- **Descriptions never enter this session.** The LinkedIn and UI/UX scripts write them straight to the inbox and print one line per posting (D21). The `job-fetcher` agent reads the Chrome sources. Read the shortlist (`keep` lines), never raw search output, a full record table or a staged note.
- **Stop on any hard stop** a reference names (automation warning, login or captcha page, Cloudflare check, sign-in wall, a script exiting 1). Don't retry.
- Verbatim JDs: never invent structure, fields or values a source didn't return.

## Sources

| Source | Default | Route | Reference |
|---|---|---|---|
| Jobgether | on | search API, no login; listing pages read in the operator's Chrome | below |
| LinkedIn | opt-in | `pipeline/scripts/sources/linkedin_fetch.py` (logged-in browser) | [`references/linkedin.md`](references/linkedin.md) |
| Indeed | disabled 2026-10-28 | the operator's Chrome (Claude in Chrome) | [`references/indeed.md`](references/indeed.md) |
| UI/UX Jobs Board | opt-in | `pipeline/scripts/sources/uiux_board.py` (plain HTTP) | [`references/uiux.md`](references/uiux.md) |

Opt-in sources are read through routes their terms restrict. `/job-setup` records the operator's choice, so don't re-ask. Ask which enabled sources to run this session.

## Step 1: search

**Streamed fast path (D26, D30).** Two slices, fast sources first, so the first package starts about 20 minutes in instead of after LinkedIn. Both calls read the whole day's records, so slice 2 lists only what slice 1 didn't.

1. Start LinkedIn in the background: `python3 pipeline/scripts/retrieve.py search --write --sources linkedin` (pacing-bound, about 4 minutes; D16). Add `--incremental` for a same-day pass.
2. Run the fast sources in the foreground (seconds): `python3 pipeline/scripts/retrieve.py search --write --paid --sources fantastic,theirstack,uiux,jobgether`. `--paid` stays explicit, part of this line and not a separate decision. It prints slice 1: one shortlist grouped by source.
3. **Confirmation 1** (D30): show slice 1. Then `python3 pipeline/scripts/retrieve.py stage --write --shortlist <tsv> [--only <id>…] [--except <id>…]`, fold (Step 4), and start the package wave for the new Prospects (Step 5) without waiting for LinkedIn. Russ may ask for a first batch of two or three paid postings to get one package out early, at one extra agent startup.
4. When LinkedIn finishes, its output is **slice 2**: Select already dropped what slice 1 listed. **Confirmation 2**, then stage, fold and a second package wave the same way.

A `[source] STOPPED` line is a hard stop. At most three confirmations a run (Indeed, if re-enabled, is a third slice). Running both sources in one call (`search --write --paid` with no `--sources`) still works and gives one shortlist and one confirmation: use it when Russ wants a single sitting. After approval, `stage` prints the job-fetcher lines for Jobgether picks. The per-source steps below remain the fallback.

**Paid sources run once a day.** Fantastic and TheirStack bill per job returned and their 24-hour windows overlap, so a same-day re-run mostly re-buys jobs already seen; the scripts refuse a second call for the same search on the same day, so keep that guard. Keep `limit` above the day's expected count. When a call returns exactly its `limit`, the script prints a WARNING and writes `capped: true` in the search record: the source likely had more, so a later call's overflow is not new postings, and `limit` needs raising. Decide on a second daily run only after the Daily volume experiment reports the rate.

Otherwise, search each enabled source as its reference (or the Jobgether section below) says. Every search writes one record to `logs/searches/YYYY-MM-DD--<name>.md`. Name an incremental run `…-incremental.md`. Then merge the new titles:

```bash
python3 pipeline/scripts/tracking/unique_titles.py --write
```

**Done when** each search record exists, matches the search-record schema (in the old automation repo's `data/README.md`, not yet migrated), and lists a non-empty `job_ids` table. An empty list is an error, not 'nothing new': loosen the filters instead.

## Step 2: select

A full description costs about 3.5k tokens, so choose before fetching.

1. Once every enabled search is done, run `python3 pipeline/scripts/tracking/select_candidates.py logs/searches/<this run's records>.md` once over all of them, every source together. It drops every job that already has a task (by job id, or by company and title with legal suffixes and '&'/'and' ignored), is already staged, repeats within the run, or has an excluded title. It prints one `keep` or `drop` line per job. Read the `keep` lines. The same command serves every source.
2. Subsidiaries and person-named companies still slip past it. Check those by eye.
3. Choose the most plausible fits against the profile, within `selection: batch_size` and each source's `pacing: max_fetches_per_run`. Fetch an ambiguous title rather than guess.
4. Present one shortlist, grouped by source, and get one confirmation for the whole run.

## Step 3: fetch and stage

**Script sources (LinkedIn, UI/UX Jobs Board): run the stage command yourself, once per source, for the whole selection (D21).** Write each id as `<source_search>=<id>` (UI/UX: `<source_search>=<path>`, the path from the search record) so one call spans every search:

```bash
python3 pipeline/scripts/sources/linkedin_fetch.py stage --write design-manager=4300000001 experience-designer=4300000002 …
python3 pipeline/scripts/sources/uiux_board.py stage --write uiux-remote-us=/job/<id>-<slug> …
```

Start them with Bash `run_in_background` and go on with the Chrome sources while they run: the LinkedIn server drives its own browser profile (`~/.linkedin-mcp/profile/`), the board is plain HTTP, and neither touches the operator's Chrome. Never run two LinkedIn processes at once. A background exit 1 is a hard stop like any other: on its exit notification read only the last line, and stop the whole run, Chrome work included. Each prints one line per posting, with `over100` or `-` for LinkedIn.

**Fit check: off for now** (`fit: check: false`; `python3 pipeline/scripts/naming.py fit` says so). Every staged note goes to the fold (Fit batches were removed, D34). When it is on, give the staged ids to one `job-fetcher` agent with `source: staged` once both scripts have finished.

**Chrome sources (Jobgether, Indeed):** use the `job-fetcher` agent (`model: haiku`), never the main session. Split the selection into batches of `batch_size` and run **one batch at a time** (they share the operator's Chrome). Give each batch its `source` and one line per job: `job_id`, title, company, `source_search`. Each reply is one line per job: `id | company | title | staged or skipped: reason | over100 or -`.

Record the skips in the search-run record. The fold sets each new task's priority (D27): critical, or medium when the LinkedIn note carries `over100: true`. Don't set it by hand; change one only when the operator asks. If a script or an agent reports a hard stop, stop the run.

**Fold once,** after every source has finished.

## Step 4: fold

Dry run first, then apply:

```bash
python3 pipeline/scripts/tracking/fold_jobs_into_tasks.py
python3 pipeline/scripts/tracking/fold_jobs_into_tasks.py --write --consume
```

Each staged note becomes (or refreshes) the task `<Company> - <Job title>.md` in the tracking project. An existing task keeps its status and history. Never change a posting's stage unless the operator asks. Before a bulk edit to `_tasks/`, copy the affected files to the scratchpad, since the tasks hold the only copy of each description.

**Done when** the dry run shows the expected jobs and, after `--write --consume`, each task has its custom fields filled, its body is the JD, and `logs/inbox/` is empty.

## Step 5: package wave

Same session, no `/clear` between. Run `python3 pipeline/scripts/naming.py reports` and write match reports for its `due` rows with the resume-tailoring skill's batch steps (Step 3 there), then stop at Matching approved (D22). As each report batch lands, start its interest briefs (interest-statement skill, Batches). After Russ checks Matching approved: render, letters and drafts, checks, `charset.py`. Then the handoff. In a streamed run (Step 1), do this once per slice: slice 1's wave runs while LinkedIn finishes.

## Jobgether

Jobgether searches across companies with no login. It joins the flow at the inbox, so everything from the fold on is the shared flow above. Manual runs only.

1. **Search.** `python3 pipeline/scripts/sources/jobgether_fetch.py search --all --write --quiet` (D26) calls the same `searchJobs` tool over HTTP, 2 seconds apart, and writes `logs/searches/YYYY-MM-DD--jg-<name>.md` (`type: jobgether-search-run`) for each search that found jobs within `max_age_days`. A search with none writes no record. `retrieve.py search` runs it for you. An empty Jobgether search is normal, not the error Step 1 describes. Don't call `mcp__jobgether__searchJobs` in the session: its results would enter the context.
2. **Select.** As Step 2. The script also drops placeholder companies such as 'Our Team!'.
3. **Fetch and stage** with `source: jobgether`. The agent opens each listing `url` in the operator's Chrome (`navigate`, then `get_page_text` as a separate call), 2 seconds apart, and keeps only the `Job description` section (up to `More` / `About the company`). The API returns no description, and scripted requests to listing pages get 403. A page that says 'Offer not found' is skipped, not retried. Staged notes are `logs/inbox/<id>.md` with `type: jobgether-job` and `source_search: jg-<name>`.

## Troubleshooting

| Symptom | Action |
|---|---|
| Empty `job_ids` | Loosen filters: wider `date_posted`, more `work_type` or `experience_level`, higher `max_pages` |
| A script exits 1 | A hard stop. Read its last line, report it, don't retry |
| A script exits 2 | A usage or config error, such as a search with zero cards on page 1. Fix the config |
| `mcp__jobgether__searchJobs` missing | Enable the `jobgether` server from [`.mcp.json`](../../../.mcp.json) and restart the session |
| Tool call times out | Raise `TOOL_TIMEOUT` (seconds) or `TIMEOUT` (ms) in `.env`; reduce `max_pages` |
