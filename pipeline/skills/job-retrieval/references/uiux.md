# UI/UX Jobs Board (opt-in)

Load this only when `sources: uiux: enabled` is true and the operator wants a board run. uiuxjobsboard.com is a design-only board, read over plain HTTP by `pipeline/scripts/sources/uiux_board.py`, with no browser and no sign-in. The board's terms restrict automated access. The script waits 5 seconds between requests, list and job pages alike. **Never fetch the site any other way** (WebFetch, curl, a browser).

## Search

For each entry under `uiux: searches:` in the criteria file (merged with `uiux: defaults:`):

```bash
python3 pipeline/scripts/sources/uiux_board.py search <name> --write
python3 pipeline/scripts/tracking/unique_titles.py --write
```

It saves `logs/searches/YYYY-MM-DD--uiux-<name>.md` with `type: uiux-search-run`. Zero cards on page 1 is an error, never 'nothing new'.

## Select

As Step 2 of the skill. The script also drops `exclude_types` (Internship) and marks Featured cards `check:` so you can confirm they're in the search's location. Skip companies that are a person's name by eye. Apply the `uiux: selection:` policy. The picks go on the run's one combined shortlist (Step 2 of the skill).

## Fetch and stage

Run it yourself, once for the whole selection, in the background (Step 3 of the skill, D21), with each job's `path` from the search record (a bare id returns 404):

```bash
python3 pipeline/scripts/sources/uiux_board.py stage --write uiux-<name>=<path> …
```

Staged notes are `logs/inbox/<id>.md` with `type: uiux-job` and `source_search: uiux-<name>`. The script does the reading and prints one line per posting. The fit check follows `selection: fit_check` (off for now).

## Hard stop

Stop when the script exits 1: a list-page error, a 403, 429 or 5xx, a Cloudflare page ('Just a moment', 'Attention Required', 'Verify you are human'), or two job pages in a row missing markers (the layout has probably changed). Don't retry. Exit 2 is a usage or config error. If Cloudflare starts challenging plain requests, the fallback is the Chrome route, as for Indeed. That is a spec change, not a workaround in the script.

`python3 pipeline/scripts/sources/uiux_board.py check <file.html>…` tests the parser offline on saved pages.
