---
description: ""
type: spec
status: draft
---

## User Stories

As an agent processing a given job description to produce an application, I want to produce a resume file tailored for ATS parsers so that it receives maximum visibility.

As an agent evaluating a resume, I want to know how and where I can integrate high-value terms into its content so that ATS parsers fall in love and want to make sweet, sweet datacenter love to it.

## Decisions

Be efficient: evaluate the resume _after_ the fields have been populated. In this state the resume should be able to stand on its own as a complete document without tuning.

1. Identify high-value terms in the job posting.
2. For each high-value term, search the resume for:

- exact matches
- spelling variations
- synonyms
- absence of matches, variations, and synonyms.

3. For each exact match, do nothing. Assume that what is there is enough.
4. For each spelling variation, propose adopting the spelling used by the job description.
5. For each synonym, propose replacing the template's wording with the job description's wording.
6. When a concept is not represented at all, record it as a gap in the match report and continue.
7. Aim for 25-35 high-value terms present in the résumé once steps 3-5 are done. If fewer are present, record the shortfall in the match report as a gap.

Steps 4 and 5 are proposals written to the match report. The agent never applies them: the skill edits only slot values. Russ reviews the report and tunes the template's fixed text himself. The report is the single stop for review, for gaps and shortfalls alike.

## Open questions
