# Indeed (opt-in)

Load this only when `sources: indeed: enabled` is true and the operator wants an Indeed run. Indeed is searched and read on indeed.com in the operator's signed-in Chrome (Claude in Chrome), behind Cloudflare, and it also carries Glassdoor's listings. Indeed's terms restrict automated access. Indeed's own connector (`mcp__claude_ai_Indeed__*`) is not used: its ids aren't stable.

**Wait 8 seconds between every page load**, search and listing pages alike. Run `await new Promise(r => setTimeout(r, 8000))` with `javascript_tool` before each `navigate` after the first.

## Search

For each entry under `indeed: searches:` in the criteria file (merged with `indeed: defaults:`), `navigate` to `https://www.indeed.com/jobs?q=<keywords>&l=Remote&fromage=<fromage>&sort=date`. Read the cards with `javascript_tool`, never `get_page_text`:

```js
const seen = new Set(), rot = '0123456789abcdef'.repeat(2);
[...document.querySelectorAll('a[data-jk]')]
  .filter(a => !a.closest('[aria-hidden="true"]') && a.offsetWidth > 0 && a.offsetHeight > 0)
  .map(a => { const c = a.closest('li') || a.parentElement;
    return { jk: a.dataset.jk, title: a.innerText.trim(),
      company: c.querySelector('[data-testid="company-name"]')?.innerText.trim() ?? '',
      location: c.querySelector('[data-testid="text-location"]')?.innerText.trim() ?? '' }; })
  .filter(r => /^[0-9a-f]{16}$/.test(r.jk) && !rot.includes(r.jk) && r.company && !seen.has(r.jk) && seen.add(r.jk))
```

It keeps visible cards only and drops the hidden decoy card, whose key is a run of consecutive hex digits. It also drops the 'Positions in …' carousel cards, which show no company or location and ignore the search filters. One page per search is enough: with `fromage` at 14 or less, no pager appears. **Never open a decoy key.**

Write `logs/searches/YYYY-MM-DD--ind-<name>.md` with `type: indeed-search-run` and the usual table (`jk` in the `job_id` column).

## Select

As Step 2 of the skill. Indeed often lists the same posting as LinkedIn with legal suffixes added ('Conservice LLC'); the script strips them. Observe `sources: indeed: pacing: max_fetches_per_run`. The picks go on the run's one combined shortlist (Step 2 of the skill).

## Fetch and stage

The `job-fetcher` agent, `source: indeed`. It opens `https://www.indeed.com/viewjob?jk=<jk>` (`navigate`, then a separate call) and reads only the description with `javascript_tool`: `document.querySelector('#jobDescriptionText')?.innerText`. Only if that returns null does it fall back to `get_page_text`, cut from the `Full job description` heading to `Report job`. It reads `posted` from the page's JSON-LD `datePosted`. Staged notes are `logs/inbox/<jk>.md` with `type: indeed-job` and `source_search: ind-<name>`.

## Hard stop

Stop on a Cloudflare page ('Verify you are human', 'Just a moment'), a sign-in wall, or any message about unusual traffic. Don't retry.
