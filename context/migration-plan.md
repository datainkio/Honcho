---
title: "Migration plan: automation → Honcho"
description: "Retires the Portfolio vault automation and finishes Honcho, a standalone project with its own structure. Code and docs are ported; no data is copied in; dotpm stays as Honcho's tracker."
type: plan
status: in-progress
created: 2026-10-29
updated: 2026-11-02
---

# Migration plan: automation → Honcho

The goal is to deprecate the automation in the Portfolio vault (`Portfolio/business development/automation` with its sibling `data/`, `source/` and `goals/Application Tracking/`) and to finish Honcho. Honcho is a separate project, not a new home for the old data. It has its own structure (run profiles, `applicant/`, `applications/`, `logs/`), expanded functionality and a better DX. The old repo is read only as a source of code and docs to port. It keeps working off its own files until the cutover.

## Decisions

Recorded in [`decisions.md`](decisions.md) as D31 to D33.

1. **Personal data lives inside Honcho, gitignored** (Russ, 2026-10-29). The repo ships generic `DEFAULT` inputs. An install's own profile, inputs, packages, tasks and run records stay out of git (D33).
2. **dotpm stays** (Russ, 2026-11-02; reverses the 10-29 decision to drop it). Postings are tracked in Honcho's own dotpm project: `applications/DEFAULT.md` with `applications/_tasks/` (D31).
3. **History:** `decisions.md` comes over to `context/` (Honcho's decisions start at D31, since the old repo reached D30). The specs go to `pipeline/specs/`. Handoffs and closed plans stay in the old repo as its archive.
4. **Run records** go to `logs/`: `searches/`, `inbox/`, `runs/`, `fit/`, `fixtures/`, `lexicon.json`.
5. **No data is copied in** (Russ, 2026-11-02). Honcho starts from its own runs. Cost: Select dedupes only against Honcho's tasks, so a posting tracked only in the old project can come back (D31).
6. **One path layer** (D32). `naming.py` resolves every path from `honcho.yaml` and the active profile. Scripts import the paths, and skills and the job-fetcher name inputs by role plus their `naming.py paths` label.

## Layout

| What | Honcho | Git |
| --- | --- | --- |
| Run profile | `profiles/<name>.md`, named by `honcho.yaml` (`HONCHO_PROFILE` overrides) | `DEFAULT.md`, `README.md` |
| Dossier, truth rules, criteria, résumé and letter templates, questions, render style | `applicant/<kind>/<file the profile names>` | `DEFAULT.*`, `README.md` |
| Application packages | `applications/<Company> - <Job title>/` | no |
| Tracking (dotpm) | `applications/DEFAULT.md`, `applications/_tasks/` | project note yes (see open questions), tasks no |
| Run records | `logs/` | no |
| Code | `pipeline/scripts/`, `pipeline/skills/`, `pipeline/agents/`, `pipeline/specs/`, `pipeline/runbook.md` | yes |
| Claude wiring | `.claude/skills/*` and `.claude/agents/*` link into `pipeline/`; `.mcp.json`, `.env.example`, `CLAUDE.md` | yes |
| History | `context/decisions.md`, `context/handoffs/` | yes |
| Reference | `reference/` (content models, journeys, personas, datasources) | yes |

Ported from the old repo (code and docs only): `scripts/`, `skills/`, the job-fetcher agent, `runbook.md`, `context/decisions.md`, six specs, `config/README.md` (now `applicant/criteria/README.md`), `.mcp.json`. `config/search-criteria.yaml` and `config/render-style.yaml` seeded `applicant/criteria/russ.yaml` and `applicant/styles/DEFAULT.yaml`.

## Stages

1. **Path layer.** Done (D32). *Verify:* every script compiles; `naming.py paths` lists every path; `setup_check.py` passes.
2. ~~Copy Russ's data in.~~ Cancelled (decision 5).
3. ~~Drop dotpm.~~ Cancelled (decision 2).
4. **Claude wiring.** Done: skills and the job-fetcher are linked from `.claude/`, `.mcp.json` and `.env.example` are present, and the skills' and agent's paths name Honcho's layout.
5. **History and docs.** Done: `decisions.md` (D31 to D33 added), specs, runbook, criteria README, `applications/README.md`. Unmapped references are listed under open questions.
6. **Cutover.** A full dry retrieval works, with all five sources planned. *Left:* one package render from Honcho, once Russ checks Matching approved on a reviewed match report (`render_resume.py <job_id>` dry run, then `--write`). Then mark the old repo archived and point the Portfolio vault's links at Honcho.

## Open questions

- **The committed project note holds install data.** `applications/DEFAULT.md` is tracked in git (`!applications/DEFAULT.md`), but its `taskIds` list this install's postings. Options: commit an empty project template, or give the install its own gitignored project note (renaming it rewrites every task's project link).
- **References with no Honcho counterpart:** `Priority.md` and `goals/Business Development/…` links in the runbook and `integrated-datasources-spec.md`. Also `context/token-efficiency-review.md`, `context/fit-rubric.md` and `context/package-efficiency-plan.md`, cited by the runbook, specs and script comments. The inbox and search-record schema (`../data/README.data.md`) is not migrated either.
- **Content models:** `reference/content models/` is being redone.
- **Interest statements:** to be retired in favour of question-answers. Its template, `candidate/templates/interest statements/DEFAULT.md`, survives only in `origin/main`.
- **`vocabulary/`** (authored upstream in content strategy): ship it with Honcho or keep it personal.

