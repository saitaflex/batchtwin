"""
Entry point: renders BUSINESS_PLAN.pdf.

    python docs/bp_build.py

Kept separate from build_business_plan.py (which holds the shared styles and
flowable helpers) so the content modules can import those helpers without a
circular import back through the builder.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

import build_business_plan as B
import bp_content_a as A
import bp_content_b as BB
import bp_content_c as C
import finance_model as FM

OUT = Path(__file__).resolve().parent
COVER_BG = colors.HexColor("#0d1b2e")


# ------------------------------------------------------------------- chrome
def on_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(COVER_BG)
    canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    canvas.setFillColor(B.CYAN)
    canvas.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
    canvas.restoreState()


def on_body(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(B.MUTED)
    canvas.drawString(20 * mm, 10 * mm, "BatchTwin — Business Plan & Investment Dossier")
    canvas.drawRightString(190 * mm, 10 * mm, f"{doc.page}")
    canvas.setStrokeColor(B.GRID)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 12.5 * mm, 190 * mm, 12.5 * mm)
    # thin top rule
    canvas.line(20 * mm, A4[1] - 14 * mm, 190 * mm, A4[1] - 14 * mm)
    canvas.setFont("Helvetica", 7.2)
    canvas.drawString(20 * mm, A4[1] - 12 * mm, "Laboratoires Medicka · Tunisia · 2026")
    canvas.restoreState()


class Book(BaseDocTemplate):
    """Notifies the TOC of every heading so page numbers are real."""

    def afterFlowable(self, flowable):
        if hasattr(flowable, "_toc_level"):
            self.notify("TOCEntry",
                        (flowable._toc_level, flowable._toc_text, self.page))


# --------------------------------------------------------------------- cover
def cover():
    S = B.SS
    tiles = [("1,205", "DOSSIER FIELDS DIGITALISED"),
             ("143", "AUTOMATED TESTS PASSING"),
             (f"{B.M[3]['revenue_tnd']:,.0f}", "YEAR-3 REVENUE, TND"),
             (f"{B.BE['sites_for_breakeven_on_licence_alone']}", "SITES TO BREAK EVEN")]
    tt = Table([[Paragraph(v, S["CovNum"]) for v, _ in tiles],
                [Paragraph(l, S["CovLbl"]) for _, l in tiles]],
               colWidths=[42.5 * mm] * 4)
    tt.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, 0), 0),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                            ("TOPPADDING", (0, 1), (-1, 1), 0),
                            ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#2c4666"))]))
    # The logo carries the wordmark, so the cover does not repeat it as type.
    return [Spacer(1, 44 * mm),
            B.logo_card(),
            Spacer(1, 16 * mm),
            Paragraph(B.SUBTITLE, S["CovS"]),
            Spacer(1, 11),
            Paragraph(B.STRAP, S["CovStrap"]),
            Spacer(1, 26 * mm),
            tt,
            Spacer(1, 46 * mm),
            Paragraph(B.TEAM, S["CovMeta"]),
            Paragraph(B.PARTNER, S["CovMeta"]),
            Spacer(1, 5),
            Paragraph(B.VERSION, S["CovMeta"]),
            NextPageTemplate("body"),
            PageBreak()]


def toc_page():
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("t0", fontName="Helvetica-Bold", fontSize=10, leading=17,
                       textColor=B.BLUE, spaceBefore=6),
        ParagraphStyle("t1", fontName="Helvetica", fontSize=8.8, leading=13.4,
                       textColor=B.INK2, leftIndent=11),
        ParagraphStyle("t2", fontName="Helvetica", fontSize=8.2, leading=12,
                       textColor=B.MUTED, leftIndent=24),
    ]
    # Deliberately not heading(): the contents page should not list itself.
    return [Paragraph("Contents", B.SS["H1"]),
            B.para("Page numbers are generated from the rendered document, so every entry "
                   "below points at the page it actually falls on."),
            Spacer(1, 6),
            toc,
            PageBreak()]


def story():
    s = []
    s += cover()
    s += B.front_matter()
    s += toc_page()
    s += A.ch1() + A.ch2() + A.ch3()
    s += BB.ch4() + BB.ch5() + BB.ch6() + BB.ch7() + BB.ch8() + BB.ch9()
    s += C.ch10() + C.ch11() + C.ch12() + C.ch13() + C.ch14()
    s += C.appendices()
    s += C.references()
    return s


def _render(path):
    doc = Book(str(path), pagesize=A4,
               leftMargin=20 * mm, rightMargin=20 * mm,
               topMargin=18 * mm, bottomMargin=16 * mm,
               title="BatchTwin - Business Plan & Investment Dossier",
               author="Oussama Labidi, Salem Amara, Ahmed Hammami",
               subject="Business plan, financial model and market analysis for BatchTwin")

    cov = Frame(0, 0, A4[0], A4[1], id="cov",
                leftPadding=18 * mm, rightPadding=18 * mm,
                topPadding=0, bottomPadding=0)
    body = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cov], onPage=on_cover),
        PageTemplate(id="body", frames=[body], onPage=on_body),
    ])
    # multiBuild resolves the table of contents (two passes minimum)
    doc.multiBuild(story())
    return path


def build_safely():
    """Render to a temp file, then swap it in.

    On Windows a PDF open in a viewer holds an exclusive lock, and building
    straight to the final path destroys 40 pages of work with a PermissionError
    on the very last step. Build elsewhere, then move.
    """
    import os
    import tempfile

    final = OUT / "BUSINESS_PLAN.pdf"
    tmp = Path(tempfile.gettempdir()) / f"BUSINESS_PLAN.{os.getpid()}.pdf"
    _render(tmp)
    try:
        os.replace(tmp, final)
        return final, True
    except PermissionError:
        fallback = OUT / "BUSINESS_PLAN.new.pdf"
        try:
            os.replace(tmp, fallback)
        except PermissionError:
            return tmp, False
        return fallback, False


if __name__ == "__main__":
    p, clean = build_safely()
    try:
        import fitz
        print(f"wrote {p}  ({fitz.open(str(p)).page_count} pages)")
    except Exception:
        print(f"wrote {p}")
    if not clean:
        print("NOTE: BUSINESS_PLAN.pdf was locked (open in a viewer?), so the new "
              "build was written alongside it. Close the viewer and rerun to replace it.")
