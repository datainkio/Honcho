# Handoff: job-retrieval run, 2026-10-31

For the next session (or Russ) picking up this run. State is on disk; nothing here needs the old conversation.

## Where the run stands

Stopped at **Matching approved** (D22) for ten postings. Russ reviews each `match-report.md` and checks the task's Matching approved box. Never check it for him.

| Done | Not done |
|---|---|
| Search: Jobgether, UI/UX Jobs Board, LinkedIn | LinkedIn slice 2 (skipped by Russ) |
| Stage and fold: 23 tasks in `tracking/DEFAULT/_tasks/` | Jobgether batches 3-4 and most of batch 2 (skipped by Russ) |
| Match reports for 10 postings in `output/<task name>/` | Match reports for the other 13 tasks |
| | Interest briefs (no template on disk, see below) |
| | Render, cover letters, `charset.py` (after approval) |

The 10 reports: Atlassian, CaptivateIQ, Clover Health, Counterpart Health, Dandy, Grand Circle, HighLevel (AI Workflows), Park National Bank, SupplyHouse.com, WRS Health. Each report ends with a Flags section. Read those first:

- **Clover Health and Counterpart Health** are the same job text (Counterpart Health, a Clover subsidiary). Apply once.
- **Park National Bank** requires living in its Ohio-area footprint. **SupplyHouse.com** is remote only for residents of 16 listed states (Maryland is not one) with six trips a year to Melville, NY.
- **Dandy** is a graphic-design and brand-marketing management role. Weak fit.
- **CaptivateIQ, HighLevel, Clover/Counterpart** ask for 3+ or 5+ years managing people. Russ's titled management is about 2 years 8 months (profile §5). Don't claim more.
- **WRS Health** is the best fit; its type reads "Full-time | Independent Contractor".

Most reports are under the 25-35 term target (15 to 25 present). Each records the shortfall in its Gaps.

## What was fixed this session (all uncommitted)

- **Jobgether server:** enabled in `.claude/settings.local.json` (`enabledMcpjsonServers: ["jobgether"]`). The scripts call its API over HTTP, so it isn't strictly needed.
- **Tracking:** the profile's `tracking` is now a project folder path (`./tracking/DEFAULT`). `naming.PROJECT_NOTE` is `<folder>/<folder name>.md`. The old Application Tracking project note is now `tracking/DEFAULT/DEFAULT.md` (title still "Application Tracking"). The bare template is backed up in the session scratchpad.
- **Schema and profiles:** `profile-schema.json` requires `tracking`. `honcho.yaml` lost its unused `project_mgmt` key.
- **Profile paths:** `resume`, `cover_letter` and `style` now point at `./input/resumes/`, `./input/cover letters/`, `./input/styles/` (they said `input/templates/…`).
- **Output location:** application packages live in `output/<task name>/`, not `output/applications/`. `naming.APPLICATIONS` is `output/`, and the skill and script docs were updated to match.
- **Copied from the old repo** (`~/Projects/Portfolio/business development/automation/`): `pipeline/specs/keyword-matching-spec.md`, `pipeline/specs/ats-formatting-spec.md`, and `reference/content models/match-report.md` (a stopgap; Russ is redoing the content models).
- **Stale "Application Tracking" paths** in skills, runbook, `_CLAUDE.md` and script docstrings now say `tracking/DEFAULT/_tasks`.

## Open problems

1. **Interest-statement template is missing.** `profiles/*.yaml` points at `./input/templates/interest statements/DEFAULT.md`, which doesn't exist. The copy in git HEAD was at `candidate/templates/interest statements/DEFAULT.md`. Interest briefs and `/interest-statement` need it.
2. **Old tasks are gone.** The tracking note's `taskIds` list about 180 earlier tasks, but `_tasks/` holds only these 23. `select_candidates.py` dedupes against `_tasks/`, so earlier postings can reappear in later runs. Restoring the old `_tasks/` files fixes it.
3. **Paid sources never ran.** `input/criteria/DEFAULT.yaml` has no Fantastic or TheirStack searches, so `--paid` did nothing. Indeed shows `enabled: true` there, but the skill says it was disabled 2026-10-28.
4. **`job-fetcher` agent paths are stale** (`../data/inbox/`, `../../data/README.md`). The real inbox is `logs/inbox/`. I passed explicit paths in each prompt. Fix `pipeline/agents/job-fetcher.md` before the next Chrome batch.
5. **Skill text** in `job-retrieval` and `resume-tailoring` still says `scripts/…` and `config/…`. The real locations are `pipeline/scripts/` and `input/criteria/DEFAULT.yaml`. Run commands from the repo root.

## Resume

- Remaining ids in `logs/runs/2026-10-31-144731-search/shortlist.tsv` (LinkedIn, 211 rows; 22 proposed picks were listed to Russ but not approved) and `logs/runs/2026-10-31-144735-search/shortlist.tsv` (Jobgether and UI/UX).
- Not-yet-reported tasks: `python3 pipeline/scripts/naming.py reports` (the 13 `due` rows).
- After Russ checks Matching approved: `python3 pipeline/scripts/render_resume.py <job_id>` (dry run), then `--write`; then `/cover-letter-writing`, `/interest-statement` (blocked on item 1), `python3 pipeline/scripts/charset.py`.
- Then `/clear`.
