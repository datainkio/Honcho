# job-retrieval

`/job-retrieval` runs one manual retrieval session: it searches the enabled job sources, picks the likely fits, stages their descriptions, folds them into tracking tasks, and starts the package wave. The operator approves each slice before anything is fetched. Nothing here is scheduled or unattended. The operational authority is [SKILL.md](SKILL.md). These diagrams explain it.

## Who is responsible for what

One of the key values of this project is optimal token efficiency. Towards that end, responsibilities are distributed across models depending upon the particular needs of the task. Retrieval is fairly low cost given that much of it is handled by Python scripts. LLMs come into play when interpreting results, authoring files, and working with MCP servers.

| Tag | Who                   | Used for                                                                                     |
| --- | --------------------- | -------------------------------------------------------------------------------------------- |
| 🧑  | Operator (hooman)     | Starting the run, approving each slice                                                       |
| 🧠  | Sonnet (main session) | Source checks, choosing fits, reading dry runs, the package wave, the handoff                |
| ⚡  | Haiku (`job-fetcher`) | Opening Jobgether listings (and Indeed, if re-enabled) in Chrome and staging the description |
| ⚙️  | Python scripts        | Searching, de-duplicating, staging LinkedIn, UI/UX and the paid APIs, folding. No model      |

The runbook reserves the more capable models for résumé bases, cover letters, specs and decisions.

## The flow

Five steps, one confirmation per slice. The confirmation sits between Select and Fetch, because a full description costs about 3.5k tokens. A streamed run (D26, D30) has two slices: the fast sources first, then LinkedIn when its paced search finishes. Each slice goes through Select, approval, staging, the fold and its own package wave. That is at most three confirmations a run, the third only if Indeed is turned back on.

Each step is tagged with what does the work. Scripts run no model, so they cost no tokens beyond the one-line results the main session reads. Sonnet runs the session and makes the judgment calls. Haiku only reads Chrome pages, so full descriptions stay out of Sonnet's context.

```mermaid
flowchart TD
  start(["🧑 operator starts /job-retrieval"]) --> enabled{"🧠 Source enabled in the<br/>profile's criteria file?<br/>(naming.py paths: criteria)"}
  enabled -- no --> skip["Skip that source"]
  enabled -- yes --> search

  subgraph S1["1 · Search"]
    search["⚙️ retrieve.py search<br/>LinkedIn in the background;<br/>Jobgether, UI/UX, paid APIs (--paid) in the foreground"] --> record[("Search records<br/>logs/searches/")]
    record --> titles["⚙️ unique_titles.py<br/>merge new titles"]
  end

  titles --> select

  subgraph S2["2 · Select"]
    select["⚙️ select_candidates.py<br/>over the day's records, every source"] --> shortlist[("Shortlist, grouped by source<br/>logs/runs/&lt;stamp&gt;-search/shortlist.tsv")]
    shortlist --> eye["🧠 Check by eye, then choose fits<br/>against the profile"]
  end

  eye --> confirm{"🧑 operator approves<br/>this slice?"}
  confirm -- no --> stop(["End run"])
  confirm -- yes --> fetch

  subgraph S3["3 · Fetch and stage"]
    fetch["⚙️ retrieve.py stage: LinkedIn, UI/UX,<br/>Fantastic, TheirStack<br/>⚡ Jobgether: job-fetcher agent"] --> inbox[("Inbox<br/>logs/inbox/&lt;job_id&gt;.md")]
  end

  inbox --> fold

  subgraph S4["4 · Fold"]
    fold["⚙️ fold_jobs_into_tasks.py<br/>🧠 Sonnet reads the dry run, then applies"] --> task[("Tracking task<br/>applications/_tasks/<br/>Company - Job title.md")]
  end

  task --> wave

  subgraph S5["5 · Package wave"]
    wave["🧠 Match reports for the due rows<br/>(naming.py reports), then stop<br/>at Matching approved"]
  end

  wave -- "LinkedIn slice finishes" --> select
  wave --> done(["🧠 Handoff, then /clear"])

  classDef sonnet fill:#e8f0fe,stroke:#4a6fa5,color:#111
  classDef haiku fill:#fff4d6,stroke:#b8860b,color:#111
  classDef script fill:#eeeeee,stroke:#777,color:#111
  classDef human fill:#e6f4ea,stroke:#3c8d5a,color:#111
  class enabled,eye,wave,done sonnet
  class search,titles,select script
  class confirm,start human
```

