#!/usr/bin/env python3
"""Fold job-description notes into Application Tracking dotpm tasks.

Each staged <src>/<job_id>.md (default logs/inbox/) becomes (or updates) applications/_tasks/<Company> - <Job title>.md:
JD frontmatter -> the task's dotpm `customFields` (keyed by field id), JD body -> the task description
(note body). Field definitions live in the project note's `customFields`; missing ones are created,
existing ones are matched by name, so re-runs are idempotent.

Usage:
    python3 pipeline/scripts/tracking/fold_jobs_into_tasks.py                      # dry run: report only
    python3 pipeline/scripts/tracking/fold_jobs_into_tasks.py --write --consume    # apply, then delete staged notes
    python3 pipeline/scripts/tracking/fold_jobs_into_tasks.py --src logs/jobs   # fold a different staging folder
"""
import argparse
import datetime as dt
import json
import random
import re
import shutil
import string
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from naming import q, split  # noqa: E402

VAULT = naming.VAULT_ROOT
INBOX = naming.INBOX
PROJECT = naming.PROJECT
PROJECT_NOTE = naming.PROJECT_NOTE
TASKS = naming.TASKS
PROJECT_LINK = PROJECT_NOTE.relative_to(VAULT).with_suffix("").as_posix()  # dotpm finds the project by this link

# (field name, type, JD key). Order = column order in dotpm.
FIELDS = [
    ("Fit", "number", "fit_score"),
    ("Company", "text", "company"),
    ("Posting", "url", "url"),
    ("Job ID", "text", "job_id"),
    ("Location", "text", "location"),
    ("Work type", "select", "work_type"),
    ("Posted", "date", "posted"),
    ("Retrieved", "date", "retrieved_at"),
    ("Search", "text", "source_search"),
    ("Résumé variant", "text", "resume_variant"),
    ("Industry", "select", "industry"),
    ("Activities", "multiselect", "activities"),
    ("Technologies", "multiselect", "technologies"),
]
BASE_OPTIONS = {"work_type": ["remote", "hybrid", "onsite"]}


def new_id(n=16):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def refresh_links(task):
    """Re-insert the Posting / Résumé / Cover letter block that the fresh JD body doesn't carry."""
    from tracking.task_links import refresh
    refresh(task)


def value(jd_key, ftype, fm):
    v = fm.get(jd_key)
    if v in (None, "", []):
        return None
    if ftype == "date":
        return (v.date() if isinstance(v, dt.datetime) else v).isoformat()
    if ftype == "number":
        return float(v) if not float(v).is_integer() else int(v)
    if ftype == "multiselect":
        return [str(x) for x in v]
    return str(v)


def load_jobs(src):
    jobs = []
    for p in sorted(src.glob("*.md")):
        if p.name.startswith("README"):
            continue
        fm_text, body = split(p)
        jobs.append((p, naming.load_yaml(fm_text), body.lstrip("\n")))
    return jobs


def resolve_fields(project_fm, jobs):
    """Return [(id, name, type, jd_key, options)], reusing ids for existing names."""
    existing = {f["name"]: f for f in project_fm.get("customFields") or []}
    out = []
    for name, ftype, key in FIELDS:
        f = existing.get(name, {})
        opts = None
        if ftype in ("select", "multiselect"):
            seen = set(BASE_OPTIONS.get(key, [])) | set(f.get("options") or [])
            for _, fm, _ in jobs:
                v = value(key, ftype, fm)
                seen.update(v if isinstance(v, list) else [v] if v else [])
            opts = sorted(seen)
        out.append((f.get("id") or new_id(), name, ftype, key, opts))
    return out, [f for n, f in existing.items() if n not in {x[0] for x in FIELDS}]


def fields_block(fields, others):
    lines = ["customFields:"]
    for f in others:  # preserve any field defined by hand outside this mapping
        lines += [f"  - id: {q(f['id'])}", f"    name: {q(f['name'])}", f"    type: {q(f['type'])}"]
        if f.get("options"):
            lines += ["    options:"] + [f"      - {q(o)}" for o in f["options"]]
    for fid, name, ftype, _, opts in fields:
        lines += [f"  - id: {q(fid)}", f"    name: {q(name)}", f"    type: {q(ftype)}"]
        if opts is not None:
            lines += ["    options:"] + [f"      - {q(o)}" for o in opts]
    return "\n".join(lines)


def replace_key_block(fm_text, key, block):
    """Replace a top-level YAML key (and its indented continuation) or append it."""
    pat = re.compile(rf"^{re.escape(key)}:.*\n(?:[ \t]+.*\n|-.*\n)*", re.M)
    text = fm_text + "\n"
    if pat.search(text):
        return pat.sub(lambda _: block + "\n", text, count=1).rstrip("\n")
    return fm_text.rstrip("\n") + "\n" + block


def set_values(fm_text, values):
    """Replace or append `values` ({field_id: value}) inside a task's customFields block, leaving every other field
    as it is. The renderers use it to set one link field; the fold rewrites the whole block with task_values_block."""
    m = re.search(r"^customFields:.*\n((?:[ \t]+.*\n?)*)", fm_text + "\n", re.M)
    if not m:
        sys.exit("task has no customFields block")
    body = m.group(1)
    for fid, v in values.items():
        if isinstance(v, list):
            new = f"  {fid}: []\n" if not v else f"  {fid}:\n" + "".join(f"    - {q(x)}\n" for x in v)
        else:
            new = f"  {fid}: {json.dumps(v) if isinstance(v, (int, float)) else q(v)}\n"
        # drop any existing entry for this id (scalar line plus indented list items)
        body = re.sub(rf"^  {fid}:.*\n(?:    .*\n)*", "", body, flags=re.M)
        body = body.rstrip("\n") + "\n" + new
    return ((fm_text + "\n")[: m.start(1)] + body + (fm_text + "\n")[m.end(1):]).rstrip("\n")


