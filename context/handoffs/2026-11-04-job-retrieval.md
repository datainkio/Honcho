---
status: superseded
---

# Handoff: job-retrieval run, 2026-11-04

For the next session (or Russ) picking up this run. State is on disk; nothing here needs the old conversation.

## Where the run stands

Sources run: LinkedIn, UI/UX Jobs Board, Jobgether. Fantastic and TheirStack did not run: `.env` is missing, so neither API key is set and no credits were spent.

36 tasks were folded today. 23 are Prospects posted 2026-11-04, and Russ chose the 16 at priority critical for packages. All 16 have a match report, résumé (.docx, .pdf) and cover letter (.docx). `charset.py` exits 0. No question answers, by Russ's choice. Every status is still `todo`.

Russ told the session to check Matching approved on these 16 without reviewing the reports first. That was a one-time instruction. D22 still stands for later runs.

Job ids: 4487243887 4487066786 4485083668 4486385193 4486383212 4486310309 4485095050 4487040846 4487042078 4487018938 4485077816 4485083680 4485091349 4486368958 4486388144 4486307263

Posted today, not critical, no package: Apex, CareSource, Checkr, Robert Half (high); AAA, Experis (medium); Capital One (low).

## Review before submitting

- Not remote: Abbott (on site daily, Lake Forest IL), Allegion (hybrid, Golden CO), Stampli (hybrid 3 days, Austin), Pitney Bowes (hybrid 4 days, Shelton CT, no relocation), Amazon (Arlington VA or Seattle WA, no remote stated).
- GSW: listed California and remote, but pay is in CAD. Confirm US eligibility.
- Crewlia x4: junior roles, which profile section 13 advises against. Each letter states 20+ years and gives no reason for applying. Keyword counts are 11-14 because the JDs are short.
- Staffing, unnamed clients: Aquent x4, Skill (the JD names Aquent as partner; the letter says Dear Skill), TEKsystems ($60-70/hr; the body says Lead Designer; closes Nov 16).
- Under the 25-35 keyword target: Aquent Multidisciplinary 21, GSW 24, Crewlia x4. All recorded in Gaps.
- Wording to check: forward-looking lines in the Crewlia Junior Product Designer letter ('I would flag unclear requirements') and the Allegion letter ('I would bring that instinct'); Abbott's role_summary slot names point-of-care diagnostics; the Allegion letter's Figma, GitHub and Claude Code references come from the résumé's vocabulary; Aquent Sr. Product and Content's 'cloud code usage' is listed as partly backed; Amazon's title 'GREF – Global Product' reads awkwardly on the résumé.
- Letter page count: `soffice` isn't installed, so one-page fit is unconfirmed for the .docx files. Each letter's `open_questions` lists details Russ could add.
- `HAACP` in the dossier is likely a typo for HACCP. No résumé carries it.

## Decisions still open

1. Delete three new duplicate tasks? `Deel - Staff Product Designer.md` (old `deel---staff-product-designer.md` is Applied, same job id), `Contra - Senior Product Designer.md` (old slug task, same job id), `Wander - Senior Product Designer.md` (old task of the same name is LinkedIn 4475089981; new is UI/UX 1660426; replace it with the Portfolio copy). None has a new package. Until then, Deel's new task sits at Prospect, so the freeze doesn't protect its folder: don't render 1656626.
2. Refresh links on the old tasks? `task_links.py` dry run said 622 of 651 would change, and nobody has reviewed why. The sample review comes first.
3. Is `status-s62o7t` (297 old tasks) still a valid status? It wasn't among the project note's status rows checked.

## Changed this session

- `pipeline/scripts/sources/linkedin_fetch.py` (uncommitted): one feedback reference now routes a page to `parse_redesigned`, and the 'We had trouble finding exact matches' banner is a badge. The real `experience-designer` re-run parsed 125 jobs with 0 unlabeled.
- 623 tasks copied from `Portfolio/goals/Application Tracking/_tasks` into `applications/_tasks/` with no overwrites. The Portfolio originals are untouched. `applications/_tasks/` is gitignored.
- `applicant/rules/russ.md` replaced with `Portfolio/business development/source/truth-rules.md`. `applicant/criteria/russ.yaml` moved to the D35 layout (gitignored).
- Aquent UI/UX (4485083668) and Sr. Product and Content (4485091349): ' 2' added to the task titles to separate their folders from older packages. Report `job_title:` keys keep the 2 off résumés and letters. The older folders are untouched.
- The `backup/local-main-2026-11-04` branch holds the 5 local commits dropped by the hard reset at the start of the session.

## Known bug, not fixed

`pipeline/scripts/package/match_packet.py` line 292 names batch files to the second, so parallel agents overwrite each other's packets. All report agents hit it and caught it. Add a pid or uuid to the name. Until then, build packets one at a time in the main session and copy each batch file.

## Next

The 2026-11-03 handoff is superseded by this one. Its 24 tasks were not found: a search of `~/Projects` for one of its job ids (4484619252) hits only that handoff, and a spot check of three ids finds none in `applications/_tasks/`. The Creative Circle and Wealthfront folders exist, so at least some packages survive with no task. The Portfolio copy may also be stale, because any status changed in Honcho after the migration isn't in it. Find the Honcho tasks, or re-check statuses, before trusting the freeze on older postings.

Russ reviews the 16 packages and answers the open decisions. Add `.env` keys to run the paid sources. `naming.py reports` still lists due rows from older tasks and other sources; write those only when Russ asks.
