#!/usr/bin/env python3
"""Render a résumé or letter body to an ATS-safe PDF (selectable text, embedded font, single column).

Same markdown subset as the .docx renderer: `#`/`##`/`###` headings, `- ` bullets, **bold**, *italic*.
Font, sizes, spacing, margins and bullets come from the profile's style file (`pdf`); length never
shrinks the font (D18: no page limit).
Needs reportlab. The .docx stays the default
submission format (resume-tailoring skill, step 7); the PDF is for postings that ask for one, and as a layout check.
"""
import re
import sys
from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from package import charset  # noqa: E402

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
VARIANTS = {"": "", "-Bold": " Bold", "-Italic": " Italic", "-BoldItalic": " Bold Italic"}  # name suffix -> file suffix


def _register(font):
    for name, f in VARIANTS.items():
        if font + name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font + name, str(FONT_DIR / f"{font}{f}.ttf")))
    pdfmetrics.registerFontFamily(font, normal=font, bold=f"{font}-Bold", italic=f"{font}-Italic",
                                  boldItalic=f"{font}-BoldItalic")


def _inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)


def _build(body, path, title, style):
    def para(key):
        v = style[key]
        return ParagraphStyle(key, fontName=style["font"] + ("-Bold" if v["bold"] else ""), fontSize=v["size"],
                              leading=v["size"] * v["line_spacing"], textColor=HexColor("#" + v["color"]), alignment=TA_LEFT,
                              spaceBefore=v["space_before"], spaceAfter=v["space_after"])

    st = {key: para(key) for key in ("body", "h1", "h2", "h3")}
    size, bullet, m = style["body"]["size"], style["bullet"], style["margins"]
    flow, bullets = [], []

    def flush():
        if bullets:
            flow.append(ListFlowable([ListItem(Paragraph(b, st["body"]), leftIndent=bullet["indent"]) for b in bullets],
                                     bulletType="bullet", start=bullet["char"], leftIndent=bullet["indent"],
                                     bulletFontName=style["font"], bulletFontSize=size))
            bullets.clear()

    for line in body.splitlines():
        if not line.strip():
            continue
        if line.startswith("- "):
            bullets.append(_inline(line[2:]))
            continue
        flush()
        for prefix, key in (("### ", "h3"), ("## ", "h2"), ("# ", "h1")):
            if line.startswith(prefix):
                flow.append(Paragraph(_inline(line[len(prefix):]), st[key]))
                break
        else:
            flow.append(Paragraph(_inline(line), st["body"]))
    flush()
    doc = SimpleDocTemplate(str(path), pagesize=letter, title=f"{naming.candidate_name()} - {title}", author=naming.candidate_name(),
                            leftMargin=m["left"] * inch, rightMargin=m["right"] * inch, topMargin=m["top"] * inch,
                            bottomMargin=m["bottom"] * inch)
    doc.build(flow)


def render_pdf(body, path, title):
    charset.check(body, Path(path).name)  # D9: no < > { } " in submitted text
    style = naming.render_style("pdf")
    _register(style["font"])
    _build(body, path, title, style)
