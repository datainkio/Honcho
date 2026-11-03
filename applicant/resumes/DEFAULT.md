---
title: Resume Template
description: Defines the foundational structure and content for all generated resumes. Editable areas (aka slots) are delineated by double braces.
created:
updated:
audience: Applicant Tracking Systems
# Copy this file to applicant/resumes/<profile>.md, point your profile's `resume template` at it, and replace every
# <placeholder> with your own text. The renderer refuses < and >, so a placeholder left in place stops the render.
# Placeholders. Everything in the body outside a {{ slot }} is fixed text: render it as written.
# Each {{ slot }} in the body is defined below. A slot holds words or a phrase, never a sentence
# or narrative. Its value must read correctly in the sentence around it, take its terms from the
# posting, and claim nothing the dossier doesn't back. No < > { } or double quotes
# in a value (D9). A slot left unfilled keeps its braces, which the renderer refuses.
slots:
  job_title_article:
    filled_by: script
    source: job_title
    form: "'a' or 'an', whichever reads correctly before job_title"
  job_title:
    filled_by: script
    source: "naming.job_title(): the posting's title without the company"
    form: the posting's title exactly as written
    example: Senior UX Designer
  role_summary:
    filled_by: agent
    source: the posting's description
    form: "verb phrase that completes 'who will …'; base-form verb, no closing period"
    length: 6-15 words
    example: lead end-to-end design for a clinical data platform used by care teams
  hook_quality:
    filled_by: agent
    source: "one quality of the posting: its role, scope, industry, or a skill it asks for"
    form: "noun phrase that completes 'Given …'"
    length: 3-10 words
    example: "the role's focus on accessible public services"
  related_projects:
    filled_by: agent
    source: choose 2-3 from options; never write a new one
    form: the option as written
    # List the projects from your dossier a summary may name, each written as it should read in the sentence.
    options:
      - <project one>
      - <project two>
      - <project three>
      - <my work for an organization>
  common_theme:
    filled_by: agent
    source: what the posting and related_projects share per the dossier
    form: "noun phrase that completes 'with its focus on …'"
    length: 2-6 words
    example: plain-language service design
---

## Contact Information

<Your Name>
<portfolio URL>
<email>
<phone>

## Summary

<Two or three sentences that hold for every application: who you are, what you do best, and the kind of role you take on.>

You are looking for {{ job_title_article }} {{ job_title }} who will {{ role_summary }}. Given {{ hook_quality }}, you will find {{ related_projects }} with their focus on {{ common_theme }} to be particularly interesting.

<One closing sentence, such as where to see your portfolio.>

## Experience

### <Start> - current: <Title>, <Organization>

<What you were responsible for, the scope, and the results you can attribute to your own work. Every claim here must trace to your dossier.>

### <Start> - <End>: <Title>, <Organization>

<Repeat one block per role, most recent first.>

## Education

### <Institution> (<Degree>)

<Field of study; the degree's status if it isn't conferred.>

## Awards & Recognition

- <Award: category>

## Certifications

#### <Certification>, <Issuer>, <Month Year>
