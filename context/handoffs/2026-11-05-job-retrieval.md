---
status: active
---

# Handoff: job-retrieval run, 2026-11-05

State is on disk; nothing here needs the old conversation.

## Where the run stands

Sources: UI/UX, Jobgether, LinkedIn. 27 tasks folded, all at Prospect (`todo`), each with a match report, résumé (.docx, .pdf) and cover letter (.docx). `charset.py` exits 0. No question answers, by Russ's choice.

Russ told the session to check Matching approved on all 27 without reviewing the reports. That was a one-time instruction. D22 still stands for later runs.

Job ids: 6aec5ad81c8aea01fb86c137 1658926 1666526 6aebf8bb1c8aea01fb84ecaa 1658626 1662726 1659326 1666326 4487731060 4485563388 4486570729 4486715058 4487566979 4487532021 4485825182 4485821347 4485822275 4485829076 4485812704 4485810753 4485819330 4485808806 4485827164 4485811709 4485827154 4485807807 4485817518

## Paid sources

- Fantastic: stopped on 403, 'API Key has exceeded the allowed limit for "jobs" meter'. Not retried. Account quota or plan needs attention.
- TheirStack: killed mid-response when Fantastic stopped the run. No record written, so the same-day guard won't block a re-run. Russ skipped it. Whether it billed is unknown: check the balance.

## Review before submitting

- Not remote: BitGo (on-site Palo Alto), UiPath (hybrid Austin). Stryker: Weston FL preferred, remote needs approval; the task says San Diego.
- Ladders x13: employer unnamed, 'For our client' wording. Letters say 'Dear Ladders,' and skip the company paragraph. Payroll says both remote and 'hybrid office requirements'; Head of Design is listed as Finance & Insurance with healthcare duties.
- Weak fits: Maven (5+ years of UX writing unmet), OleOle (deferred pay that 'may never be payable'; shipped native apps unmet), Ladders Design Engineer (12 keywords), Ladders Product Ops (16), Stryker (Illustrator and Photoshop required, no backing), Clarity (2+ years XP and DoW use cases required, no backing).
- Management years: ZipRecruiter, UiPath and four Ladders roles ask for more than the profile backs. Letters give no year count.
- Under 25 keywords: 8 Ladders reports, shortfall recorded in Gaps.
- Letters state some gaps outright (GitLab, Maven, PeopleFinders, BitGo and others). Those lines assume the gap is real: correct any where Russ has the experience.
- Letter facts to confirm: Clarity 'civilian agencies' is inferred; Maven says the contract fits the consulting practice; 'GSA's Office of Evaluation Sciences' expands OES from outside the dossier, in the Ladders Growth letter and possibly others.
- Over 350 words: Ammortal 376, OleOle 358, UiPath 357. `soffice` isn't installed, so one-page fit is unconfirmed for every letter. Start with those three.
- One Sankey sentence repeats in three letters: Ladders Senior Manager UX, Ladders Investing, UiPath.
- Ammortal: posted as Senior Director, but the JD body says VP.
- Kamiwaza: `job_title: Senior UX Designer` added to the report so the company stays out of the Summary.

## Open work

Every open question is now a task in the dotpm project [`context/Honcho Dev/`](../Honcho%20Dev/Honcho%20Dev.md), 15 in all, including those carried from the 2026-11-04 handoff.

Decided by Russ on the whiteboard, 2026-11-05:

- HACCP: the dossier is corrected (3 places). Existing letters stay as they are, so 8 of these letters and the older Stampli letter still say HAACP.
- False gaps: agreed they are false. Existing résumés stay as they are. Task: Resolve false gaps in match reports.

## Working note

`applications/` is gitignored, so `rg` skips it without `--no-ignore`. This gave a false 'no reports' result today.

## Next

Russ reviews the 27 packages. Pipeline and data work comes from the Honcho Dev board.