## Where each source goes

The sources differ in how they search and how they fetch. Descriptions never enter the main session. Scripts write them straight to the inbox, and the `job-fetcher` agent (Haiku) reads the Chrome sources. `retrieve.py` runs every script source's search, then every stage, as one command each.

```mermaid
flowchart LR
  subgraph Sources
    li["LinkedIn<br/><i>opt-in</i>"]
    ux["UI/UX Jobs Board<br/><i>opt-in</i>"]
    jg["Jobgether<br/><i>on by default</i>"]
    fj["Fantastic.jobs<br/><i>paid, opt-in</i>"]
    ts["TheirStack<br/><i>paid, opt-in</i>"]
    ind["Indeed<br/><i>disabled 2026-10-28</i>"]
  end

  li -- "linkedin_fetch.py search" --> rec[("Search records")]
  ux -- "uiux_board.py search" --> rec
  jg -- "jobgether_fetch.py search<br/>searchJobs over HTTP, no login" --> rec
  fj -- "fantastic_fetch.py search<br/>saves the full response" --> rec
  ts -- "theirstack_fetch.py search<br/>saves the full response" --> rec
  ind -. "operator's Chrome" .-> rec

  rec --> sel["select_candidates.py"]
  sel --> ok{"operator approves"}

  ok --> li2["linkedin_fetch.py stage<br/>own process"]
  ok --> ux2["uiux_board.py stage"]
  ok --> paid2["fantastic_fetch.py stage<br/>theirstack_fetch.py stage<br/>from the saved response, no network"]
  ok --> agent["job-fetcher agent<br/>one batch at a time<br/>Chrome"]

  li2 --> inbox[("Inbox")]
  ux2 --> inbox
  paid2 --> inbox
  agent --> inbox
  inbox --> fold["Fold into tasks"]
```

| Source            | Search                       | Fetch                           | Pace                                             |
| ----------------- | ---------------------------- | ------------------------------- | ------------------------------------------------ |
| LinkedIn          | script, logged-in browser    | script, logged-in browser       | enforced delay and fetch cap                     |
| UI/UX Jobs Board  | script, plain HTTP           | script                          | 5 seconds between requests                       |
| Jobgether         | script, search API over HTTP | job-fetcher in Chrome           | 2 seconds between requests                       |
| Fantastic.jobs    | script, paid API             | script, from the saved response | one call per search a day; `limit` caps the cost |
| TheirStack        | script, paid API             | script, from the saved response | one call per search a day; `limit` caps the cost |
| Indeed (disabled) | Chrome                       | job-fetcher in Chrome           | 8 seconds between page loads                     |

## The services

What the run talks to, and which model sits where. Solid lines are calls the run makes. The scripts own all search traffic and every LinkedIn, UI/UX and paid-API read, so the main session never touches those sites directly. Only listing pages that block scripts (Jobgether, and Indeed while enabled) go through Claude in Chrome.

