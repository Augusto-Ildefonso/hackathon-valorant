"""PDF layout of the printable Action Plan (Stream D). A4, white page, text first, images where the document asks for them.

ReportLab only (BSD). The base fonts cover Latin-1 (pt-BR accents); characters outside it (e.g. CJK in a player's name)
are dropped instead of printed as boxes.
"""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import CondPageBreak, Flowable, Image, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .report import Block, Document
from .report_images import ImageBank, Picture, Strip

INK = colors.HexColor("#14171f")
MUTED = colors.HexColor("#5b6275")
ACCENT = colors.HexColor("#e0314b")
CARD = colors.HexColor("#1b1f2a")
RULE = colors.HexColor("#d9dce4")
PAGE_W, _PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def clean(text: str) -> str:
    """Latin-1 safe and XML-escaped."""
    return escape(text.encode("cp1252", "ignore").decode("cp1252"))


STYLES = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=26, leading=30, textColor=colors.white),
    "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=12, leading=16, textColor=colors.HexColor("#c9cdd8")),
    "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#9aa1b2")),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=INK, spaceBefore=14, spaceAfter=6, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=ACCENT, spaceBefore=10, spaceAfter=4, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=INK, spaceBefore=8, spaceAfter=2, keepWithNext=1),
    "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=4),
    "li": ParagraphStyle("li", fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK),
    "cap": ParagraphStyle("cap", fontName="Helvetica-Oblique", fontSize=8.5, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceBefore=3, spaceAfter=8),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8, leading=10, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white),
    "label": ParagraphStyle("label", fontName="Helvetica", fontSize=7.5, leading=9, textColor=colors.HexColor("#c9cdd8"), alignment=TA_CENTER),
}


class Rule(Flowable):
    """A thin accent line under a section title."""

    def __init__(self, width: float = CONTENT_W):
        super().__init__()
        self.width, self.height = width, 3

    def draw(self):
        self.canv.setStrokeColor(ACCENT)
        self.canv.setLineWidth(1.2)
        self.canv.line(0, 1, 28 * mm, 1)
        self.canv.setStrokeColor(RULE)
        self.canv.setLineWidth(0.5)
        self.canv.line(28 * mm, 1, self.width, 1)


class _Unknown(Flowable):
    """Placeholder tile for an icon the catalog does not have: dashed frame with a question mark."""

    def __init__(self, width: float, height: float):
        super().__init__()
        self.width, self.height = width, height

    def draw(self):
        c = self.canv
        c.setStrokeColor(colors.HexColor("#6b7285"))
        c.setDash(2, 2)
        c.setLineWidth(0.8)
        c.roundRect(1, 1, self.width - 2, self.height - 2, 3, stroke=1, fill=0)
        c.setDash()
        c.setFillColor(colors.HexColor("#9aa1b2"))
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(self.width / 2, self.height / 2 - 6, "?")


def _cover(doc: Document) -> list:
    rows = [[Paragraph(clean(doc.title), STYLES["title"])], [Paragraph(clean(doc.subtitle), STYLES["sub"])]]
    rows += [[Paragraph(clean(m), STYLES["meta"])] for m in doc.meta]
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD), ("LEFTPADDING", (0, 0), (-1, -1), 16), ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, 0), 18), ("BOTTOMPADDING", (0, -1), (-1, -1), 16), ("TOPPADDING", (0, 1), (-1, -1), 3),
        ("LINEBEFORE", (0, 0), (0, -1), 4, ACCENT),
    ]))
    return [t, Spacer(1, 10)]


def _picture(p: Picture, caption: str, max_w: float = 105 * mm) -> list:
    w = min(max_w, CONTENT_W)
    img = Image(io.BytesIO(p.data), width=w, height=w * p.height / p.width)
    img.hAlign = "CENTER"
    parts: list = [img]
    if caption:
        parts.append(Paragraph(clean(caption), STYLES["cap"]))
    else:
        parts.append(Spacer(1, 8))
    return parts


