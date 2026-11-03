---
description: "Integrate other datasources into the flow of job posts"
type: spec
status: accepted
date: 2026-10-08
---

## User Stories

- As a person looking for a job, I want to know within five minutes when a new job becomes available so that I can increase my chances of my application being seen when I apply. **Not met by this spec:** see Decisions.
- As an agent listening for when new jobs become available, I want to retrieve data from public JSON feeds of open roles so that Russ can respond quickly

## Requirements

- The API must allow searches for job posts without requiring a company (and thus limiting any value)
- The LinkedIn flow stays as it is. The new source must not change the LinkedIn steps, task fields, or [`Priority.md`](../../../goals/Application%20Tracking/Priority.md).

## Decisions (2026-10-08)

- **Datasource:** [Jobgether](https://jobgether.com/developers). It searches across companies with no key, through REST (`jobgether.com/api/v1/jobs`) or MCP (`jobgether.com/mcp`, tool `searchJobs`).
- **Trigger: manual only.** Russ or an agent runs it on request, like LinkedIn. The 15-minute schedule is dropped, so the five-minute story isn't met. Jobgether also lags the original posting by days, so only the employers' own feeds could meet it.
- **Pacing:** 2 seconds between requests, the `Crawl-delay` in Jobgether's `robots.txt`.
- **Scope:** full-remote roles in the United States or Anywhere.
- **Job description:** read from the Jobgether listing page in Russ's Chrome, for selected postings only. The API returns no description.
- **Model:** Sonnet at low effort. Search, duplicate checks, and staging are mechanical.

## What the API returns

One search returns up to 25 jobs per page and 10 pages. Each job has `id` (24 hex characters), `title`, `company`, `url` (the Jobgether listing), `location`, `remote`, `contractType`, `experience`, `salaryRange`, `jobFunctions`, and `postedAt` (an exact date). There's no description and no single-job lookup. The listing page carries the full text and an Apply link to the employer's own site. Scripted requests to listing pages get 403; a browser reads them.

Some results hide the employer behind a placeholder name ("Our Team!", "Remote Office"). Skip those.

## Design: Jobgether joins at the inbox

A Jobgether posting is staged in `logs/inbox/` like a LinkedIn one. From there the fold, tasks, fit scoring, résumés, and cover letters run unchanged.

1. **Search.** Call `searchJobs` once per entry under `jobgether:` in the criteria file (`naming.py paths`, row `criteria`) (mapping: [`applicant/criteria/README.md`](../../applicant/criteria/README.md#jobgether-searchjobs)). Write a record to `logs/searches/YYYY-MM-DD--jg-<name>.md`, using the LinkedIn table layout.
2. **Select.** Skip a result if a task already has its id, if a task already has the same company and title (the same posting found on LinkedIn), or if its company is a placeholder. Match on each task's `title` frontmatter, not its file name, because dotpm renames files. Then apply the `selection:` cap and plausibility judgment.
3. **Fetch.** Open each selected listing in Chrome (`get_page_text`), 2 seconds apart.
4. **Stage** `logs/inbox/<id>.md`:

| Inbox field | From |
| --- | --- |
| `type` | `jobgether-job` |
| `job_id` | `id` |
| `url` | `url` |
| `title`, `company`, `location` | same names |
| `work_type` | `remote`: Full Remote becomes `remote` |
| `posted` | `postedAt` (date) |
| `retrieved_at` | fetch time |
| `source_search` | `jg-<name>` (the prefix marks the source, so no new field) |
| body | the page text, verbatim |

5. **Fold** with `fold_jobs_into_tasks.py`, unchanged.

## Changes

- `.mcp.json`: add the `jobgether` server.
- The criteria file (`naming.py paths`, row `criteria`): add a `jobgether:` block with its own `defaults`, `searches` and `selection`. The LinkedIn blocks stay as they are.
- `pipeline/scripts/naming.py`: the ` (<job_id>)` suffix that separates same-named tasks only matches digits. Widen both regexes to accept a 24-character hex id.

Nothing else changes in code.

## Acceptance

- A `jg-` search record exists, and `unique_titles.py --write` merges its titles.
- After staging two or three postings, the fold dry run shows only those tasks being created.
- Each new task has its custom fields filled, Search `jg-…`, Posting the Jobgether link, and the page text as its description.
- `task_links.py` dry run shows no changes to existing tasks.

## Pilot findings (2026-10-08)

One search (`jg-ux-designer`, 25 results) and three postings folded: Clover Health, Consilio, Clearwater. The acceptance list passed, and no existing task changed.

- **Duplicate check works.** Four of 25 results already had tasks (Northbeam, Mark43, MeridianLink, HealthEquity) and were skipped by company and title.
- **Stage only the `Job description` section.** The listing page wraps it in Jobgether's own material: an AI-written role overview, a sign-in "match analysis" filled with placeholder data, related jobs, and the footer. The staged body runs from the text after the `Job description` heading up to the `More` / `About the company` line, verbatim.
- **One role can appear under two companies.** Clover Health's Staff UX Designer is Counterpart Health's role (its subsidiary), also listed separately as Counterpart Health. Company plus title doesn't catch this; read the description's opening before selecting.
- **The Chrome extension must be connected.** If `/chrome` shows Installed but not Connected, quit the Claude desktop app and restart Chrome.

## Indeed (2026-10-12)

**Accepted 2026-10-12, after the pilot** (see [Pilot findings](#indeed-pilot-findings-2026-10-12)). Decision: D14 in [`context/decisions.md`](../../context/decisions.md).

### Decisions

- **Datasource:** [Indeed](https://www.indeed.com), searched and read on indeed.com in Russ's signed-in browser through Claude in Chrome (Browser 1). Since 2026-07-01 Glassdoor runs on Indeed's listings, so one source covers both.
- **Not Indeed's own connector.** The official connector (`mcp__claude_ai_Indeed__*`, beta) returns the full description, but it can't support this flow. See [Connector probe](#connector-probe).
- **Trigger: manual only**, like LinkedIn and Jobgether.
- **Pacing:** 8 seconds between page loads, search and listing pages alike. That is LinkedIn's spacing; Indeed's bot checks are stricter than Jobgether's.
- **Scope:** remote roles in the United States (`l=Remote`). Indeed lists many of them as 'Remote in <city>', and those count.
- **Model:** Sonnet at low effort for runs, and Sonnet for the job-fetcher. Search, duplicate checks and staging are mechanical.

### What the site returns

- **Search page:** `https://www.indeed.com/jobs?q=<keywords>&l=Remote&fromage=<days>&sort=date`. `fromage` (days since posted: 1, 3, 7 or 14) and `sort=date` both apply. Each result card is a link with `data-jk`, Indeed's 16-character hex job key, plus the title, company (`[data-testid="company-name"]`) and location (`[data-testid="text-location"]`). Cards show no posted date. Paging uses a pager below the results, but with `fromage` at 14 or less no pager appeared, so one page per search is enough. The paging parameter is unconfirmed (the extension hides query strings).
- **Decoy cards.** Each results page holds one hidden card: inside `aria-hidden="true"`, zero size, with a fake key made of consecutive hex digits (`890abcdef0123456`, `456789abcdef0123`). It is a trap for scrapers. Opening it would mark the session as a bot. Both pages seen so far used `890abcdef0123456`.
- **Carousel cards.** A 'Positions in <field>' carousel adds a few cards with `data-jk` but no company or location. They ignore the search filters (a marine sales manager appeared under 'UX designer'), so they are dropped.
- **Listing page:** `https://www.indeed.com/viewjob?jk=<jk>`. The description sits between the `Full job description` heading and the `Report job` line. Above it are Indeed's header and a `Job details` block (pay, job type), and below it are related-search links.
- **Posted date:** not in the page text. The page's JSON-LD `JobPosting` object carries `datePosted` (an ISO time in UTC) and `validThrough`.
- **No applicant count**, so a staged Indeed posting never carries `over100`.
- **Volume:** 'UX designer' over 7 days, sorted by date, gave about five results on 2026-10-12, including misfits such as a plumbing designer. The title filter and the job-fetcher's fit check do real work here.

### Design: Indeed joins at the inbox

1. **Search.** For each entry under `indeed:` in the criteria file (`naming.py paths`, row `criteria`), `navigate` to the search URL, then read the cards with `javascript_tool`: keep a card only if its link is visible and not inside `aria-hidden="true"` and it shows a company, and drop any key that is a run of consecutive hex digits (a rotation of `0123456789abcdef`). The script is in the runbook. Return `jk`, title, company and location only, never page text. Write `logs/searches/YYYY-MM-DD--ind-<name>.md` with `type: indeed-search-run` and the LinkedIn table layout.
2. **Select.** Skip a result if a task already has its `jk` as Job ID, or a task already has the same company and title (matched on each task's `title` frontmatter, as for Jobgether). Compare companies with legal suffixes removed: Indeed shows 'Conservice LLC' where LinkedIn may show 'Conservice'. Apply `exclude_title_terms`, then the `selection:` cap and plausibility judgment.
3. **Fetch** through the `job-fetcher` subagent with `source: indeed`: `navigate` to the listing, call `get_page_text` as a separate call, then read `datePosted` from the JSON-LD with `javascript_tool`. 8 seconds between listings, enforced by an in-page timer, not by tool latency.
4. **Stage** `logs/inbox/<jk>.md`:

| Inbox field | From |
| --- | --- |
| `type` | `indeed-job` |
| `job_id` | `jk`, quoted (unquoted, YAML reads a key like `1234567e89012345` as a number) |
| `url` | `https://www.indeed.com/viewjob?jk=<jk>`, with no tracking parameters |
| `title`, `company`, `location` | the result card, as shown |
| `work_type` | `remote` when the location starts with 'Remote'; `hybrid` when it starts with 'Hybrid'; otherwise empty |
| `posted` | JSON-LD `datePosted`, date part |
| `retrieved_at` | fetch time, from the system clock |
| `source_search` | `ind-<name>` (the prefix marks the source, so no new field) |
| body | the page text after the `Full job description` heading, up to the `Report job` line, verbatim |

5. **Fold** with `fold_jobs_into_tasks.py`, unchanged.

**Stop the run** on a Cloudflare page ('Verify you are human', 'Just a moment'), a sign-in wall, or any message about unusual traffic. **Skip, don't retry,** a listing that says the job has expired or is no longer available. The pilot met none, so the exact wording is still unrecorded; the job-fetcher quotes it when it first appears.

### Changes

- The criteria file (`naming.py paths`, row `criteria`): an `indeed:` block with its own `defaults` (`location: Remote`, `fromage`, `sort: date`, `max_pages: 1`), `searches` (the Jobgether phrases plus 'UX content strategist', one phrase per search, named `ind-<name>`), and `selection` (cap 25, `fetch_delay_seconds: 8`). The LinkedIn and Jobgether blocks stay as they are.
- `applicant/criteria/README.md`: the URL-parameter mapping.
- `pipeline/scripts/naming.py`: `JOB_ID` also accepts a 16-character hex id. Every existing task must parse to the same id before and after.
- `pipeline/agents/job-fetcher.md`: a `source: indeed` branch, and `mcp__claude-in-chrome__javascript_tool` in `tools:`.
- `pipeline/runbook.md`: an 'Indeed (third source)' section. `../data/README.data.md`: 'Indeed notes'. Automation `CLAUDE.md`: Indeed in the hard rules.
- `.mcp.json`: no change. Claude in Chrome is already used for Jobgether.

### Acceptance

- An `ind-` search record exists, lists only visible cards (no decoy keys), and `unique_titles.py --write` merges its titles.
- After staging two or three postings, the fold dry run shows only those tasks being created.
- Each new task has its custom fields filled: Job ID the `jk`, Search `ind-…`, Posting the `viewjob?jk=` link, Posted from `datePosted`, and the 'Full job description' text as its description.
- `task_links.py` dry run shows no changes to existing tasks.

### Connector probe

Indeed's official connector was tried first, on 2026-10-12. It works from the main session and from subagents, and its detail text matches the listing page. It fails this flow on three counts:

- **No stable id.** `Job Id` is a handle (`JOBSEARCH_1000NN`) from a counter that keeps rising across searches: the same Blue State posting was 100005, then 100011. `get_job_details` rejects Indeed's own `jk`: 'There was an error getting job details. Please try again later.', on two tries.
- **Thin search.** At most 10 results, the top of the site's relevance list. No paging, no date filter, no sort. Results ran back to February 2026, and `location: remote` let city-listed jobs through.
- **Low yield.** 15 results over two searches, about one plausible fit.

Its `get_resume` tool reads Russ's Indeed profile. That is never a source of facts; `professional-profile.md` is.

### Indeed pilot findings (2026-10-12)

- **Search:** `ind-ux-designer` (7 days, by date) gave 4 real cards, 1 hidden decoy and 3 carousel cards. The card script returned the 4 real ones. None had a task. Record: `logs/searches/2026-10-12--ind-ux-designer.md`.
- **Fetch:** three picked; the job-fetcher staged Figure Lending and Conservice and skipped CREADEVS on fit (hourly contract, not senior). Both listings had the `Full job description` and `Report job` markers and a JSON-LD `datePosted`. No Cloudflare page, sign-in wall or expired listing.
- **Verbatim check:** the Conservice task body and the page's text between the markers both run to 901 words, with the same first and last words.
- **Fold:** dry run and write created only the two tasks, with Job ID, Search, Posting, Posted, Retrieved and Work type filled. The inbox was emptied.
- **Fixed after the pilot:** the job-fetcher relied on tool latency instead of waiting 8 seconds, and wrote a placeholder `retrieved_at`. It now waits with an in-page timer (measured at 8,001 ms) and reads the system clock. `job_id` must be quoted.
- **`task_links.py` dry run:** 167 existing tasks would change, unrelated to Indeed. Most posting `.docx` files are missing from `applications/` (tracked in Business Development as 'Recover missing application .docx files'). The two new tasks' link blocks were correct.
- **Paging:** a 14-day search showed about 17 real cards and no pager, so `max_pages` is 1.

## UI/UX Jobs Board (2026-10-12)

**Accepted 2026-10-12, after the pilot** (see [Pilot findings](#uiux-jobs-board-pilot-findings-2026-10-12)). Russ had accepted the route and the product-design scope earlier the same day. Decision: D15 in [`context/decisions.md`](../../context/decisions.md). Probe log: the [task](../../../goals/Business%20Development/_tasks/retrieve-postings-from-ui-ux-jobs-board.md).

### Decisions

- **Datasource:** [UI/UX Jobs Board](https://uiuxjobsboard.com), a design-only board. Its role pages include UX research and UX writing, its Apply buttons go straight to the employer's ATS, and in the probe only 1 of 50 remote-US postings already had a task.
- **Route: a script, not a browser or a model.** `pipeline/scripts/sources/uiux_board.py` reads list and job pages over plain HTTP and writes the staged note itself. The board needs no sign-in, serves full HTML to a plain request, and its robots.txt allows everything but `/hire/success`. This is the first source read by code. D2's 'no custom code' already gave way to the fold script; the line kept here is that code does the I/O and a model does the judgment (fit).
- **Not WebFetch.** It passes the page through a model that summarizes, so the text isn't verbatim.
- **Fallback: Chrome**, the Indeed pattern, if Cloudflare starts challenging plain requests. Never work around a challenge in the script.
- **User agent:** the script names itself (`uiux_board.py`, personal job search) instead of passing as a browser. If Cloudflare challenges that, the run stops and the fallback applies.
- **Trigger: manual only**, like the other three.
- **Pacing:** 5 seconds between requests, list and job pages alike, enforced by the script. The site sets no Crawl-delay; 5 sits between Jobgether's 2 and Indeed's 8, and the probe made 21 requests at that spacing with no challenge.
- **Scope:** remote roles in the United States or Anywhere, from the location pages `remote-united-states` and `remote-anywhere`. Role pages can't be filtered by location, so titles are filtered at selection.
- **Product designer is a target role** (Russ, 2026-10-12). It dominates this board. The job-fetcher's target list is shared, so this applies to every source.
- **The employer's apply URL is not kept.** There is no inbox field for it, and the board page in `url` links to it.
- **Model:** Sonnet at low effort for runs. The job-fetcher runs on Haiku for `uiux` batches (Agent `model: haiku`), adopted by Russ after the pilot: the script does the reading, so only the fit check is left. Other sources keep Sonnet.

### What the site returns

- **List page:** `https://uiuxjobsboard.com/design-jobs/<slug>?page=<n>`, 50 cards a page, newest first, with a pager (`nav[aria-label="Pagination"]`, 'Page 1 of 6'). Each card links `/job/<id>-<slug>` and shows the company ('<Company> is hiring'), title, type (Full Time, Contract, Internship), salary when given, location ('Remote' 'United States') and age ('3h', '2d', '1mo'). No exact date. Expired cards say 'Expired' and sink to the end of the list.
- **Featured cards** carry '★ Featured' in place of the age and sit at the top of role pages (CSS order, not date), sometimes off-location. None appeared on the remote-US page.
- **Unknown slugs look like empty searches.** `/design-jobs/ux-researcher-remote-united-states` returns 200 with the words echoed into the title and no cards.
- **Some companies are people** ('Matthew Allen is hiring'), likely recruiters hiding the employer.
- **Job page:** `https://uiuxjobsboard.com/job/<id>-<slug>`. The slug is required: the bare `/job/<id>` returns 404. A header block (company, title, TYPE, CATEGORY, LOCATION, POSTED '<age> ago') ends at `</header>`. The description is `div.job-description`, ending at `</div><aside`; the sidebar's 'Share this job' follows. A JSON-LD `JobPosting` carries `title`, `hiringOrganization.name` (it matched the header on all 13 pages checked), `datePosted` (ISO, UTC), `employmentType` and `validThrough`. `validThrough` is always `datePosted` plus two months, so it says nothing about whether the role is open. Its `description` is cut at 164 characters.
- **The anatomy doesn't depend on the employer's ATS.** Greenhouse, Lever, Workday, Rippling, Workable and a company careers site all gave the same page.
- **Bodies** run 4,459 to 10,823 characters, close to LinkedIn's. They carry HTML entities (`&nbsp;`), headings, paragraphs and lists.
- **Filled job page:** still 200, with 'This role has been successfully filled!', the description and 'Share this job', but no POSTED label, no Apply button and no `JobPosting` (only `Organization`).
- **No applicant count**, so a staged posting never carries `over100`.
- **No API, RSS or JSON feed.** `/sitemaps/1.xml` lists about 1,940 job URLs with `lastmod`; it isn't needed while list pages sort by date.
- **Volume:** remote-US page 1 on 2026-10-12 held 10 postings 7 days old or less, mostly senior and staff product designer, plus UX research and a design director.

### Design: UI/UX Jobs Board joins at the inbox

1. **Search.** `python3 pipeline/scripts/sources/uiux_board.py search <name>` for each entry under `uiux:` in the criteria file (`naming.py paths`, row `criteria`). It reads page 1 of the entry's slug, then more pages up to `max_pages`, and stops at the first card that isn't Featured and is Expired or older than `max_age_days`. Featured cards have no age, so they never stop the search; they are listed and marked. Zero cards on page 1 is an error, never 'nothing new'. An age it can't read is an error too. It prints one row per card; with `--write` it saves `logs/searches/YYYY-MM-DD--uiux-<name>.md` with `type: uiux-search-run` and the LinkedIn table layout, plus `type`, `age`, `featured` and `path` columns. `path` is the card's `/job/<id>-<slug>`, which staging needs.
2. **Select.** As for Indeed: skip a card if a task already has its id as Job ID, or a task already has the same company and title (each task's `title` frontmatter, legal suffixes removed). Compare companies with '&' and 'and' removed as well, and count a tracked title that starts with the card's title as the same title ('UI/UX Designer' matches 'UI/UX Designer \| AI Powered Products'). Skip `exclude_types` (Internship), Featured cards outside the search's location, and companies that are a person's name: the employer is hidden, so duplicates can't be caught. Apply the shared `exclude_title_terms`, then the `selection:` cap and plausibility judgment. Subsidiaries (Counterpart Health and Clover Health) still need a read of the opening.
3. **Fetch and stage** through the `job-fetcher` subagent with `source: uiux`. It runs `python3 pipeline/scripts/sources/uiux_board.py stage --search <name> --write <path>…` once per search in its batch. The script fetches each job page 5 seconds apart, writes `logs/inbox/<id>.md`, and prints one line per posting, never description text. The job-fetcher then reads each staged note, checks fit, and deletes a misfit's note.
4. **Staged note** `logs/inbox/<id>.md`:

| Inbox field | From |
| --- | --- |
| `type` | `uiux-job` |
| `job_id` | the board's numeric id (7 digits so far), quoted |
| `url` | `https://uiuxjobsboard.com/job/<id>-<slug>`, the full path |
| `title` | JSON-LD `title` |
| `company` | JSON-LD `hiringOrganization.name` |
| `location` | the header's LOCATION parts joined with ', ' ('Remote, United States') |
| `work_type` | `remote` when the location starts with 'Remote'; `hybrid` when it starts with 'Hybrid'; otherwise empty |
| `posted` | JSON-LD `datePosted`, date part |
| `retrieved_at` | fetch time, from the system clock |
| `source_search` | `uiux-<name>` (the prefix marks the source, so no new field) |
| body | the text of `div.job-description`, as the page renders it |

5. **Fold** with `fold_jobs_into_tasks.py`, unchanged.

**The body is the description's own text, converted mechanically.** Entities are decoded, `&nbsp;` becomes a space, and tags are removed. Headings, paragraphs and `<br>` become line breaks, with a blank line between blocks. A list item starts with '- ', standing for the bullet the page shows. Link text stays and link targets go. Nothing is added, reordered or reworded, and stray markup in the text (a literal `**`) stays as it is.

**Stop the run** on any list-page response other than 200, any 403, 429 or 5xx, or a Cloudflare page ('Just a moment', 'cf-chl', 'Attention Required', 'Verify you are human'), even one served with 200. Don't retry. **Skip, don't retry,** a job page that returns 404, or that lacks the POSTED label, `div.job-description`, 'Share this job' or a `JobPosting`. Report 'filled' when the page says 'This role has been successfully filled!'. Two job pages in a row missing markers for any other reason stop the run: the layout has probably changed.

### Changes

- The criteria file (`naming.py paths`, row `criteria`): a `uiux:` block with its own `defaults` (`max_age_days: 7`, `max_pages: 1`), `searches` (`uiux-remote-us` for `remote-united-states`, `uiux-remote-anywhere` for `remote-anywhere`) and `selection` (cap 25, `fetch_delay_seconds: 5`, `exclude_types: [Internship]`). The other blocks stay as they are.
- `applicant/criteria/README.md`: the URL mapping.
- `pipeline/scripts/sources/uiux_board.py`: new. Standard library plus PyYAML (which the fold already needs). Dry run unless `--write`; writes only to `logs/searches/` and `logs/inbox/`. A `check <file.html>…` command runs the parser on saved pages with no network; the probe's pages are in `../data/fixtures/uiux-board/`.
- `pipeline/scripts/naming.py`: no change. `JOB_ID` already accepts the numeric id (`\d{6,}`), and LinkedIn's 10-digit ids can't collide with 7-digit ones in practice.
- `pipeline/agents/job-fetcher.md`: a `source: uiux` branch, and product design in the shared target list.
- `pipeline/runbook.md`: a 'UI/UX Jobs Board (fourth source)' section. `../data/README.data.md`: 'UI/UX Jobs Board notes'. Automation `CLAUDE.md`: the board in the hard rules.
- `.mcp.json`: no change.

### Acceptance

- `check` passes on every live job page in the fixtures and refuses the filled one.
- A `uiux-` search record exists, holds no Expired card and nothing older than `max_age_days` apart from marked Featured cards, and `unique_titles.py --write` merges its titles.
- After staging two or three postings, the fold dry run shows only those tasks being created.
- Each new task has its custom fields filled: Job ID the board id, Search `uiux-…`, Posting the board's job URL, Posted from `datePosted`, Location and Work type, and the description as its body.
- **Verbatim check:** one task body against Chrome's `get_page_text` for the same page gives the same word count and the same first and last words, setting aside the '- ' bullet markers.
- `task_links.py` dry run shows no change to existing tasks beyond the known missing-`.docx` set.
- The Haiku and Sonnet fit checks on the same staged notes are recorded side by side.

### UI/UX Jobs Board pilot findings (2026-10-12)

The acceptance list passed. Six plain requests in all (one search, five job pages), 5 seconds apart, under the script's own user agent. No challenge, block or error status.

- **Search:** `uiux-remote-us` kept 10 cards, 4 hours to 7 days old, from one page. Record: `logs/searches/2026-10-12--uiux-remote-us.md`. `unique_titles.py --write` added one new title.
- **Select:** the id and the company-and-title checks flagged none of the 10, but reading by eye found two duplicates. Counterpart Health's Staff UX Designer is the role tracked under Clover Health. 'Linda Werner Associates, UI/UX Designer' is the tracked 'Linda Werner & Associates, Inc - UI/UX Designer \| AI Powered Products'; the Select rule above now folds '&' and allows a title suffix. Sedgwick's role was junior. Russ picked five of the remaining seven.
- **Stage:** the script staged all five (611 to 1,489 words) and printed no description text.
- **Fit check, Haiku against Sonnet** on the same notes, nothing deleted: they agreed on four (Rezilient Health, RapidAI, CodePath, Wander). On Lyntris, Sonnet skipped it because the role requires an active TS/SCI clearance, which `professional-profile.md` doesn't list. Haiku noted the clearance and staged it anyway. That meets the adoption rule in the task (Haiku may stage more, never less), though one disagreement in five is little evidence. Lyntris's note was deleted. **Adopted by Russ, 2026-10-12:** Haiku for `uiux` batches, and 'requires an active security clearance' added to the job-fetcher's shared skip list, so either model now skips such a role from any source.
- **Verbatim check:** for RapidAI, the browser's own rendering of the description (`innerText` of `div.job-description` in Chrome) and the staged body have the same 611 words and the same SHA-256 of the word sequence. The full text never entered the main session.
- **Fold:** dry run and write created only the four tasks, with Company, Posting, Job ID, Location, Work type, Posted, Retrieved and Search filled. The inbox was emptied.
- **`task_links.py` dry run:** 167 existing tasks would change, the known missing-`.docx` set; none of the four new tasks is among them.
- **Ids:** `naming.find_task` finds each new task by its 7-digit id.

## Tasks

[Retrieve postings from Jobgether](../../../goals/Business%20Development/_tasks/retrieve-postings-from-jobgether.md) in Business Development, with two subtasks: set up, then pilot.

[Retrieve postings from Indeed](../../../goals/Business%20Development/_tasks/retrieve-postings-from-indeed.md) in Business Development, with the plan and probe results.

[Retrieve postings from UI/UX Jobs Board](../../../goals/Business%20Development/_tasks/retrieve-postings-from-ui-ux-jobs-board.md) in Business Development, with the plan, the model for each phase, and the probe results.

## Fantastic.jobs (2026-10-21)

**Accepted 2026-10-21, after the pilot.** Rationale and rules: [D23](../../context/decisions.md). Operation: the runbook's Fantastic.jobs section. Fields: [`applicant/criteria/README.md`](../../applicant/criteria/README.md#fantasticjobs).

- **Datasource:** [Fantastic.jobs](https://developer.fantastic.jobs/llms.txt), a paid API over company career pages (58 applicant-tracking systems: Greenhouse, Lever, Workday, Ashby, SmartRecruiters and more) and job boards (LinkedIn, Wellfound, Y Combinator). It returns full descriptions and AI-derived salary, work arrangement and experience fields.
- **Route:** `pipeline/scripts/sources/fantastic_fetch.py`. Only `search --write` calls the API. It saves the raw response, and `stage` builds inbox notes from it offline.
- **Pilot (2026-10-21):** 10 jobs from `active-ats`, all new against the tracker, with 740-1,350-word descriptions; 9 had a salary range. 4 were on target and 1 borderline; the 5 misses were learning experience, instructional design, sales and solution design roles, now excluded in the query. The 24-hour count fell from 21 to 11, and the 31-day count was 483 before tightening. The 5 picks were folded.
- **Plan:** 500 jobs and 100 requests a month, renewing 2026-10-28. Count endpoints cost a request and no job credits.

## Resources

### Candidate datasources: search across companies

These meet the requirement. Endpoints were probed on 2026-10-08 unless marked unverified.

- [USAJOBS Search API](https://developer.usajobs.gov/) — `data.usajobs.gov/api/search`; free self-serve key (401 without one). Strong fit for Russ's federal work.
- [The Muse public API](https://www.themuse.com/developers/api/v2) — `themuse.com/api/public/jobs`; no key; has a "Design and UX" category.
- [Himalayas jobs API](https://himalayas.app/api) — `himalayas.app/jobs/api`; no key; remote only; cursor pagination.
- [Remotive API](https://remotive.com/api/remote-jobs) — no key; `category=design`; asks callers to keep request volume low.
- [Remote OK API](https://remoteok.com/api) — no key; terms require a followed link back to Remote OK.
- [We Work Remotely: design RSS](https://weworkremotely.com/categories/remote-design-jobs.rss) — RSS feed for each category.
- [Dribbble Jobs RSS](https://dribbble.com/jobs.rss) — RSS; design roles.
- [Jobicy API](https://jobi.cy/apidocs) — no key; credit to Jobicy required.
- [Working Nomads API](https://www.workingnomads.com/api/exposed_jobs/) — no key; mostly engineering.
- [HN Who is Hiring (Algolia API)](https://hn.algolia.com/api) — no key; monthly thread; mostly engineering.
- [Arbeitnow API](https://www.arbeitnow.com/api/job-board-api) — no key; mostly Europe.
- [Adzuna API](https://developer.adzuna.com/) — free key; pulls from many boards (unverified).

### Datasources for one company at a time

These do not meet the requirement alone; useful only with a watchlist of target companies.

- [SmartRecruiters Posting API](https://developers.smartrecruiters.com/docs/posting-api) — `api.smartrecruiters.com/v1/companies/{id}/postings`; no key.
- [Rippling ATS job board](https://api.rippling.com/platform/api/ats/v1/board/rippling/jobs) — `/board/{slug}/jobs`; no key.
- [Workable jobs endpoint](https://apply.workable.com/) — `apply.workable.com/api/v3/accounts/{sub}/jobs` (unverified).
- [Recruitee offers endpoint](https://docs.recruitee.com/reference/offers) — `{company}.recruitee.com/api/offers/` (unverified).

### Not usable

- [jobspipe: Indeed API guide](https://jobspipe.dev/blog/indeed-api-guide) — Indeed shut down its Publisher API in 2023; current APIs are for employers only. Its [MCP connector](https://docs.indeed.com/mcp) (beta, 2026) is for job seekers but has no stable id; see [Connector probe](#connector-probe).
- [Monster partner: Job Search](https://partner.monster.com/job-search) — partner credentials only, no self-serve signup.
- [jobspipe: Monster job posting API](https://jobspipe.dev/blog/monster-job-posting-api.md)

### Paid services that collect jobs from many sources

- [jobspipe](https://jobspipe.dev/) — includes an MCP server.
- [Fantastic.jobs](https://fantastic.jobs/)
- [TheirStack](https://theirstack.com/)
- [SerpApi Google Jobs](https://serpapi.com/google-jobs-api)