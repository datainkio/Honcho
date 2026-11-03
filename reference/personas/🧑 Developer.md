---
type: persona
influence: advises
---
# Developer

A peer with responsibility for implementing design strategies.

## Decides
"Does this designer understand how things get built?"
## Attention
Brief, but will open dev tools on the site.
## Looks for
- A site that is fast, accessible, and well made. 
- Readable code and meaningful documentation. 
- Signs of clean handoff. 
- Collaboration skillzorz.
- Awareness and appreciation for technical constraints.
- Performance & accessibility metrics (e.g. Lighthouse).
## Rules out
Motion that stutters. Technical claims without evidence.
## Moves it forward by
Vouching: "This is a guy I can work with and who will make me look like a goddamn hero."

## At the repo

Reached from the site footer, a résumé link, or a recruiter forwarding the GitHub profile. Usually reading on github.com, not cloning. Gives the README about a minute, then opens two or three files to check it.

### Information needs
In the order they ask:
1. **What is this?** One sentence, a live link, and a screenshot or two.
2. **What's it built with, and why?** The stack, and the choices behind it.
3. **How is it put together?** Where content, design tokens, templates and motion each come from.
4. **Is it real?** Tests, CI, deploys, commit history. Evidence beats adjectives.
5. **Can I run it?** Only if steps 1 to 4 hold up. It must not fail without secrets.

### Evaluation criteria
- **Signal over volume.** A short README that links out to depth beats a long one.
- **Claims match code.** One broken claim, such as a dead link, a missing script, or `[[wikilinks]]` rendering raw on GitHub, discounts the rest.
- **Proportion.** Architecture fits the size of the problem. Ceremony on a portfolio site will read as over-engineering unless the README says what it buys.
- **Craft at the seams.** Accessibility and reduced motion are handled, not promised. Generated files are labelled. Secrets stay out of the repo.
- **Authorship.** Which decisions were the designer's own, especially now that AI tooling is visible in the tree.

### Questions they bring
- Why a static site generator and not React or Next.js?
- How do Figma and Sanity reach the page, and what happens when either is down?
- Is GSAP progressive enhancement, or does the page break without JavaScript?
- How is `prefers-reduced-motion` handled? Everywhere, or in places?
- What's tested, and what does CI actually run?
- Can I build it without Figma and Sanity tokens?
- What is `CLAUDE.md`, and why does every template have a `.md` beside it?
- Where should I look first to judge the code?

### What will surprise and delight
Each item is backed by a file in `dataink.io/frontend/`:
- **Design tokens pulled from Figma at build time.** `npm run build:design` writes `styles/colors.css` and the font families, so design and code can't drift silently. See `scripts/fetchFigma.js`.
- **A motion system with contracts.** Sections never call each other. They emit and listen through one `AnimationBus`, and boot is gated `director:ready` → `preloader:out`. Contract tests in `test/choreography/` enforce it. See `js/choreography/`.
- **Reduced motion as policy.** A written spec (`specs/animation/motion-accessibility-policy.md`), breakpoint motion profiles, and a reduced-motion branch required on every ScrollTrigger.
- **Specs before code.** Per-feature specs in `specs/animation/` and `specs/views/`, including a component API contract (`component-api.views-spec.md`).
- **Every template documents itself.** Each `.njk` and `.js` has a `.md` sidecar, checked by `npm run audit:sidecars`.
- **Atomic design.** Templates are organised into atoms, molecules, organisms, templates and pages, with `npm run scaffold:component` and `npm run scaffold:page` to generate new ones.
- **A console note for whoever opens dev tools.** See `views/templates/partials/dev-note/`.
- **Developer tooling.** `npm run doctor`, `npm run help`, and a workflow that turns `TODO` comments into GitHub issues (`.github/workflows/todo-to-issue.yml`).
- **AI-assisted workflow, kept low-key.** `CLAUDE.md`, sidecars as context contracts, and a knowledge graph exist to raise token efficiency and cut iteration effort. An agent reads a short sidecar instead of a whole implementation. Mention it once, as an engineering trade-off, near the end and never as a headline. Unexplained, these files look like noise.