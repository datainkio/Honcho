#!/usr/bin/env python3
"""Render a résumé or cover-letter body to a Word file, styled by the profile's style file.

Shared by render_resume.py and render_cover_letter.py. render_pdf.py is the PDF counterpart. A library, not a command.
Needs python-docx and pyyaml.
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from package import charset  # noqa: E402

VAULT_ROOT = naming.VAULT_ROOT


def wikilink(path, label):
    return f"[[{path.resolve().relative_to(VAULT_ROOT).as_posix()}|{label}]]"


def _apply_style(st, font, v):
    """Set one Word style from a the profile's style file entry. Drops the theme fonts, which Word prefers over a named font."""
    st.font.name, st.font.size, st.font.bold = font, Pt(v["size"]), v["bold"]
    st.font.color.rgb = RGBColor.from_string(v["color"])
    rfonts = st.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rfonts.attrib.pop(qn(attr), None)
    pf = st.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(v["space_before"]), Pt(v["space_after"]), v["line_spacing"]


def render_docx(body, path, title):
    charset.check(body, Path(path).name)  # D9: no < > { } " in submitted text
    doc = Document()
    style = naming.render_style("docx")
    for key, name in (("body", "Normal"), ("h1", "Heading 1"), ("h2", "Heading 2"), ("h3", "Heading 3")):
        _apply_style(doc.styles[name], style["font"], style[key])
    m = style["margins"]
    for s in doc.sections:
        s.top_margin, s.bottom_margin = Inches(m["top"]), Inches(m["bottom"])
        s.left_margin, s.right_margin = Inches(m["left"]), Inches(m["right"])
    doc.core_properties.title = f"{naming.candidate_name()} - {title}"
    doc.core_properties.author = naming.candidate_name()

    def runs(p, text):
        for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
            if not part:
                continue
            if part.startswith("**"):
                p.add_run(part[2:-2]).bold = True
            elif part.startswith("*"):
                p.add_run(part[1:-1]).italic = True
            else:
                p.add_run(part)

    for line in body.splitlines():
        if not line.strip():
            continue
        if line.startswith("# "):
            h = doc.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("- "):
            runs(doc.add_paragraph(style="List Bullet"), line[2:])
        else:
            runs(doc.add_paragraph(), line)
    doc.save(path)
