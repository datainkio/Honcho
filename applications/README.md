# Pipeline Output

This is where the pipeline writes the application packages.

## Versioning & Privacy

Given that the contents of this folder are specific to the operator, only the README and any sibling files get committed. Folders - assumed to contain pipeline output - remain local-only.

## The Application Package

Each posting gets one folder, named after its tracking task: `<Company> - <Job title>`. When two postings share a company and title, the folder name ends with ` (<job_id>)`. Each file is written by the skill or script on the arrow that points to it. Highlighted files are the ones you submit: upload the `.docx`/`.pdf` files and paste the text of `why-interested.md`.

```mermaid
flowchart TD
    task["Tracking task (JD)<br/>applications/_tasks/"]

    subgraph pkg["applications/#lt;Company#gt; - #lt;Job title#gt;/"]
        report["match-report.md"]
        resume["resume.md"]
        rdocx["#lt;Name#gt; - #lt;Title#gt;.docx"]
        rpdf["#lt;Name#gt; - #lt;Title#gt;.pdf"]
        brief["interest.md"]
        why["why-interested.md"]
        letter["cover-letter.md"]
        ldocx["#lt;Name#gt; - #lt;Title#gt; - Cover Letter.docx"]
    end

    task -- "/resume-tailoring" --> report
    report -- "Matching approved, then render_resume.py" --> resume
    resume --> rdocx & rpdf
    report -- "/interest-statement" --> brief
    brief --> why
    resume -- "/cover-letter-writing" --> letter
    letter -- "render_cover_letter.py" --> ldocx

    classDef submit stroke-width:3px
    class rdocx,rpdf,why,ldocx submit
```
