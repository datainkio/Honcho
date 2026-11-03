# ══════════════════════════════════════════════════════════════════════════════
# Job Search Criteria — DEFAULT
# ══════════════════════════════════════════════════════════════════════════════
# A starting point. Copy it to applicant/criteria/<profile>.yaml, point your run
# profile's `criteria` key at it, and replace the example roles with your own.
# Every field is described in README.md (same folder). This file is plain YAML;
# the .yaml.md name lets Obsidian open it.
#
# As shipped, only Jobgether is on, so a fresh install can search without any
# login, scraping or paid key.
# ══════════════════════════════════════════════════════════════════════════════

# ── Sources ───────────────────────────────────────────────────────────────────
# Which sources a run may use. A source missing here is off, except Jobgether
# (public search API, no login), which is on by default. LinkedIn, Indeed and
# UI/UX Jobs Board are opt-in: each is read through a logged-in or scripted
# route that its terms of service restrict (D17). Turn one on only if you accept
# that risk for your own account. Fantastic.jobs and TheirStack are paid APIs:
# turn one on once you have accepted its terms and put its key in .env. The
# scripts refuse a disabled source, and retrieve.py and the runbook skip it.
sources:
  linkedin: { enabled: false }
  jobgether: { enabled: true }
  indeed: { enabled: false }
  uiux: { enabled: false }
  fantastic: { enabled: false } # paid API (D23)
  theirstack: { enabled: false } # paid API (D24)

# ── Fit check ─────────────────────────────────────────────────────────────────
# What the job-fetcher keeps after reading a description, every source. It reads
# this block through `python3 pipeline/scripts/naming.py fit`. Off while
# `selection: fit_check` is false. Plain prose: `targets` and `location` say
# what fits, `skip` lists what a role's core must not be.
fit:
  targets: >-
    UX and product design (senior, lead) and UX research
  location: remote in the US
  skip:
    - product management
    - software engineering

# ══════════════════════════════════════════════════════════════════════════════
# LinkedIn
# ══════════════════════════════════════════════════════════════════════════════
# pipeline/scripts/sources/linkedin_fetch.py calls `search_jobs` once per entry
# under `searches`. LinkedIn's search page keeps only `keywords` and
# `date_posted`, and reads keywords as a semantic query (no Boolean operators,
# D25), so put the location and work type in the words: 'remote ... in United
# States'.

defaults: # applied to every search unless the search overrides them
  max_pages: 5 # 1–10, 25 rows a page
  easy_apply: false
  # past_hour | past_24_hours | past_week | past_month. Results come in relevance
  # order, so a long window can fill the pages before the freshest jobs appear.
  date_posted: past_24_hours

# Laid over `defaults:` by `linkedin_fetch.py search --incremental`, for a
# second pass on the same day.
incremental:
  max_pages: 1

searches:
  - name: ux-designer
    keywords: "remote senior UX designer in United States"

  - name: ux-researcher
    keywords: "remote UX researcher in United States"

# ── Selection policy ──────────────────────────────────────────────────────────
# Not tool parameters. The scripts enforce fetch_delay_seconds, LinkedIn's
# max_fetches_per_run and exclude_title_terms; the session applies the rest when
# it picks which returned jobs to fetch in full. Select always skips jobs that
# already have a task or are staged.
selection:
  max_fetches_per_run: 50
  fetch_delay_seconds: 4 # human-paced spacing before every search_jobs and get_job_details call
  batch_size: 10 # jobs per job-fetcher batch, Chrome sources only (Jobgether, Indeed); batches run one after another
  fit_check: false # true: the job-fetcher applies the `fit:` block to every staged description
  # Titles containing any of these (case-insensitive) are dropped before
  # fetching. Add terms as you reject postings; when a title is ambiguous, fetch it.
  exclude_title_terms:
    - product manager

