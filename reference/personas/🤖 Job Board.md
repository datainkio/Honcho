---
type: persona
influence: supplies
---
# Job Board

Not one board. Each source publishes postings in its own way, so each one is an instance of this persona with its own search, detail, and description steps. Recruiters and hiring managers own the postings. A retrieval run talks to one instance at a time.

## Instances

All four run on request, never on a schedule.

| Instance | Retrieval | Pacing |
| --- | --- | --- |
| LinkedIn | Logged-in browser; two calls per posting | 8 s |
| Jobgether | Search API; description read from a Chrome page | 2 s |
| Indeed | Chrome; all three steps on the site | 8 s |
| UI/UX Jobs Board | Plain HTTP script; all three steps | 5 s |

## Decides

"Which postings exist, and which does this search return?" The board decides what a search can see. It does not decide whether Russ applies.

## Attention

Literal. It returns what matches the parameters it is given, and nothing more. Each instance limits or challenges automated access, so every run is paced and stops on a challenge page.

## Looks for

Search parameters in its own vocabulary. A stable job ID. A detail page with the posted date. The full description text.

## Rules out

Results that aren't postings: decoy and carousel cards, expired or filled listings, and placeholder employers such as "Our Team!". Skip them. Don't retry.

## Moves it forward by

Returning, for each posting, what a staged note needs: a stable ID, title, company, location, posted date, and the description verbatim.

## Retrieval by instance

Each instance has three steps. **Posts** come from a search. **Details** add the posted date and any other header fields. **Description** is the body text. Some instances return all three in one response, and some need a call or a page read for each.

### LinkedIn

- **Posts.** `search_jobs` (MCP `linkedin`) takes search parameters and returns job IDs with titles. One call per saved search, run by `pipeline/scripts/sources/linkedin_fetch.py`.
- **Details.** `get_job_details` takes one job ID and returns the full posting: header, posted age, and applicant count. This is a second call per posting.
- **Description.** The same `get_job_details` response. It runs from "About the job" to the "… more" line. The script refuses a page where that line is missing.
- **Pacing.** 8 seconds between calls. Needs a valid login session, and only one session at a time.

### Jobgether

- **Posts.** `searchJobs` (MCP `jobgether`; REST `jobgether.com/api/v1/jobs` is the same data). No key, and no company is required. Returns ID, title, company, location, URL, and posted date. Scope: full-remote roles in the US or Anywhere.
- **Details.** Already in the search result. No further call.
- **Description.** The API has no description. Open the listing URL in Chrome and keep the `Job description` section, up to "More" or "About the company". The rest of the page is Jobgether's own material.
- **Pacing.** 2 seconds between calls, its `robots.txt` Crawl-delay. Scripted requests to listing pages get 403, so the description is read in Chrome.

### Indeed

- **Posts.** The search page `indeed.com/jobs?q=…&l=Remote&fromage=…&sort=date`, read in Chrome. Each card yields a 16-character job key (`jk`), title, company, and location. Drop hidden decoy cards and carousel cards that lack a company or location. Indeed's official connector is not used: it has no stable ID and rejects the `jk`.
- **Details.** The listing page `indeed.com/viewjob?jk=…`. Posted date comes from the page's JSON-LD `datePosted`, read with JavaScript. No applicant count.
- **Description.** The page text, from "Full job description" up to "Report job".
- **Pacing.** 8 seconds between page loads. Stop on a Cloudflare page, a sign-in wall, or a message about unusual traffic.

### UI/UX Jobs Board

- **Posts.** `GET /design-jobs/<slug>?page=n` for the `remote-united-states` and `remote-anywhere` location pages. A script reads each card: job path, company, title, type, location, and age. Expired cards sink to the end. No sign-in and no API.
- **Details.** `GET /job/<id>-<slug>`. The slug is required; the bare ID returns 404. Title, company, and posted date come from the JSON-LD `JobPosting`. A filled listing has no POSTED label and no `JobPosting`, so skip it.
- **Description.** The `div.job-description` element, converted to text mechanically. Nothing is reworded.
- **Pacing.** 5 seconds, enforced by the script. Stop on any 403, 429, 5xx, or Cloudflare challenge, even one served with 200. Don't work around a challenge; the Chrome route is the fallback. Never fetch through WebFetch, which summarizes.

## Sources of truth

Design and field mapping: [integrated datasources spec](../business%20development/automation/specs/integrated-datasources-spec.md). Operating steps: [runbook](../business%20development/automation/runbook.md).
