# scripts

The mechanical work of a run: searching, pacing, staging, folding, packets and rendering. Run everything from the repo root as `python3 pipeline/scripts/<folder>/<script>.py`. Every script is a dry run unless it takes `--write`. Layout and rationale: D34 in [`context/decisions.md`](../../context/decisions.md).

## Root

The path layer and the commands that span the folders.

- [naming.py](naming.py): every path, resolved from `honcho.yaml` and the run profile (D32); task names, field ids, the frozen and Prospect gates; the shared frontmatter reader (`split`) and YAML quoting (`q`). `paths | ids | fit | reports | interest`.
- [retrieve.py](retrieve.py): one command per retrieval step. `search` runs every enabled source, then Select; `stage` sends approved picks to each source.
- [setup_check.py](setup_check.py): install readiness.
- [measure_sessions.py](measure_sessions.py): tokens, cost and time per Claude Code session. Standard library only.

## sources/

One script per job board, each with `search`, `stage` and an offline `check`. They share [common.py](sources/common.py): exit codes (1 is a hard stop, 2 is bad input), each source's `sources: <source>:` block with its opt-in (D17, D35), guarded writes and API keys. Pacing, parsing and hard stops stay in each script.

- [linkedin_fetch.py](sources/linkedin_fetch.py): the linkedin MCP server over stdio (D16)
- [jobgether_fetch.py](sources/jobgether_fetch.py): Jobgether search over HTTP; listing pages are read in Chrome by the job-fetcher (D26)
- [uiux_board.py](sources/uiux_board.py): UI/UX Jobs Board over plain HTTP (D15)
- [fantastic_fetch.py](sources/fantastic_fetch.py): Fantastic.jobs, paid (D23)
- [theirstack_fetch.py](sources/theirstack_fetch.py): TheirStack, paid (D24)

## tracking/

Between the search records and the dotpm tasks.

- [select_candidates.py](tracking/select_candidates.py): the Select rules for every source
- [unique_titles.py](tracking/unique_titles.py): the titles index
- [fold_jobs_into_tasks.py](tracking/fold_jobs_into_tasks.py): inbox notes into tasks; also `set_values`, the one-field task edit the renderers use
- [task_links.py](tracking/task_links.py): each task's links block

## package/

A posting's application package.

- [match_packet.py](package/match_packet.py): the two files an agent reads per batch (D28)
- [keyword_lexicon.py](package/keyword_lexicon.py): repeat keyword verdicts, as hints (D28)
- [render_resume.py](package/render_resume.py), [render_cover_letter.py](package/render_cover_letter.py): render and link, behind the approval and frozen gates (D13, D22)
- [charset.py](package/charset.py): the form-safe character lint (D9)
- Libraries, not commands: [match_report.py](package/match_report.py) (match-report tables), [render_docx.py](package/render_docx.py), [render_pdf.py](package/render_pdf.py)

## Imports

A script in a folder puts `pipeline/scripts` on `sys.path` and imports `naming` and siblings by package (`from package.match_report import table`). Nothing needs installing, and each script still runs directly.