def task_values_block(fields, fm, existing):
    """Merge JD values over the task's existing customFields; empty JD values never erase."""
    merged = dict(existing or {})
    for fid, _, ftype, key, _ in fields:
        v = value(key, ftype, fm)
        if v is not None:
            merged[fid] = v
    lines = ["customFields:"]
    for fid, v in merged.items():
        if isinstance(v, list):
            lines += [f"  {fid}:"] + [f"    - {q(str(x))}" for x in v]
        elif isinstance(v, bool) or isinstance(v, (int, float)):
            lines.append(f"  {fid}: {json.dumps(v)}")
        elif isinstance(v, (dt.date, dt.datetime)):
            lines.append(f"  {fid}: {q(v.isoformat())}")
        else:
            lines.append(f"  {fid}: {q(v)}")
    return "\n".join(lines) if len(lines) > 1 else "customFields: {}"


def new_priority(fm):
    """A new task's priority (D27): critical, or medium when LinkedIn showed over 100 applicants. Match reports are
    written only for critical Prospects (`naming.py reports`), so this is the triage step. Existing tasks keep theirs."""
    return "medium" if fm.get("over100") else "critical"


def new_task_fm(title, now, due="", priority="critical"):
    return "\n".join([
        "pm-task: true",
        f'projectId: "[[{PROJECT_LINK}|{naming.project_fm().get("title", PROJECT_NOTE.stem)}]]"',
        "parentId:",
        f"id: {new_id()}",
        f"title: {q(title)}",
        "type: task",
        "status: todo",
        f"priority: {q(priority)}",
        'start: ""',
        f'due: "{due}"',
        "progress: 0",
        "assignees: []",
        "tags: []",
        "subtaskIds: []",
        "dependencies: []",
        f"createdAt: {now}",
        f"updatedAt: {now}",
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--src", type=Path, default=INBOX, help="folder of staged <job_id>.md notes")
    ap.add_argument("--consume", action="store_true", help="delete each staged note once folded")
    args = ap.parse_args()

    jobs = load_jobs(args.src.resolve())
    if not jobs:
        print(f"nothing staged in {args.src}")
        return
    p_fm_text, p_body = split(PROJECT_NOTE)
    fields, others = resolve_fields(naming.load_yaml(p_fm_text), jobs)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    updated, created, links, skipped = 0, [], [], []
    backup = None
    if args.write:  # the tasks are the only copy of each JD (D5): copy each one before it is overwritten
        backup = naming.backup_dir() / f"fold-{dt.datetime.now():%Y%m%d-%H%M%S}"
        backup.mkdir(parents=True, exist_ok=True)
    for path, fm, body in jobs:
        jid = str(fm["job_id"])
        try:
            task = naming.find_task(jid)
            if task:
                t_fm, _ = split(task)
                updated += 1
            else:
                company = fm.get("company", "")
                title = naming.unique_title(company, fm["title"], jid)
                task = TASKS / f"{naming.folder_name(title, company)}.md"
                t_fm = new_task_fm(title, now, str(fm.get("retrieved_at") or now)[:10], new_priority(fm))  # due = retrieved date
                created.append(jid)
                links.append(f"[[{task.stem}|{title}]]")
            existing = (naming.load_yaml(t_fm) or {}).get("customFields")
            t_fm = replace_key_block(t_fm, "customFields", task_values_block(fields, fm, existing))
            t_fm = re.sub(r"^source_job:.*\n?", "", t_fm, flags=re.M)  # pre-D5 pointer to data/jobs/
            if args.write:
                if jid not in created:
                    # dotpm may have renamed the file since it was found: write where the task is now, never
                    # to the old name (which recreated Capital One's old file on 2026-10-23).
                    task = naming.find_task(jid)
                    if not task:
                        raise FileNotFoundError(f"task for {jid} vanished")
                    shutil.copy2(task, backup / task.name)
                task.write_text(f"---\n{t_fm}\n---\n\n{body.rstrip()}\n", encoding="utf-8")
                refresh_links(task)
                if args.consume:
                    path.unlink()
        except FileNotFoundError as e:  # renamed mid-run and not found again: leave the note staged for a rerun
            skipped.append(jid)
            print(f"  {jid}  skipped, still staged: {e}", file=sys.stderr)

    p_fm = replace_key_block(p_fm_text, "customFields", fields_block(fields, others))
    if links:
        p_fm = re.sub(r"^(taskIds:\n(?:  - .*\n)*)", lambda m: m.group(1) + "".join(f"  - {q(l)}\n" for l in links),
                      p_fm + "\n", count=1, flags=re.M).rstrip("\n")
        p_body = p_body.rstrip("\n") + "\n" + "".join(f"- [ ] {l}\n" for l in links)
    if args.write:
        PROJECT_NOTE.write_text(f"---\n{p_fm}\n---\n{p_body}", encoding="utf-8")

    print(f"{'WROTE' if args.write else 'DRY RUN'}: {len(jobs)} jobs -> {updated} tasks updated, {len(created)} created"
          + (f", {len(skipped)} skipped (rerun to fold them)" if skipped else "") + (f"; backups in {backup}" if backup else ""))
    for fid, name, ftype, key, opts in fields:
        filled = sum(value(key, ftype, fm) is not None for _, fm, _ in jobs)
        print(f"  {name:<15} {ftype:<11} {fid}  filled {filled}/{len(jobs)}" + (f"  options {len(opts)}" if opts else ""))


if __name__ == "__main__":
    main()
