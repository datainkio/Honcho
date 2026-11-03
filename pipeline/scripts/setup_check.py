#!/usr/bin/env python3
"""Check that this install is ready to run: paths, profile, truth rules, config, tracking project and Python modules.

`python3 pipeline/scripts/setup_check.py` prints one line per check (`ok`, `warn` or `missing`) and exits 1 if anything is missing.
Read-only. /job-setup runs it first and last; see applicant/criteria/README.md for the paths and their env overrides.
"""
import importlib.util
import re
import shutil
import sys

import yaml

import naming

CONFIG = naming.CRITERIA
SOURCES = ("linkedin", "jobgether", "indeed", "uiux", "fantastic", "theirstack")
PLACEHOLDER = re.compile(r"<(Your Name|rule \d[^>]*)>|YYYY-MM-DD")
missing = 0


def report(state, check, detail=""):
    global missing
    missing += state == "missing"
    print(f"{state:8}{check:14}{detail}")


def front(path):
    m = naming.FM_RE.match(path.read_text(encoding="utf-8"))
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


subs = [p for p in (naming.SEARCHES, naming.INBOX, naming.RUNS, naming.APPLICATIONS) if not p.is_dir()]
if subs:
    report("missing", "folders", f"create {', '.join(str(p) + '/' for p in subs)}")
else:
    report("ok", "folders", f"{naming.LOGS}, {naming.APPLICATIONS}")

if not naming.PROFILE_FILE.is_file():
    report("missing", "run profile", f"{naming.PROFILE_FILE} (HONCHO_PROFILE={naming.PROFILE_NAME})")
else:
    report("ok", "run profile", str(naming.PROFILE_FILE))

profile = naming.DOSSIER
if not profile.is_file():
    report("missing", "dossier", f"{profile} (copy applicant/dossiers/DEFAULT.md)")
else:
    text = profile.read_text(encoding="utf-8")
    name = str(front(profile).get("name") or "")
    gone = [n for n in range(1, 18) if not re.search(rf"^## {n}\. ", text, re.M)]
    if not name or PLACEHOLDER.search(name):
        report("missing", "dossier", f"{profile.name}: no `name:` in the frontmatter")
    elif gone:
        report("missing", "dossier", f"{profile.name}: numbered headings missing: §{', §'.join(map(str, gone))}")
    else:
        report("ok", "dossier", f"{profile} ({name})")

rules = naming.TRUTH_RULES
if not rules.is_file():
    report("missing", "truth-rules", f"{rules} (copy applicant/rules/DEFAULT.md)")
elif PLACEHOLDER.search(rules.read_text(encoding="utf-8")):
    report("missing", "truth-rules", f"{rules} still has template placeholders")
else:
    report("ok", "truth-rules", str(rules))

cfg = {}
if not CONFIG.is_file():
    report("missing", "config", f"{CONFIG} (name a criteria file in the run profile)")
else:
    try:
        cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        report("missing", "config", f"does not parse: {e}")
src = cfg.get("sources") or {}
on = [s for s in SOURCES if (src.get(s) or {}).get("enabled", s == "jobgether")]
for s in on:
    block = cfg if s == "linkedin" else cfg.get(s) or {}
    if not block.get("searches"):
        report("missing", "config", f"{s} is enabled but has no searches")
    elif "<" in str(block["searches"]):
        report("missing", "config", f"{s} searches still have template placeholders")
if cfg:
    report("ok" if on else "missing", "sources", ", ".join(on) or "none enabled")
    fit = cfg.get("fit") or {}
    if not (fit.get("targets") and fit.get("location")) or "<" in str(fit):
        report("missing", "fit", "`fit:` needs targets and location, without placeholders")
    else:
        report("ok", "fit", fit["location"])

if not naming.PROJECT_NOTE.is_file():
    report("missing", "tracking", f"{naming.PROJECT_NOTE} (create the Obsidian Project Manager project)")
elif not naming.TASKS.is_dir():
    report("missing", "tracking", f"{naming.TASKS}/ (create it)")
else:
    report("ok", "tracking", str(naming.PROJECT))

render = [m for m in ("docx", "reportlab") if importlib.util.find_spec(m) is None]
if render:
    report("warn", "python", f"{sys.executable} lacks {', '.join(render)}: résumé and letter rendering needs them")
else:
    report("ok", "python", sys.executable)

if "linkedin" in on:
    report("ok" if shutil.which("uvx") else "missing", "uvx", shutil.which("uvx") or "not on PATH (LinkedIn needs it)")

sys.exit(1 if missing else 0)