def _strip(s: Strip, caption: str) -> list:
    if not s.items:
        return []
    cells, h = [], 15 * mm
    for path, label in s.items:
        if path is None:  # the catalog has no picture: say so with a tile instead of leaving a silent gap
            cells.append([_Unknown(18 * mm, h), Paragraph(clean(label), STYLES["label"])])
            continue
        with PILImage.open(path) as im:
            ratio = im.width / im.height
            small = im.convert("RGBA")
            small.thumbnail((360, 360), PILImage.LANCZOS)  # the catalog originals are ~1024 px: far more than a 3 cm icon needs
            buf = io.BytesIO()
            small.save(buf, format="PNG", optimize=True)
        w = min(h * ratio, 30 * mm) if ratio >= 1 else h * ratio
        hh = w / ratio
        cells.append([Image(io.BytesIO(buf.getvalue()), width=w, height=hh), Paragraph(clean(label), STYLES["label"])])
    col_w = min(CONTENT_W / len(cells), 34 * mm)
    t = Table([[c[0] for c in cells], [c[1] for c in cells]], colWidths=[col_w] * len(cells), hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, -1), (-1, -1), 5), ("LINEAFTER", (0, 0), (-2, -1), 0.5, colors.HexColor("#2b3142")),
    ]))
    parts: list = [t]
    if caption:
        parts.append(Paragraph(clean(caption), STYLES["cap"]))
    else:
        parts.append(Spacer(1, 6))
    return parts


def _table(b: Block) -> list:
    total = sum(b.widths) or 1
    widths = [CONTENT_W * w / total for w in (b.widths or [1] * len(b.rows[0]))]
    data = [[Paragraph(clean(c), STYLES["cellh" if i == 0 else "cell"]) for c in row] for i, row in enumerate(b.rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CARD), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f5f8")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [t]


def _flowables(doc: Document, bank: ImageBank) -> list:
    out: list = _cover(doc)
    group: list | None = None  # a "round entry" (h3 and what follows) stays on one page

    def flush():
        nonlocal group
        if group:
            out.append(KeepTogether(group))
        group = None

    def add(items: list) -> None:
        # only the round heading plus its first two pieces (weapons strip + summary) are kept together
        if group is None:
            out.extend(items)
            return
        group.extend(items)
        if len(group) >= 4:  # heading + (strip, caption/spacer) + summary
            flush()

    for b in doc.blocks:
        if b.kind == "h1":
            flush()
            out += [CondPageBreak(45 * mm), Paragraph(clean(b.text), STYLES["h1"]), Rule(), Spacer(1, 4)]  # no title alone at a page bottom
        elif b.kind == "h2":
            flush()
            out += [CondPageBreak(35 * mm), Paragraph(clean(b.text), STYLES["h2"])]
        elif b.kind == "h3":
            flush()
            group = [Paragraph(clean(b.text), STYLES["h3"])]
        elif b.kind == "p":
            add([Paragraph(clean(b.text), STYLES["p"])])
        elif b.kind == "bullets":
            add([ListFlowable([ListItem(Paragraph(clean(i), STYLES["li"]), leftIndent=12) for i in b.items], bulletType="bullet", start="•",
                              leftIndent=12, bulletFontSize=8, bulletColor=ACCENT), Spacer(1, 4)])
        elif b.kind == "image":
            res = bank.resolve(b.ref)
            parts = _picture(res, b.caption) if isinstance(res, Picture) else _strip(res, b.caption) if isinstance(res, Strip) else []
            if group is None and parts:
                out.append(KeepTogether(parts))  # image and caption never split across pages
            else:
                add(parts)
        elif b.kind == "table":
            flush()
            out += _table(b)
    flush()
    return out


def _page(canvas, d) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 10 * mm, "VaváGym · plano de ação".encode("cp1252", "ignore").decode("cp1252"))
    canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Página {d.page}")
    canvas.setStrokeColor(RULE)
    canvas.line(MARGIN, 14 * mm, PAGE_W - MARGIN, 14 * mm)
    canvas.restoreState()


def render_pdf(doc: Document, bank: ImageBank) -> bytes:
    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=16 * mm, bottomMargin=20 * mm,
                            title=clean(doc.title), author="VaváGym", subject=clean(doc.subtitle))
    pdf.build(_flowables(doc, bank), onFirstPage=_page, onLaterPages=_page)
    return buf.getvalue()
