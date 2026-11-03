#!/usr/bin/env python3
"""Characters that must never appear in résumé or cover-letter text (decision D9).

Online application forms reject `< > { } "` (and the curly double quotes “ ”) as invalid input and
won't submit until each one is found and removed. Résumé and cover-letter bodies are checked here:
the renderers refuse to render a body that contains one, and this script lints the masters.

Use in code:   charset.check(body, where)       # raises ValueError listing each hit
Lint:          python3 pipeline/scripts/package/charset.py       # every resume.md, cover-letter.md, why-interested.md and questions.md under applications/
Fix in place:  python3 pipeline/scripts/package/charset.py --fix # applies the replacements below, backing up first

The templates under applicant/ are never linted: a résumé template's slots are written {{ name }}.

Replacements (the only ones --fix makes):
    p<0.10        ->  p under 0.10
    "quoted"      ->  'quoted'      (straight or curly double quotes become single quotes)
Anything else it finds is reported, not guessed at.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402

DATA = naming.ROOT  # report paths relative to the repo
ROOTS = [naming.APPLICATIONS]
MASTERS = ("resume.md", "cover-letter.md", "why-interested.md", "questions.md")
FORBIDDEN = '<>{}"“”'
FM_RE = re.compile(r"^---\n.*?\n---\n", re.S)


def body_of(text):
    m = FM_RE.match(text)
    return text[m.end():] if m else text


def find(text):
    """[(line number, character, context)] for each forbidden character in `text`."""
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in re.finditer(f"[{re.escape(FORBIDDEN)}]", line):
            hits.append((n, m.group(), line[max(0, m.start() - 25): m.end() + 15]))
    return hits


def check(text, where="text"):
    hits = find(text)
    if hits:
        shown = "; ".join(f"line {n} {c!r} in ...{ctx}..." for n, c, ctx in hits[:5])
        raise ValueError(f"{where}: {len(hits)} forbidden character(s) ({FORBIDDEN}): {shown}")


def fix(text):
    text = re.sub(r"\bp\s*<\s*(\d)", r"p under \1", text)
    text = re.sub(r'["“]([^"“”\n]*)["”]', r"'\1'", text)
    return text


def masters():
    return sorted(p for root in ROOTS for name in MASTERS for p in root.rglob(name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="apply the documented replacements to master bodies")
    ap.add_argument("--backup", type=Path, help="folder to copy each changed file into first (required with --fix)")
    args = ap.parse_args()
    if args.fix and not args.backup:
        sys.exit("--fix needs --backup <folder> (the data folders are not in git)")
    bad = changed = 0
    for p in masters():
        text = p.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        head, body = (text[: m.end()], text[m.end():]) if m else ("", text)
        if args.fix and (new := fix(body)) != body:
            dest = args.backup / p.relative_to(DATA)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, dest)
            p.write_text(head + new, encoding="utf-8")
            body, changed = new, changed + 1
        for n, c, ctx in find(body):
            bad += 1
            print(f"{p.relative_to(DATA)}  {c!r}  ...{ctx}...")
    print(f"{len(masters())} masters, {changed} fixed, {bad} forbidden character(s) remaining")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
