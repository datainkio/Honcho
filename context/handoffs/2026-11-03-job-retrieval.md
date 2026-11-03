---
status: active
---

# Handoff: job-retrieval run, 2026-11-03

For the next session (or Russ) picking up this run. State is on disk; nothing here needs the old conversation.

## Where the run stands

LinkedIn only, one search (`experience-designer`). Stopped at **Matching approved** (D22) for twelve postings. Russ reviews each `match-report.md` and checks the task's Matching approved box. Never check it for him.

- Search: `logs/searches/2026-11-03--experience-designer.md`, 125 rows (capped at 5 pages), 95 kept by Select. Shortlist: `logs/runs/2026-11-03-070904-search/shortlist.tsv`.
- Staged 24 at `fetch_delay_seconds: 1`, no stops. Folded: 24 tasks created, inbox empty.
- 10 of the 24 are priority medium (over 100 applicants), so no report: Ashby x2, Consertus, Creative People, Design Citizen, DigitalOcean, Drake Software, Flex, Instrumentl, Quo.

## Match reports written (12), with what Russ should weigh

| job_id | Posting | Count | Flags |
|---|---|---|---|
| 4484619252 | Creative Circle, Lead Product Designer | 29 | staffing firm; contract-to-hire; EST hours |
| 4484620168 | CyberCoders, Senior UI/UX Designer - AI | 32 | staffing firm; no pay |
| 4486005364 | Haystack, Senior Product Designer | 22 (short 3) | recruiter; no pay range |
| 4484624818 | HighLevel, Lead Product Designer, Design Systems | 27 | India-based, US/UK hires; $150-190K; design-system case study required |
| 4485757956 | Kelly, Senior UX Designer | 27 | W2 contract to Oct 2027; $65/hr; occasional onsite Urbandale IA |
| 4486463754 | UnitedHealth Group, Sr Product Designer, Agentic Platform | 32 | DC-area hires 4 days in office (Baltimore may count); $112.7-193.2K; 10+ yrs |
| 4486810565 | UnitedHealth Group, Sr UX Designer, Web Experience | 30 | same office rule; $91.7-163.7K; AEM unbacked |
| 4486406195 | Vanta, Sr Product Designer, Agent Experience | 28 | $197-232K; 7+ yrs |
| 4486194620 | Vanta, Staff Product Designer, Activation | 25 | $236-278K; 8+ yrs B2B SaaS; wants activation metrics the profile lacks |
| 4486003435 | Wealthfront, Sr Staff Product Designer, Investing | 28 | ~$240K + equity; 8+ yrs consumer software |
| 4485775634 | AppleOne, Content Designer | 25 | staffing; 12-month contract; West Coast hours; choose the rendered job_title (JD says UI Designer IV) |
| 4484349776 | Aquent, Sr. Conversational Designer | 22 (short) | staffing; W-2 only; strip [AQ-24967] from job_title? |

## Next

1. Done: Russ had all twelve approved and rendered (résumé .docx/.pdf, `charset.py` 0), and all twelve cover letters rendered and linked. The Résumé variant field is retired (D36). Report `job_title:` overrides: Aquent (code stripped), both UnitedHealth (' - Remote' stripped); AppleOne kept 'Content Designer'.
2. Next per posting: cover letter, questions, `charset.py`. python-docx 1.2.0 and reportlab 4.5.1 are now in the system python3 user site (reportlab 5 needs Python 3.10+).
3. Backlog: `naming.py reports` still lists 13 due from earlier runs (Clarity Innovations, CVS Health, ECP, HighLevel Sr. Manager, Intelerad, Lingraphica, Maven Clinic, MURAL, ParentSquare, Roo, Stord, Talkiatry, UpMetrics). Russ chose today's 12 only.

## Changed this session (uncommitted)

- `linkedin_fetch.py`: stops on the server's soft rate-limit signal (`section_errors` type `rate_limit`) for searches and postings, and on an empty search without `no_matching_jobs`.
- D35: the criteria file is regrouped (`fit`, `selection`, `sources: <source>:`); scripts and docs follow. Backups of the old files are in the session scratchpad only.
- Commit `5570c03` (criteria docs, DEFAULT criteria) is still unpushed.
