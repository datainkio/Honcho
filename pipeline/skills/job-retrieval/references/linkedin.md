# LinkedIn (opt-in)

Load this only when `sources: linkedin: enabled` is true and the operator wants a LinkedIn run. It reads the operator's real logged-in browser, which LinkedIn's User Agreement forbids automating, and the server has no rate limiting. Keep it human-paced.

## Preconditions

1. `uvx mcp-server-linkedin@latest --status` reports a valid session. If not, the operator runs `uvx mcp-server-linkedin@latest --login` themselves (it opens a real browser; they solve any captcha or 2FA).
2. Only one active LinkedIn session. `pipeline/scripts/sources/linkedin_fetch.py` starts its own server, so if this session has called any `mcp__linkedin__*` tool, call `mcp__linkedin__close_session` first.
3. Never use `send_message` or `connect_with_person` without an explicit request.

## Search

Never call `search_jobs` in the session (D16). The script calls it, 4 seconds apart, merging each search with `defaults:`:

```bash
python3 pipeline/scripts/sources/linkedin_fetch.py search --all --write --quiet     # or name searches instead of --all
python3 pipeline/scripts/tracking/unique_titles.py --write
```

It writes `logs/searches/YYYY-MM-DD--<search-name>.md` with `type: linkedin-search-run`. For a second pass on the same day add `--incremental`: it lays the config's `incremental:` block (last 24 hours, 1 page) over each search and names the records `…-incremental.md`. `--quiet` prints a count per search: read the shortlist in Step 2, not the results. The field mapping is in `applicant/criteria/README.md`.

## Fetch and stage

Run it yourself, once for the whole selection, in the background (Step 3 of the skill, D21):

```bash
python3 pipeline/scripts/sources/linkedin_fetch.py stage --write <source_search>=<job_id> …
```

It calls `get_job_details` 4 seconds apart and stages `logs/inbox/<job_id>.md`: frontmatter plus the verbatim description. It prints one line per posting and no description text. It enforces `selection.max_fetches_per_run` and `fetch_delay_seconds` itself. `--search <name> <job_id>…` still works for ids from one search.

## Hard stop

If a script exits 1, or LinkedIn shows an automation warning, a login page, a captcha or a security check, stop the run. Close this session's LinkedIn tools first (`mcp__linkedin__close_session`) if any were used. Don't retry.

| Symptom | Action |
|---|---|
| 'setup/authentication in progress' | Wait for Chromium prep, or `--login`, then retry once |
| Session expired | Re-run `--login` |
