---
description: "Defines how job posts get prioritized when they are first retrieved"
type: spec
status: draft
---

The goal is to calculate a single "fit score" for each job posting.

## User Stories

As Russ, I want to rank job postings according to a given set of criteria so that I can focus my effort on those most likely to yield positive results.

As an agent, I want to evaluate how job postings align with a given set of metrics so that I can assign the single numeric score Russ will use to determine the order in which job postings will be addressed.

## Evaluation Criteria

The fit score estimates the value of a retrieved job post. It is the product of multiple metrics calculated at retrieval, presented below in descending order of value:

1. freshness (i.e. time since job posting was published)

   a. minutes,

   b. hours

   c. days

   d. weeks

2. role seniority

   a. director

   b. lead

   c. senior

   d. seniority unclear or undefined

   e. junior

3. location

   a. remote

   b. hybrid

   c. on-site or in-office

## Decisions

## Open questions
