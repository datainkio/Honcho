# Search-criteria mapping

Every field in the criteria file (the one the run profile's `criteria` key names; `naming.py paths`, row `criteria`) corresponds to a parameter of the `search_jobs` MCP tool. Values below are read from the tool source ([`job.py`](https://github.com/stickerdaniel/linkedin-mcp-server/blob/main/linkedin_mcp_server/tools/job.py)), which exposes more filters than the project README table advertises.

## `search_jobs` parameters

| YAML field | Tool param | Type | Allowed values |
| --- | --- | --- | --- |
| `keywords` | `keywords` | string (required) | free text; LinkedIn boolean operators (`OR`, `AND`, quotes) work |
| `location` | `location` | string | free text, e.g. `"Remote"`, `"Baltimore, Maryland"` |
| `max_pages` | `max_pages` | int | `1`–`10` (default `3`) |
| `date_posted` | `date_posted` | enum | `past_hour`, `past_24_hours`, `past_week`, `past_month` |
| `job_type` | `job_type` | list/enum | `full_time`, `part_time`, `contract`, `temporary`, `volunteer`, `internship`, `other` |
| `experience_level` | `experience_level` | list/enum | `internship`, `entry`, `associate`, `mid_senior`, `director`, `executive` |
| `work_type` | `work_type` | list/enum | `on_site`, `remote`, `hybrid` |
| `easy_apply` | `easy_apply` | bool | `true`, `false` (default `false`) |
| `sort_by` | `sort_by` | enum | `date`, `relevance` |

Multi-value fields (`job_type`, `experience_level`, `work_type`) are comma-separated at the tool boundary; express them as YAML lists here and the runbook joins them.

## Returns

`search_jobs` returns a dict with `url`, `sections` (name → raw text), and **`job_ids`** — a list of numeric job-ID strings. Those IDs are the input to `get_job_details`. A LinkedIn job URL like `https://www.linkedin.com/jobs/view/3284153990` carries the same ID (`3284153990`), so job IDs already sitting in the job ledger CSV in the old automation repo's `source/` folder can be fed straight to `get_job_details` without a search.

## `sources:` (D17)

Top-level block of `<source>: { enabled: bool }` for `linkedin`, `jobgether`, `indeed`, `uiux`, `fantastic` and `theirstack`. A missing entry is off, except `jobgether`, which is on by default because its search API needs no login. The other three are opt-in: LinkedIn is read through a logged-in browser, Indeed through Chrome behind Cloudflare, and the UI/UX Jobs Board by plain-HTTP scraping, and each source's terms restrict automated access. `fantastic` and `theirstack` are paid APIs whose terms Russ accepted on 2026-10-21 (D23, D24). `linkedin_fetch.py`, `uiux_board.py`, `fantastic_fetch.py` and `theirstack_fetch.py` refuse a disabled source (`search` and `stage`; `check` still runs). The runbook skips disabled Jobgether and Indeed sections.

## `fit:`

Top-level block the `job-fetcher` applies to every staged description, whatever the source: `targets` (prose), `location` (prose) and `skip` (a list of what a role's core must not be). The fetcher reads it through `python3 pipeline/scripts/naming.py fit`, never the whole file. `/job-setup` writes it from the profile's §13.

## Paths and Python (D17)

Paths default to the repo layout: `naming.py paths` prints each one, resolved from `honcho.yaml` and the active profile. Override with an environment variable: `HONCHO_PROFILE` (the profile), `HONCHO_LOGS` (logs), `HONCHO_APPLICATIONS` (applications), `HONCHO_BACKUPS` for pre-write copies (default: a folder in the system temp dir), and `HONCHO_LEXICON` for the keyword lexicon. Every script needs `pyyaml`. Rendering résumés and cover letters also needs `python-docx`, `reportlab` and `pypdf` in the same Python. `python3 pipeline/scripts/setup_check.py` reports the resolved paths and what is missing.

## Not tool parameters

The `defaults:` block is a project convenience (merged into each search by the runbook). The `selection:` block is advisory policy for *which* returned jobs to fetch in full and how fast — it governs the local pipeline, not the LinkedIn query. `exclude_title_terms` drops titles before any fetch, and `batch_size` sets how many jobs each `job-fetcher` subagent handles (runbook Step 2).

## Jobgether `searchJobs`

The `jobgether:` block of the criteria file holds the Jobgether searches (own `defaults`, `searches` and `selection`). Its fields are the `searchJobs` parameters, read from the API's own docs at `jobgether.com/astroapi/ai/jobs/docs`. An invalid value returns a 400 that lists the allowed values. Design: [`../../pipeline/specs/integrated-datasources-spec.md`](../../pipeline/specs/integrated-datasources-spec.md).

| Field | Type | Values used |
| --- | --- | --- |
| `keyword` | string | free text over title, function, skills, and company. No boolean operators, so use one search per phrase. |
| `locations` | list | `united-states`, `anywhere` |
| `remoteType` | enum | `full-remote` (others: `remote-first`, `hybrid`) |
| `experience` | list | `senior-5-10-years`, `expert-10-years` |
| `contractType` | list | `full-time`, `freelance` |
| `sort` | enum | `date` (or `relevance`) |
| `limit` | int | `25` (the maximum) |
| `page` | int | 1–10 |

`max_age_days` (in `defaults:`, 3) is not an API parameter: `pipeline/scripts/sources/jobgether_fetch.py` drops postings older than that and stops paging once a page reaches them (results are sorted by date).

Its `selection:` block works like the LinkedIn one, but `fetch_delay_seconds` is 2, Jobgether's `Crawl-delay`.

## Indeed

The Indeed block has no MCP tool. Each search is an indeed.com URL opened in Russ's browser through Claude in Chrome, and the runbook's Indeed section runs it.

Search URL template:

`https://www.indeed.com/jobs?q=<keywords>&l=<location>&fromage=<fromage>&sort=<sort>`

| Config field | URL parameter | Values |
| --- | --- | --- |
| `keywords` | `q` | free text, one phrase per search |
| `location` | `l` | `Remote` |
| `fromage` | `fromage` | `1`, `3`, `7` or `14` (days since posted) |
| `sort` | `sort` | `date` or `relevance` |
| `max_pages` | the pager below the results | `1`: with `fromage` 14 or less, no pager appears. The paging parameter is unconfirmed; confirm it before raising this |
| `name` | none | becomes `source_search` (`ind-<name>`) |

Notes:

- Results are read from visible cards only. Each results page hides one decoy card with a fake key; never open it.
- Cards give the `jk` key, title, company and location, but no posted date. The posted date comes from the listing page.
- Indeed's own MCP connector is not used. See the [Connector probe](../../pipeline/specs/integrated-datasources-spec.md#connector-probe) in the spec.

## UI/UX Jobs Board

The UI/UX Jobs Board block has no MCP tool. `pipeline/scripts/sources/uiux_board.py` reads the board over plain HTTP. The design is in the spec's [UI/UX Jobs Board section](../../pipeline/specs/integrated-datasources-spec.md#uiux-jobs-board-2026-10-12).

Search URL template:

`https://uiuxjobsboard.com/design-jobs/<slug>?page=<n>`

| Config field | What it does |
| --- | --- |
| `slug` | The path segment after `/design-jobs/`. Location pages only: `remote-united-states` or `remote-anywhere`. An unknown slug returns a page with no cards, which the script treats as an error |
| `max_age_days` | Not a URL parameter. The script stops reading at the first card that isn't Featured and is Expired or older than this. Cards show an age ('3h', '2d', '1mo'), not a date |
| `max_pages` | The upper bound for `?page=` |
| `fetch_delay_seconds` | Seconds between requests, list and job pages alike. The script enforces it |
| `exclude_types` | Card type labels (Full Time, Contract, Internship) skipped at selection |
| `name` | Becomes `source_search` on staged notes, and the search record's file name `YYYY-MM-DD--<name>.md` |

The board has no search API, RSS or feed, so there are no query parameters beyond the page number.

## Fantastic.jobs

`pipeline/scripts/sources/fantastic_fetch.py` reads the paid Fantastic.jobs API (D23). Every key of a search, merged over `fantastic: defaults:`, is sent as a query parameter, except the script's own `name`, `endpoint` and `max_age_hours`. Lists are comma-joined. The full parameter list is in the OpenAPI spec, `https://data.fantastic.jobs/openapi`.

`GET https://data.fantastic.jobs/v1/<active-ats | active-jb>` with `Authorization: Bearer $FANTASTIC_JOBS_API_KEY`

| Config field | What it does |
| --- | --- |
| `endpoint` | Script only. `ats` (company career pages) or `jb` (LinkedIn, Wellfound, Y Combinator) |
| `time_frame` | `1h`, `24h`, `7d` or `6m`. Counts listings still active in the window, not post age |
| `limit` | Jobs per call (1-1000). Every job returned costs a credit, so this caps the cost of a call |
| `max_age_hours` | Script only. Drops jobs posted longer ago than this. The script also sends `date_posted_gte` as the start of the cutoff's day, so older jobs aren't billed |
| `location` | Full names only ('United States', not 'US') |
| `ai_work_arrangement` | `Remote Solely`, `Remote OK`, `Hybrid`, `On-site` (AI-derived) |
| `ai_experience_level` | `0-2`, `2-5`, `5-10`, `10+` (AI-derived) |
| `title_advanced` | Boolean title query: `&` `\|` `!` `<->` `( )` and `:*` for a prefix. `!` binds tightest, then `&`, then `\|`, so group an OR before adding exclusions |
| `description_format` | `text`. Without it, the API returns no description |
| `name` | Becomes `source_search` on staged notes, and the search record's file name `YYYY-MM-DD--<name>.md` |

## TheirStack

`pipeline/scripts/sources/theirstack_fetch.py` reads the paid TheirStack API (D24). Every key of a search, merged over `theirstack: defaults:`, is sent as-is in the JSON request body, except the script's own `name`. The full parameter list is in the OpenAPI spec, `https://api.theirstack.com/openapi.json`.

`POST https://api.theirstack.com/v1/jobs/search` with `Authorization: Bearer $THEIRSTACK_API_KEY`

| Config field | What it does |
| --- | --- |
| `limit` | Jobs per call. Every job returned costs a credit, so this caps the cost of a call |
| `posted_at_max_age_days` | `0` is today only, `1` today and yesterday. The API requires a `posted_at_*` filter, and the script refuses a search without one |
| `job_country_code_or` | ISO two-letter codes (`US`) |
| `workplace_types_or` | `on_site`, `hybrid`, `remote` |
| `job_seniority_or` | `c_level`, `staff`, `senior`, `mid_level`, `junior` |
| `job_title_pattern_or` / `_not` | Case-insensitive regexes. A title matching any `_or` pattern is kept unless it matches a `_not` pattern |
| `name` | Becomes `source_search` on staged notes, and the search record's file name `YYYY-MM-DD--<name>.md` |

## Render style

The render style (`naming.py paths`, row `render style`, under `applicant/styles/`) holds the formatting of every rendered résumé and cover letter: one `font`, then a `docx` block (read by `pipeline/scripts/package/render_docx.py`, which renders résumés and cover letters) and a `pdf` block (read by `pipeline/scripts/package/render_pdf.py`). It isn't part of the search criteria. The rules its values must keep are in [`../../pipeline/specs/ats-formatting-spec.md`](../../pipeline/specs/ats-formatting-spec.md). A change applies to the next render only; frozen postings (D13) are never re-rendered.

<!-- readme-index:start -->
## Index

- [russ.yaml](russ.yaml)
<!-- readme-index:end -->