## Progress

- 2026-10-29: plan written; decisions 1 to 4 recorded.
- 2026-10-29: stage 1 done (uncommitted), then lost when the original scripts were re-copied.
- 2026-11-02: **stage 1 redone against the current layout.** Inputs live in `applicant/<kind>/` and run profiles in `profiles/<name>.md`. Packages and the dotpm project are in `applications/`, run records in `logs/`. `naming.py` resolves all of it from `honcho.yaml` or `HONCHO_PROFILE`. Copied in: `.mcp.json`, `.env`, the criteria and the render style. Added `.gitignore`. Pre-edit scripts are in session scratchpad `839214c6…/scratchpad/scripts-orig/`.
- 2026-11-02: **plan revised (whiteboard).** Honcho is standalone, no data is copied in, and dotpm stays (D31 to D33). `naming.py` gained `fit`. The job-fetcher is linked into `.claude/agents/`. A docs sweep mapped the skills, agent, `CLAUDE.md`, specs and READMEs to Honcho paths and ported `decisions.md`, the runbook, four specs and the criteria README. Russ's résumé template, letter template and truth rules moved to `russ.md`, and the DEFAULTs are generic. `match_packet.py` no longer hardcodes the letter header. `python-docx` and `reportlab` are installed. The folder is reattached to `datainkio/honcho` (`git init`, fetch, mixed reset to `origin/main`; nothing committed). *Verified:* every script compiles. `setup_check.py` exits 0. Plan-only `retrieve.py search --paid` lists all five sources. The fold dry run, `charset.py` (0 forbidden) and `task_links.py` dry run work, and `render_resume.py` refuses an unapproved posting. The letter packet is unchanged except for its template path. Pre-edit copies are in session scratchpad `871673b0…/scratchpad/pre-edit/`.
- 2026-11-02: **scripts reorganized (D34).** `pipeline/scripts/` now has `sources/`, `tracking/` and `package/`, with shared code in `sources/common.py`, `naming.py` and `package/match_report.py`. `apply_fit_scores.py` is deleted. Every documented command path was swept. *Verified:* every script compiles on Python 3.9 and 3.12. Baseline commands give the same output as before at their new paths: setup check, naming, fold, links, charset, Select, titles, the retrieve plans, the renderer dry runs, the letter packet and the paid dry runs. Each source's error paths and its disabled-source refusal return exit 2 offline. Each offline `check` parser accepts synthetic input. LinkedIn, Jobgether and the board were not exercised live. Pre-edit copies are in session scratchpad `365e9a7e…/scratchpad/scripts-orig/`.
- 2026-11-03: **first commit of the migration.** `LICENSE` (MIT) and `.gitattributes` restored from `origin/main`. Held back as install data: `applications/DEFAULT.md` (the open question above) and the 10-31 handoff.