```mermaid
flowchart LR
  operator(["🧑 operator"])

  subgraph Claude["Claude Code session"]
    main["🧠 Main session<br/>Sonnet<br/>/job-retrieval"]
    fetcher["⚡ job-fetcher agent<br/>Haiku"]
  end

  subgraph Local["Local scripts · no model"]
    ret["retrieve.py<br/>search · stage"]
    lis["linkedin_fetch.py"]
    uxs["uiux_board.py"]
    jgs["jobgether_fetch.py"]
    paid["fantastic_fetch.py<br/>theirstack_fetch.py"]
    sel["select_candidates.py<br/>unique_titles.py"]
    fold["fold_jobs_into_tasks.py"]
  end

  subgraph MCP["MCP servers"]
    limcp["linkedin<br/>mcp-server-linkedin"]
    jgmcp["jobgether<br/>jobgether.com/mcp"]
    chrome["Claude in Chrome<br/>operator's browser"]
  end

  subgraph APIs["Paid APIs · keys in .env"]
    fjapi["Fantastic.jobs"]
    tsapi["TheirStack"]
  end

  subgraph Sites["Job sites"]
    li["LinkedIn"]
    ux["UI/UX Jobs Board"]
    jg["Jobgether"]
    ind["Indeed"]
  end

  subgraph Store["Honcho files"]
    cfg[("applicant/criteria/<br/>(profile criteria file)")]
    searches[("logs/searches/")]
    runs[("logs/runs/<br/>shortlist.tsv")]
    inbox[("logs/inbox/")]
    tasks[("applications/<br/>_tasks/")]
  end

  operator <-- "approves each slice" --> main
  main --> ret
  main --> fold
  main -- "batch of ids" --> fetcher
  fetcher -- "one line per job" --> main

  ret --> lis
  ret --> uxs
  ret --> jgs
  ret --> paid
  ret --> sel
  ret -- "dry run" --> fold

  lis --> limcp --> li
  uxs -- "plain HTTP" --> ux
  jgs -- "JSON-RPC over HTTP" --> jgmcp --> jg
  paid --> fjapi
  paid --> tsapi
  fetcher --> chrome
  chrome --> jg
  chrome -.-> ind
  main -. "Indeed search, if re-enabled" .-> chrome

  cfg -.-> ret
  cfg -.-> main
  lis --> searches
  uxs --> searches
  jgs --> searches
  paid --> searches
  sel --> searches
  sel --> runs
  lis --> inbox
  uxs --> inbox
  paid --> inbox
  fetcher --> inbox
  inbox --> fold --> tasks

  classDef sonnet fill:#e8f0fe,stroke:#4a6fa5,color:#111
  classDef haiku fill:#fff4d6,stroke:#b8860b,color:#111
  class main sonnet
  class fetcher haiku
```

Two design choices show up here. Staged descriptions go from script or agent straight to the inbox, so the 3.5k-token bodies never pass through Sonnet. And the job-fetcher shares operator's Chrome, so batches run one at a time. The LinkedIn script drives its own browser profile (`~/.linkedin-mcp/profile/`), so it runs beside the Chrome batches.

## Who does what

```mermaid
sequenceDiagram
  actor operator
  participant Main as Main session (Sonnet)
  participant Scripts as Scripts (no model)
  participant Agent as job-fetcher (Haiku)
  participant Files as logs/ and applications/

  operator->>Main: /job-retrieval
  Main->>Scripts: retrieve.py search --sources linkedin (background)
  Main->>Scripts: retrieve.py search --paid (fast sources)
  Scripts->>Files: write search records and shortlist.tsv
  loop Each slice: fast sources, then LinkedIn
    Scripts-->>Main: shortlist, grouped by source
    Main->>operator: one shortlist for the slice
    operator-->>Main: approve
    par Script sources
      Main->>Scripts: retrieve.py stage
      Scripts->>Files: write inbox notes
    and Chrome sources
      Main->>Agent: one batch of Jobgether jobs
      Agent->>Files: write inbox notes
      Agent-->>Main: one line per job, no description
    end
    Main->>Scripts: fold dry run, then --write --consume
    Scripts->>Files: create or refresh tasks, empty the inbox
    Main->>Main: package wave, stop at Matching approved
  end
  Main-->>operator: handoff
```

## The models

