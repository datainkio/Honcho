"""Names for Application Tracking tasks and the folders that hang off them.

A task is `<Company> - <Job title>.md`; its résumé and cover-letter folders reuse the same name:
`applications/<Company> - <Job title>/`, one folder per posting holding `resume.md`, the résumé `.docx` and `.pdf`,
`cover-letter.md` and the letter `.docx` (named `… - Cover Letter.docx`, see LETTER_SUFFIX).
Postings that share a company and title (a role posted once per state, say) carry the job id: new tasks as
`<Company> (<job_id>) - <Job title>` (see unique_title), older ones as `<Company> - <Job title> (<job_id>)`.
dotpm renames task files to slug(title), so look tasks up by their Job ID field with find_task(), never by file name.
"""
import json
import os
import re
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

import yaml

# The C loader (libyaml) parses the 10k-word project note in 4 ms against 41 ms; it gives the same results.
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

FM_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.S)


def split_text(text):
    """(frontmatter text, body) of a markdown document, or (None, text) when it has no frontmatter."""
    m = FM_RE.match(text)
    return (m.group(1), m.group(2)) if m else (None, text)


def split(path):
    """(frontmatter text, body) of a note; exits when it has none. The one reader the fold, the renderers, the packets
    and the lexicon share."""
    fm, body = split_text(Path(path).read_text(encoding="utf-8"))
    if fm is None:
        sys.exit(f"no frontmatter: {path}")
    return fm, body


def q(v):
    """A YAML scalar via JSON quoting: valid YAML, in the quoted style dotpm writes."""
    return json.dumps(v, ensure_ascii=False)


# One root for every path (D17): the Honcho repo, which is also the Obsidian vault task links are relative to.
# The active profile (`profiles/<name>.md`) names one file per input folder under applicant/ (HONCHO_PROFILE picks
# another profile for one run). Values match file stems case-insensitively, so `dossier: default` is DEFAULT.md.
ROOT = Path(__file__).resolve().parents[2]
VAULT_ROOT = ROOT
PIPELINE = ROOT / "pipeline"
SCRIPTS = PIPELINE / "scripts"
SKILLS = PIPELINE / "skills"
SPECS = PIPELINE / "specs"
MODELS = ROOT / "reference" / "content models"
APPLICANT = ROOT / "applicant"
LOGS = Path(os.environ.get("HONCHO_LOGS") or ROOT / "logs")
INBOX = LOGS / "inbox"
SEARCHES = LOGS / "searches"
RUNS = LOGS / "runs"
FIT = LOGS / "fit"
FIXTURES = LOGS / "fixtures"
APPLICATIONS = Path(os.environ.get("HONCHO_APPLICATIONS") or ROOT / "applications")
ENV_FILE = ROOT / ".env"
MCP_JSON = ROOT / ".mcp.json"
LETTER_SUFFIX = " - Cover Letter"  # cover-letter .docx stem ends with this; a résumé .docx/.pdf never does
_HONCHO_YAML = ROOT / "honcho.yaml"  # names this install's profile; personal, so gitignored
PROFILE_NAME = (os.environ.get("HONCHO_PROFILE")
                or (_HONCHO_YAML.is_file() and (yaml.safe_load(_HONCHO_YAML.read_text(encoding="utf-8")) or {}).get("profile"))
                or "DEFAULT")
PROFILE_FILE = ROOT / "profiles" / f"{PROFILE_NAME}.md"


def _profile():
    m = FM_RE.match(PROFILE_FILE.read_text(encoding="utf-8")) if PROFILE_FILE.is_file() else None
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def _pick(folder, key, suffixes=(".md",)):
    """The file in `folder` the profile's `key` names (default: 'default'), matched case-insensitively by stem."""
    want = str(_profile().get(key) or "default").lower()
    for suffix in suffixes:
        for p in sorted(folder.glob(f"*{suffix}")) if folder.is_dir() else ():
            if p.name[: -len(suffix)].lower() == want:
                return p
    return folder / f"{want.upper() if want == 'default' else want}{suffixes[0]}"


