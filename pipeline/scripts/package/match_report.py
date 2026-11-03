"""Readers for a posting's match report: its pipe tables and the notes under them.

Shared by render_resume.py (the Fields and Keywords tables), match_packet.py (the letter and interest packets) and
keyword_lexicon.py, so none of them imports a renderer and the packets build without python-docx or reportlab.
A library, not a command.
"""
import re


def table(md, heading):
    """Rows of the first pipe table under `## heading`, as lists of stripped cells (header and rule dropped)."""
    m = re.search(rf"^## {heading}\n(.*?)(?=^## |\Z)", md, re.M | re.S)
    rows = [l for l in (m.group(1).splitlines() if m else []) if l.startswith("|")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]


def section(md, heading):
    """The text under `## heading`, up to the next `## `."""
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", md, re.M | re.S)
    return m.group(1).strip() if m else ""


def after_table(md, heading):
    """Text in a section after its pipe table: a match report's Count and Gaps notes."""
    lines = section(md, heading).splitlines()
    last = max((i for i, ln in enumerate(lines) if ln.startswith("|")), default=-1)
    return "\n".join(lines[last + 1:]).strip()