# ══════════════════════════════════════════════════════════════════════════════
# Jobgether
# ══════════════════════════════════════════════════════════════════════════════
# Searched by pipeline/scripts/sources/jobgether_fetch.py (retrieve.py runs it).
# Fields map 1:1 to the `searchJobs` API; see README.md. `keyword` takes no
# boolean operators, so each phrase is its own search. Names carry the `jg-`
# prefix because the name becomes the staged note's `source_search`.
jobgether:
  defaults:
    locations: [united-states, anywhere] # "anywhere" roles are kept only because remoteType limits to full remote
    remoteType: full-remote
    experience: [senior-5-10-years, expert-10-years]
    contractType: [full-time, freelance]
    sort: date # relevance | date
    limit: 25 # per page; the API maximum
    max_pages: 2 # 1–10
    max_age_days: 3 # not an API parameter: the script drops older postings and stops paging

  searches:
    - { name: jg-ux-designer, keyword: "UX designer" }
    - { name: jg-ux-researcher, keyword: "UX researcher" }

  selection:
    max_fetches_per_run: 25
    fetch_delay_seconds: 2 # Jobgether's robots.txt Crawl-delay; also spaces listing-page fetches
    # batch_size and exclude_title_terms: shared with the selection block above

# ══════════════════════════════════════════════════════════════════════════════
# Indeed
# ══════════════════════════════════════════════════════════════════════════════
# Run by hand via the runbook's Indeed section, in your own Chrome. Fields become
# indeed.com search-URL parameters (see README.md). Names carry the `ind-` prefix.
# Read only visible result cards: each results page hides a decoy card.
indeed:
  defaults:
    location: Remote
    fromage: 7 # days since posted: 1 | 3 | 7 | 14
    sort: date # date | relevance
    max_pages: 1

  searches:
    - { name: ind-ux-designer, keywords: "UX designer" }
    - { name: ind-ux-researcher, keywords: "UX researcher" }

  selection:
    max_fetches_per_run: 25
    fetch_delay_seconds: 8 # between every Indeed page load, search and listing alike

# ══════════════════════════════════════════════════════════════════════════════
# UI/UX Jobs Board
# ══════════════════════════════════════════════════════════════════════════════
# Read by pipeline/scripts/sources/uiux_board.py over plain HTTP (retrieve.py
# runs it). Each search is a location page,
# https://uiuxjobsboard.com/design-jobs/<slug> (see README.md). Names carry the
# `uiux-` prefix. Role pages can't be filtered by location, so titles are
# filtered at selection.
uiux:
  defaults:
    max_age_days: 7 # stop at the first non-Featured card older than this, or Expired
    max_pages: 1 # 50 cards a page

  searches:
    - { name: uiux-remote-us, slug: remote-united-states }
    - { name: uiux-remote-anywhere, slug: remote-anywhere }

  selection:
    max_fetches_per_run: 25
    fetch_delay_seconds: 5 # between every request; the script enforces it
    exclude_types: [Internship] # the card's type label

# ══════════════════════════════════════════════════════════════════════════════
# Fantastic.jobs (paid API, D23)
# ══════════════════════════════════════════════════════════════════════════════
# pipeline/scripts/sources/fantastic_fetch.py. Billed per job returned, so
# `limit` caps the cost of every call. Every key except `name`, `endpoint` and
# `max_age_hours` is sent as a query parameter (lists comma-joined); see
# README.md. `title_advanced` is a Boolean query: & | ! <-> ( ) and :* prefix.
# Names carry the `fj-` prefix.
fantastic:
  defaults:
    endpoint: ats # ats (company career pages) | jb (job boards)
    time_frame: 24h # 1h | 24h | 7d | 6m
    limit: 25
    max_age_hours: 24 # the script's own cutoff on date_posted
    location: United States
    ai_work_arrangement: [Remote Solely, Remote OK]
    ai_experience_level: [5-10, 10+]
    description_format: text

  searches:
    - name: fj-ux-remote-us
      title_advanced: "(ux | product) & design:* | ux & research:*"

# ══════════════════════════════════════════════════════════════════════════════
# TheirStack (paid API, D24)
# ══════════════════════════════════════════════════════════════════════════════
# pipeline/scripts/sources/theirstack_fetch.py. One credit per job returned, so
# `limit` caps the cost of every call. Every key except `name` is sent as-is in
# the JSON request body; see README.md. A posted_at_* filter is required. Title
# patterns are case-insensitive regexes. Names carry the `ts-` prefix.
theirstack:
  defaults:
    limit: 25
    posted_at_max_age_days: 1 # today and yesterday
    job_country_code_or: [US]
    workplace_types_or: [remote]
    job_seniority_or: [senior, staff]

  searches:
    - name: ts-ux-remote-us
      job_title_pattern_or:
        - '\b(ux|product)\b.*\bdesign'
        - '\bux\b.*\bresearch'