DOSSIER = _pick(APPLICANT / "dossiers", "dossier")
TRUTH_RULES = _pick(APPLICANT / "rules", "rules")
CRITERIA = _pick(APPLICANT / "criteria", "criteria", (".yaml", ".yaml.md"))
RESUME_TEMPLATE = _pick(APPLICANT / "resumes", "resume template")
LETTER_TEMPLATE = _pick(APPLICANT / "cover letters", "cover letter template")
QUESTIONS = _pick(APPLICANT / "questions", "questions")
RENDER_STYLE = _pick(APPLICANT / "styles", "style", (".yaml",))
LEXICON = LOGS / "lexicon.json"
# Tracking: the dotpm project note `applications/<project>.md` and its tasks in `applications/_tasks/`.
PROJECT = APPLICATIONS
PROJECT_NOTE = _pick(APPLICATIONS, "project")
TASKS = PROJECT / "_tasks"


def criteria_text():
    """The active criteria file's text. A `.yaml.md` copy (so Obsidian can open it) is plain YAML too."""
    return CRITERIA.read_text(encoding="utf-8")
JOB_ID = r"(?:\d{6,}|[0-9a-f]{24}|[0-9a-f]{16}|fj\d{6,}|ts\d{6,})"  # LinkedIn numeric id, Jobgether 24-character hex id, Indeed 16-character hex jk, Fantastic.jobs fj + ATS id, or TheirStack ts + id


def backup_dir():
    """Where scripts copy files before a bulk write: HONCHO_BACKUPS, else the system temp dir."""
    d = Path(os.environ.get("HONCHO_BACKUPS") or Path(tempfile.gettempdir()) / "honcho-backups")
    d.mkdir(parents=True, exist_ok=True)
    return d


@lru_cache(maxsize=1)
def candidate_name():
    """The candidate's name as written in file names and sign-offs: `name:` in the dossier's frontmatter."""
    profile = DOSSIER
    m = FM_RE.match(profile.read_text(encoding="utf-8"))
    name = (yaml.safe_load(m.group(1)) or {}).get("name") if m else None
    if not name:
        raise SystemExit(f"{profile} needs a `name:` in its frontmatter")
    return str(name)


def safe(s):
    """Drop a trailing [requisition code]; turn characters that break file names or wikilinks into '-'."""
    s = re.sub(r"\s*\[[^\]]*\]", "", s)
    s = re.sub(r'[/\\:*?"<>|#^\[\]]', "-", s)
    return re.sub(r"\s+", " ", s).strip(" .") if s.strip(" .") else s.strip()


def basename(company, title):
    return f"{safe(company)} - {safe(title)}" if company else safe(title)


def job_title(task_title, company):
    """The job's own title, from a task title in either form: `Company - Title` or legacy `Title — Company`."""
    t = re.sub(rf"\s*\({JOB_ID}\)$", "", task_title.strip())  # collision id, either form: see unique_title
    if company:
        t = re.sub(rf"^{re.escape(company)} \({JOB_ID}\) - ", f"{company} - ", t)
    if company and t.startswith(f"{company} - "):
        return t[len(company) + 3:].strip()
    for sep in (" — ", " | "):
        if company and t.endswith(sep + company):
            t = t[: -len(sep + company)].strip()
    return t


def folder_name(title, company):
    """Folder name for a task, from its `title` (not the file name: dotpm renames files to slugs).
    Keeps the collision id, as a trailing ` (<job_id>)`, so same-titled postings get separate folders."""
    m = re.search(rf"\s\(({JOB_ID})\)(?=$| - )", title.strip())
    return basename(company, job_title(title, company)) + (f" ({m.group(1)})" if m else "")


def task_folder(path, ids=None):
    """Folder name for a task note, whatever its file is called."""
    ids = ids or field_ids()
    fm = task_fm(path)
    return folder_name(fm["title"], (fm.get("customFields") or {}).get(ids["Company"], ""))


def load_yaml(text):
    return yaml.load(text, Loader=_LOADER)


# Parsed frontmatter by path, valid while the file's mtime and size are unchanged. A lookup after the first costs a
# stat, so the fold, the renderers and task_links no longer re-parse 553 tasks and the project note per call, and a
# file another process rewrites (the fold, dotpm) is re-read.
_FM_CACHE = {}


def _cached_fm(path):
    st = path.stat()
    key = (st.st_mtime_ns, st.st_size)
    hit = _FM_CACHE.get(path)
    if hit and hit[0] == key:
        return hit[1]
    fm = load_yaml(FM_RE.match(path.read_text(encoding="utf-8")).group(1)) or {}
    _FM_CACHE[path] = (key, fm)
    return fm


