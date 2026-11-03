---
name: job-setup
description: Onboard a new user. Builds the professional profile, truth rules and search criteria from the templates, and checks paths, Python modules and the MCP installs. Run once, or again to fix whatever setup_check reports.
disable-model-invocation: true
model: haiku
---

# /job-setup

Sets up this automation for one person, the **candidate**. You talk to the **operator**, who is usually the candidate. Work from the datainkio/honcho repo root. `python3 pipeline/scripts/setup_check.py` is the authority on what's done: it prints one `ok`, `warn` or `missing` line per check.

## Rules

- **Never overwrite** an existing profile, truth-rules file or config without asking first. If the operator agrees, copy the old file to `<file>.bak` beside it first.
- **Never invent a fact about the candidate.** Write only what the operator gives you or what their source material says. Put anything unclear in profile §15 (Open items), not in the body.
- **Ask one topic at a time.** Offer choices with AskUserQuestion where the answer is a pick. Use plain questions where it's free text.
- No credentials in any file.
- Don't edit the operator's shell profile. Print the `export` lines and let them add them.

## Steps

### 1. Check

Run `python3 pipeline/scripts/setup_check.py`. If every line is `ok` (a `python` warning is fine), say so and ask what they want to change. Otherwise work through the steps below for the `missing` and `warn` lines only, in order.

### 2. Paths

Every path resolves from `honcho.yaml` and the active profile in `profiles/`. Run `python3 pipeline/scripts/naming.py paths` to list them. If the operator wants other locations, they edit the profile's `spec` paths, or you give them the `export` lines for `HONCHO_PROFILE` (a different profile for one run), `HONCHO_APPLICATIONS` (the applications folder) or `HONCHO_BACKUPS` (where bulk writes are backed up). Ask them to restart the session after setting any, then re-run step 1.

### 3. Dossier

The dossier is the only source of facts the résumé and cover-letter skills may use for a run. A candidate may have multiple dossiers. The operator specifies which one to use for the pipeline's runs.

1. Ask the operator for source material: a résumé, a LinkedIn profile export, or pasted text. Read what they give you.
2. Fill each `## N.` section from that material, one section at a time. Keep every numbered heading exactly as it is, because the skills read the profile by section number. Set `name:` in the frontmatter to the name exactly as it should appear in file names and sign-offs. Set `updated:` to today.
3. Leave a section's guidance line in place when the material says nothing for it. List such sections in §15 so the operator can fill them later.
4. Ask the operator to review the profile before you continue. It's the most important file in the setup.

### 4. Truth rules

These are the binding honesty rules for every résumé and letter.

1. Go through the seven rule categories one at a time. Ask the question each implies, using the profile for suggestions ('Your profile mentions a $40M program budget. Is that the program's figure or a result of your work?'). Replace the example with the operator's answer.
2. Delete a category that doesn't apply. Renumber the rest.
3. Rewrite the checklist with one short line per remaining rule. Remove every `<…>` placeholder and set `updated:`.

### 5. Search criteria

1. **Sources.** Jobgether stays on. For each opt-in source, read this notice to the operator and ask yes or no, defaulting to no:
   - **LinkedIn:** read through the operator's own logged-in browser. LinkedIn's User Agreement forbids automated access, and the account can be restricted.
   - **Indeed:** read in the operator's Chrome through the Claude in Chrome extension, behind Cloudflare. Indeed's terms restrict automated access.
   - **UI/UX Jobs Board:** plain-HTTP scraping of design-only listings. Its terms restrict automated access.
     Set `sources: <source>: enabled:` for each from the answers.
2. **Targets.** Propose target titles, location and deal-breakers from profile §13. Confirm or edit them with the operator.
3. **Fit.** Write the `fit:` block: `targets` as one sentence of role families, `location` as a short phrase, and `skip` as role kinds the operator never wants.
4. **Searches.** For each enabled source, replace the example search under `sources: <source>: searches:` with one search per target title, using the name prefix the template shows (`jg-`, `ind-`, `uiux-` or none for LinkedIn). For UI/UX Jobs Board, keep the `remote-united-states` slug unless the operator names another location page.
5. Remove every `<…>` placeholder. Check it with `python3 pipeline/scripts/setup_check.py`: it parses the file and reports the old pre-D35 layout, empty searches and placeholders.

### 6. MCP and Python

- **Jobgether:** load `mcp__jobgether__searchJobs` with ToolSearch and call it once with one target title and `limit: 1`. If the tool is missing, the operator must enable the `jobgether` server from [`.mcp.json`](../../../.mcp.json) and restart the session.
- **LinkedIn (only if enabled):** run `uvx mcp-server-linkedin@latest --status`. If it isn't logged in, ask the operator to run `uvx mcp-server-linkedin@latest --login` themselves. It opens a real browser, and they solve any captcha or 2FA. Never call a LinkedIn search or detail tool here.
- **Indeed (only if enabled):** the operator needs the Claude in Chrome extension connected. Don't open Indeed here.
- **Python:** if the `python` line warns, rendering résumés and letters will fail in that Python. Tell the operator to install the modules into the Python they'll use: `python3 -m pip install python-docx reportlab pyyaml`.

### 7. Finish

Run `python3 pipeline/scripts/setup_check.py` again and show its output. Then list what's still open: any `missing` line, and the profile sections noted in §15. The next step is a retrieval run (see [`pipeline/runbook.md`](../../runbook.md)).