The skill moves one posting through five shapes. Each is a file, and each is derived from the one before it. The task is the only permanent copy of the job description (D5).

```mermaid
erDiagram
  SEARCH_CRITERIA ||--o{ SEARCH_RECORD : "drives"
  SEARCH_RECORD ||--|{ JOB_ID_ROW : "lists"
  JOB_ID_ROW ||--o| SHORTLIST_ROW : "kept by Select"
  SHORTLIST_ROW ||--o| INBOX_NOTE : "approved and staged"
  INBOX_NOTE ||--|| TASK : "folded into, then deleted"
  TASK ||--o| MATCH_REPORT : "downstream"
  MATCH_REPORT ||--o| APPLICATION_PACKAGE : "downstream"

  SEARCH_CRITERIA {
    file path "applicant/criteria/ (the profile's criteria)"
    config fit "check, targets, location, skip"
    config selection "batch_size, exclude_title_terms (every source)"
    config sources "per source: enabled, pacing, defaults, searches"
  }
  SEARCH_RECORD {
    file path "logs/searches/DATE--name.md"
    file raw_response "paid sources: DATE--name.json beside it"
    text search_name
    datetime run_at
    object criteria
    number result_count
    boolean capped "paid sources: the call returned exactly its limit"
  }
  JOB_ID_ROW {
    text job_id
    text title
    text company
    date posted
    text fetched
  }
  SHORTLIST_ROW {
    file path "logs/runs/STAMP-search/shortlist.tsv"
    text source
    text search
    text job_id
    text company
    text title
    text location
  }
  INBOX_NOTE {
    file path "logs/inbox/job_id.md"
    text type "source-job, e.g. jobgether-job"
    text job_id PK
    text url
    text title
    text company
    text location
    text work_type
    datetime retrieved_at
    text source_search
    boolean over100 "LinkedIn only"
    body description "verbatim, transient"
  }
  TASK {
    file path "applications/_tasks/"
    text job_id PK
    text title "Company - Job title"
    select work_type
    select status "hiring stage"
    select priority "critical, or medium when over100 (D27)"
    number fit_score
    body description "verbatim, only copy"
  }
  MATCH_REPORT {
    file path "applications/TASK NAME/match-report.md"
    note scope "next skill: resume-tailoring"
  }
  APPLICATION_PACKAGE {
    file path "applications/TASK NAME/"
    note scope "résumé, cover letter, interest statement"
  }
```

Field definitions: the [job posting content model](../../../reference/content%20models/Job%20Posting.md). The inbox and search-record schemas are still in the old automation repo's `data/README.md` (not yet migrated).

## What can stop a run

A hard stop ends the whole run, Chrome work included. Don't retry.

```mermaid
flowchart TD
  run["Any source step"] --> check{"What happened?"}
  check -- "Automation warning, login,<br/>captcha or security check" --> hard["Hard stop"]
  check -- "Cloudflare check,<br/>sign-in wall, unusual traffic" --> hard
  check -- "Script exits 1, or retrieve.py<br/>prints [source] STOPPED" --> hard
  check -- "Paid API: 401, 402, 403,<br/>429 or 5xx" --> hard
  check -- "Script exits 2<br/>usage or config error" --> fix["Fix the config, then rerun"]
  check -- "Empty job_ids<br/>(not Jobgether)" --> loosen["Loosen filters:<br/>wider date, more types, more pages"]
  check -- "Paid call returns exactly<br/>its limit: WARNING, capped" --> raise["Raise limit before<br/>the next day's run"]
  check -- "Offer not found<br/>on a listing page" --> skipjob["Skip that job"]
  check -- "No problem" --> next["Continue"]
  hard --> report["Report the last line to operator.<br/>Close LinkedIn session if used."]
```

<!-- readme-index:start -->

## Index

- [references/](references/README.md)
- [SKILL.md](SKILL.md)
<!-- readme-index:end -->