def project_fm():
    """The project note's frontmatter (customFields, config.statuses, ...). Treat as read-only: it is shared."""
    return _cached_fm(PROJECT_NOTE)


def field_ids():
    return {f["name"]: f["id"] for f in project_fm()["customFields"]}


def task_fm(path):
    """A task's frontmatter. Treat as read-only: it is shared."""
    return _cached_fm(path)


def job_id(path, ids=None):
    ids = ids or field_ids()
    v = (task_fm(path).get("customFields") or {}).get(ids["Job ID"])
    return str(v) if v else None


def tasks():
    """Every task note, skipping one that vanishes between the listing and the read (dotpm renames files to slugs
    while Obsidian runs; the 2026-10-23 fold crashed on one). The renamed file is listed on the next call."""
    out = []
    for p in sorted(TASKS.glob("*.md")):
        try:
            task_fm(p)
        except FileNotFoundError:
            print(f"note: {p.name} vanished while listing tasks (renamed by dotpm?); skipped", file=sys.stderr)
            continue
        out.append(p)
    return out


def index():
    """{job_id: task path} for every task that has a Job ID."""
    ids = field_ids()
    out = {}
    for p in tasks():
        j = job_id(p, ids)
        if j:
            out[j] = p
    return out


def find_task(jid):
    return index().get(str(jid))


def frozen_statuses():
    """Statuses whose résumé and cover letter must never be rewritten: Applied (`blocked`) and Screening (`review`),
    plus every status with the dotpm 'done' toggle (`complete: true`) in the project note. That material has been
    submitted. Closed (`status-5ci3xo`) is not frozen: those postings were never submitted."""
    fm = project_fm()
    return {"blocked", "review"} | {s["id"] for s in (fm.get("config") or {}).get("statuses", []) if s.get("complete")}


def is_frozen(path, frozen=None):
    return str(task_fm(path).get("status")) in (frozen or frozen_statuses())


INTEREST_LABELS = ("Prospect",)


def statuses():
    """The project note's `config.statuses`: [{id, label, complete, ...}]."""
    fm = project_fm()
    return (fm.get("config") or {}).get("statuses", [])


def interest_statuses():
    """Status ids an interest statement may be written for (D19): those labeled Prospect (`todo`).
    Matched by label, never by id: ids are relabeled (the id `blocked` is Applied). A frozen or missing one is an error."""
    by_label = {s.get("label"): s["id"] for s in statuses()}
    missing = [l for l in INTEREST_LABELS if l not in by_label]
    if missing:
        raise SystemExit(f"no status labeled {', '.join(missing)} in {PROJECT_NOTE.name}")
    ids = {by_label[l] for l in INTEREST_LABELS}
    if ids & frozen_statuses():
        raise SystemExit(f"interest status is frozen: {sorted(ids & frozen_statuses())}")
    return ids


def interest_gate():
    """[(verdict, task path, folder)] for every task whose posting folder has a match report: 'ok', or 'skip: <why>'."""
    ids, allowed = field_ids(), interest_statuses()
    labels = {s["id"]: s.get("label") for s in statuses()}
    out = []
    for p in tasks():
        folder = APPLICATIONS / task_folder(p, ids)
        if not (folder / "match-report.md").exists():
            continue
        status = str(task_fm(p).get("status"))
        verdict = "ok" if status in allowed else f"skip: status {labels.get(status, status)}"
        out.append((verdict, p, folder))
    return out


def report_queue():
    """[(verdict, task path, folder)] for every Prospect with no match report yet: 'due' when its priority is
    critical, else 'skip: priority <p>' (D27). Prospects are resolved by label, as for interest statements."""
    ids, allowed = field_ids(), interest_statuses()
    out = []
    for p in tasks():
        fm = task_fm(p)
        if str(fm.get("status")) not in allowed:
            continue
        folder = APPLICATIONS / task_folder(p, ids)
        if (folder / "match-report.md").exists():
            continue
        prio = str(fm.get("priority") or "")
        out.append(("due" if prio == "critical" else f"skip: priority {prio or 'none'}", p, folder))
    return out


