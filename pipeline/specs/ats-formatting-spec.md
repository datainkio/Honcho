---
description: "The visibility of applications within a hiring pipeline is determined by the ATS parsers that receive them. This file documents the project's direction for applying best practices for proper ATS formatting."
type: spec
status: draft
---
ATS score four signals — keyword match, recency/current-title match, clean section parse, in-context term frequency — and recruiters run Boolean searches, so required terms must appear verbatim somewhere honest or the résumé never enters the result set. Let required terms recur naturally across summary + skills + bullets; never stuff.

## User Stories
- As an Agent, I want for the resumes I produce to follow established conventions and practices for optimal ATS formatting so that the resumes have the greatest chance of being seen by human eyes.
- As Russ, I want to follow best practices for ATS formatting so that my edits to rendered resumes maintain or increase their chances of being seen by human eyes.
- As a Recruiter or Hiring Manager, I want for applicants to submit resumes formatted according to ATS best practices so that I can make confident informed decisions about the quality of the candidate.

## Rules

These rules bind every rendered résumé and cover letter. The [resume-tailoring](../skills/resume-tailoring/SKILL.md) and [cover-letter-writing](../skills/cover-letter-writing/SKILL.md) skills check against them. Keyword matching (exact titles, required terms, acronyms) is a separate concern: see the [keyword-matching spec](keyword-matching-spec.md).

### File format

- `.docx` is the default submission format.
- `.pdf` only when the posting or application form explicitly asks for one. `pipeline/scripts/package/render_pdf.py` renders it beside the `.docx` from the same content.
- A PDF has selectable text and embedded fonts. Never submit a scanned or image-only PDF.
- No page limit for résumés ([D18](../../context/decisions.md)): the template sets the content, so length is not a tailoring lever. A cover letter is one page.

### Layout

- Single column.
- No tables, text boxes, graphics or icons.
- No skill bars or ratings: list skills as plain text.
- Contact details as plain text in the body, never in the document header or footer.

### Headings

- Standard section headings only, no clever synonyms: Professional Summary, Skills, Professional Experience, Education, Certifications, Awards & Recognition.
- The cover letter uses the same header block as the résumé.

### Typography

- A standard font at 10–12pt: Calibri, Arial, Georgia or Times.
- `.docx` and `.pdf` use the same font, embedded in the PDF.
- Font size is fixed. Length never shrinks it (no page limit, D18).
- The values (font, sizes, colors, spacing, margins, bullets) live in the render style (`naming.py paths`, row `render style`). Both renderers read it, so edit formatting there, never in the scripts.

### Dates

- 'Month Year' format: 'Jan 2020 - Mar 2023'.

### Hidden content

- No white text or hidden keyword blocks. Parsers and recruiters both treat them as manipulation.

### Editing a rendered file

- Hand edits to a rendered `.docx` or `.pdf` are allowed, as long as the result still meets these rules. A re-render from `resume.md` (or `cover-letter.md`) overwrites them.
- A frozen posting ([D13](../../context/decisions.md)) gets no edits of any kind.

## Related, not ATS

- Form-safe text ([D9](../../context/decisions.md)): no `< > { } "` or curly quotes. That rule exists because application forms reject those characters, not because parsers do. The skills' checklists keep it.

## Decisions

- **2026-10-16: One font, Arial.** Both renderers use the font named in the render style (`naming.py paths`, row `render style`). Calibri has no TTF on this Mac, so the PDF can't embed it.
- **2026-10-16: Fixed PDF size.** `max_pages` and the 9pt step-down were removed; the PDF renders at the configured size whatever its length.
- **2026-10-16: Hand edits allowed.** A rendered `.docx` or `.pdf` may be edited by hand if it still meets these rules (see [Editing a rendered file](#editing-a-rendered-file)).

## Sources

**ATS formatting (web, 2026):**

- ATS-Friendly Resume Guide 2026 — https://owlapply.com/en/blog/ats-friendly-resume-guide-2026-format-keywords-score-and-fixes
- PDF vs DOCX for ATS in 2026 — https://cvcraft.roynex.com/blog/pdf-vs-docx-resume-ats-2026
- PDF vs Word: which ATS reads correctly — https://scale.jobs/blog/pdf-vs-word-resume-format-ats-reads-correctly
- ATS-Friendly Resume Format rules — https://www.resumeprofessionalwriters.com/ats-friendly-resume-format/

**Prior art:**

- resume-ats-optimizer — https://github.com/Paramchoudhary/ResumeSkills/blob/main/skills/resume-ats-optimizer/SKILL.md
