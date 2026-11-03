---
title: "Match report — content model"
description: "Documents the findings from analysis of a given job posting, including keywords, terms, and direction for content generation. The goal is to provide transparency into the planned content so that applicants have an opportunity to tune as needed before render. Keep it with the other application artifacts (e.g. the files rendered for submission)."
type: content-model
status: draft
version: 0.1.0
updated: 2026-10-15
---

# Match report

Defines the high-value content from a given job description and how it will be integrated into the [template](business%20development/automation/skills/resume-tailoring/template.md) to produce material optimized for ATS parsing. See [Research ATS Parsing](goals/Resumé/_tasks/research-ats-parsing) for insight into the decisions guiding the strategy.

## Why

[ATS parsers](🤖%20Automated%20Tracking%20System.md) serve employers by automating the process of prioritizing applications for review. As such, they are the gatekeepers to visibility of a person's application.

## Role

This document is produced by the agent as the final step in the job retrieval flow. It provides the applicant an opportunity to review, refine, and approve the final forms of the resume and cover letter before committing to render.

## Structure

There are two main components: fields and keywords. **Fields** supplies the terms and phrases to populate specific areas of the template. **Keywords** identifies high-value vocabulary in the job description and provides direction for mapping them to existing concepts within the applicant's profile.

## Fields

Each item below corresponds to a specific area - a "slot" - in the template and describes the value to render.

### job_title_article

- filled_by: script
- source: job_title
- form: "'a' or 'an', whichever reads correctly before job_title"

## job_title

- filled_by: script
- source: "naming.job_title(): the posting's title without the company"
- form: the posting's title exactly as written
- example: Senior UX Designer

### role_summary

- filled_by: agent
- source: the posting's description
- form: "verb phrase that completes 'who will …'; base-form verb, no closing period"
- length: 6-15 words
- example: lead end-to-end design for a clinical data platform used by care team

### hook_quality

- filled_by: agent
- source: "one quality of the posting: its role, scope, industry, or a skill it asks for"
- form: "noun phrase that completes 'Given …'"
- length: 3-10 words
- example: "the role's focus on accessible public services"

### related_projects

- filled_by: agent
- source: choose from options; never write a new one
- form: the option as written
- options:
  - SBA.gov
  - MadeInAmerica.gov
  - Forms.gov
  - DEA.gov
  - the United States Web Design System
  - the Bixal HCD Team Playbook
  - the HCD Research Framework
  - the HCD Kickstart Dashboard
  - my work for USAID
  - my work for the USDA
  - my work with Enquos Total Health
  - my work with Seven Bridges Genomics
  - IBM's cognitive computing prototype

### common_theme

- filled_by: agent
- source: what the posting and related_projects share, true of that project per the profile
- form: "noun phrase that completes 'with its focus on …'"
- length: 2-6 words
- example: plain-language service design

## Keywords

The visibility of a given application depends heavily on the score granted by ATS.

Produced by the [keyword-matching](../specs/keyword-matching-spec.md) process, run on the template after the fields are filled. One row per high-value term in the posting:

| Column | Value |
| --- | --- |
| term | the term as the posting writes it |
| found as | `exact`, `variant` (spelling), `synonym`, or `absent` |
| where | the template section and the wording found there; blank when absent |
| action | none for exact; the replacement for variant and synonym (template wording → posting wording); `gap` for absent |
| backing | the profile section that supports the term; blank when none |

After the table:

- **Count:** high-value terms present once the actions are applied, against the 25-35 target. A shortfall is recorded as a gap.
- **Gaps:** each absent term, and any shortfall, as bullets of one short line each, for review. No paragraphs.

The report carries no Slot choices prose: the Fields table is the record of the slots.