def render_style(fmt):
    """The `fmt` block ('docx' or 'pdf') of the profile's style file, with the shared `font` added."""
    style = yaml.safe_load(RENDER_STYLE.read_text(encoding="utf-8"))
    return {"font": style["font"], **style[fmt]}


SLUG_LEN = 60


def slug(title):
    """dotpm's file name for a task title: lowercased, spaces and slashes to '-', cut at 60 characters."""
    return re.sub(r"[\s/]", "-", title.lower())[:SLUG_LEN]


def unique_title(company, title, jid):
    """Title for a new posting's task. dotpm renames every task file to slug(title), so a title whose slug or file
    name another task already holds can't be saved ('A note named ... already exists'). On a clash the job id goes
    right after the company, inside the 60-character slug; a trailing id is cut off on long titles."""
    ids = field_ids()
    t = f"{company} - {title}" if company else title
    taken = set()
    for p in tasks():
        fm = task_fm(p)
        if str((fm.get("customFields") or {}).get(ids["Job ID"])) != str(jid):
            taken |= {p.stem.lower(), slug(str(fm.get("title", "")))}
    if slug(t) in taken or folder_name(t, company).lower() in taken:
        t = f"{company} ({jid}) - {title}" if company else f"{title} ({jid})"
    return t


if __name__ == "__main__":
    # `python3 pipeline/scripts/naming.py paths`: every resolved path, and whether it exists.
    # `python3 pipeline/scripts/naming.py ids`: field name -> id, so nobody reads the 10k-token project note to find one.
    # `python3 pipeline/scripts/naming.py fit`: the config's fit block, so the job-fetcher never reads the whole config,
    # or 'Fit check: off' while `selection: fit_check` is false.
    import sys
    if sys.argv[1:] == ["ids"]:
        for name, fid in field_ids().items():
            print(f"{fid}\t{name}")
    elif sys.argv[1:] == ["fit"]:
        cfg = yaml.safe_load(criteria_text()) or {}
        if not (cfg.get("selection") or {}).get("fit_check", True):
            print("Fit check: off (selection: fit_check is false). Stage every posting; delete none.")
            sys.exit(0)
        fit = cfg.get("fit")
        if not fit:
            sys.exit(f"no `fit:` block in {CRITERIA.name}: run /job-setup")
        print(f"Targets: {fit.get('targets', '')}")
        print(f"Location: {fit.get('location', '')}")
        print(f"Skip roles whose core is: {'; '.join(fit.get('skip') or [])}")
    elif sys.argv[1:] == ["paths"]:
        # Every resolved path, so nobody reads this file to find one.
        print(f"profile\t{PROFILE_NAME}\t{PROFILE_FILE}")
        for label, path in (("dossier", DOSSIER), ("truth rules", TRUTH_RULES), ("criteria", CRITERIA),
                            ("résumé template", RESUME_TEMPLATE), ("letter template", LETTER_TEMPLATE),
                            ("questions", QUESTIONS), ("render style", RENDER_STYLE), ("project note", PROJECT_NOTE),
                            ("tasks", TASKS), ("applications", APPLICATIONS), ("searches", SEARCHES),
                            ("inbox", INBOX), ("runs", RUNS), ("fit", FIT), ("lexicon", LEXICON), ("specs", SPECS),
                            ("content models", MODELS), (".env", ENV_FILE), (".mcp.json", MCP_JSON)):
            print(f"{'ok' if path.exists() else 'missing'}\t{label}\t{path}")
    elif sys.argv[1:] == ["reports"]:
        # Postings due a match report (D27): critical Prospects without one. Batch runs take only these.
        for verdict, p, folder in report_queue():
            print(f"{verdict}\t{job_id(p)}\t{folder.name}")
    elif sys.argv[1:] == ["interest"]:
        # Postings with a match report, and whether /interest-statement may write for them (D19).
        for verdict, p, folder in interest_gate():
            have = "statement" if (folder / "why-interested.md").exists() else "no statement"
            brief, report = folder / "interest.md", folder / "match-report.md"
            if brief.exists() and report.stat().st_mtime > brief.stat().st_mtime:
                have += ", brief stale (report edited since)"
            print(f"{verdict}\t{have}\t{job_id(p)}\t{folder.name}")
    else:
        sys.exit("usage: python3 pipeline/scripts/naming.py paths|ids|fit|interest|reports")
