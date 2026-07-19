"""
Point d'entrée : génère BUSINESS_PLAN_FR.pdf.

    python docs/bp_build_fr.py

Réutilise toute la machinerie de bp_build.py (gabarits de page, sommaire,
numérotation) et ne remplace que le contenu et les libellés de couverture.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Frame, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

import build_business_plan as B

# Must be set before any content module formats a figure: money(), num() and pc()
# read this at call time, which is what makes "170 674 TND" and "31,4 %" come out
# of the same helpers that produce "170,674 TND" and "31.4%" for the English edition.
B.LOCALE = "fr"

import bp_build as EN  # noqa: E402  (page templates and the Book doc class)
import bp_fr_a as A  # noqa: E402
import bp_fr_b as BB  # noqa: E402
import bp_fr_c as C  # noqa: E402

OUT = Path(__file__).resolve().parent

SUBTITLE_FR = "Plan d'affaires et dossier d'investissement"
STRAP_FR = ("Le dossier de lot BPF sans papier pour les fabricants PME &mdash; "
            "bâti sur l'Odoo qu'ils exploitent déjà")
TEAM_FR = ("Oussama Labidi (chef d'équipe) &nbsp;&middot;&nbsp; "
           "Salem Amara &nbsp;&middot;&nbsp; Ahmed Hammami")
PARTNER_FR = "Partenaire de conception : Laboratoires Medicka &mdash; Nabeul, Tunisie"
VERSION_FR = "Version 1.0 &middot; 19 juillet 2026"


def cover_fr():
    S = B.SS
    tiles = [("1 205", "CHAMPS DE DOSSIER NUMÉRISÉS"),
             ("143", "TESTS AUTOMATISÉS AU VERT"),
             (B.num(B.M[3]["revenue_tnd"]), "CA ANNÉE 3, TND"),
             (B.num(B.BE["sites_for_breakeven_on_licence_alone"], 1),
              "SITES POUR L'ÉQUILIBRE")]
    tt = Table([[Paragraph(v, S["CovNum"]) for v, _ in tiles],
                [Paragraph(l, S["CovLbl"]) for _, l in tiles]],
               colWidths=[42.5 * mm] * 4)
    tt.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, 0), 0),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                            ("TOPPADDING", (0, 1), (-1, 1), 0),
                            ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#2c4666"))]))
    return [Spacer(1, 44 * mm),
            B.logo_card(),
            Spacer(1, 16 * mm),
            Paragraph(SUBTITLE_FR, S["CovS"]),
            Spacer(1, 11),
            Paragraph(STRAP_FR, S["CovStrap"]),
            Spacer(1, 26 * mm),
            tt,
            Spacer(1, 46 * mm),
            Paragraph(TEAM_FR, S["CovMeta"]),
            Paragraph(PARTNER_FR, S["CovMeta"]),
            Spacer(1, 5),
            Paragraph(VERSION_FR, S["CovMeta"]),
            NextPageTemplate("body"),
            PageBreak()]


def toc_fr():
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("t0", fontName="Helvetica-Bold", fontSize=10, leading=17,
                       textColor=B.BLUE, spaceBefore=6),
        ParagraphStyle("t1", fontName="Helvetica", fontSize=8.8, leading=13.4,
                       textColor=B.INK2, leftIndent=11),
        ParagraphStyle("t2", fontName="Helvetica", fontSize=8.2, leading=12,
                       textColor=B.MUTED, leftIndent=24),
    ]
    return [Paragraph("Sommaire", B.SS["H1"]),
            B.para("Les numéros de page sont générés à partir du document rendu : chaque "
                   "entrée pointe donc vers la page où elle se trouve réellement."),
            Spacer(1, 6), toc, PageBreak()]


def on_body_fr(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(B.MUTED)
    canvas.drawString(20 * mm, 10 * mm,
                      "BatchTwin — Plan d'affaires et dossier d'investissement")
    canvas.drawRightString(190 * mm, 10 * mm, f"{doc.page}")
    canvas.setStrokeColor(B.GRID)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 12.5 * mm, 190 * mm, 12.5 * mm)
    canvas.line(20 * mm, A4[1] - 14 * mm, 190 * mm, A4[1] - 14 * mm)
    canvas.drawString(20 * mm, A4[1] - 12 * mm, "Laboratoires Medicka · Tunisie · 2026")
    canvas.restoreState()


def story():
    s = []
    s += cover_fr()
    s += A.front_matter_fr()
    s += toc_fr()
    s += A.ch1() + A.ch2() + A.ch3()
    s += BB.ch4() + BB.ch5() + BB.ch6() + BB.ch7() + BB.ch8() + BB.ch9()
    s += C.ch10() + C.ch11() + C.ch12() + C.ch13() + C.ch14()
    s += C.appendices()
    s += C.references()
    return s


def _render(path):
    doc = EN.Book(str(path), pagesize=A4,
                  leftMargin=20 * mm, rightMargin=20 * mm,
                  topMargin=18 * mm, bottomMargin=16 * mm,
                  title="BatchTwin - Plan d'affaires et dossier d'investissement",
                  author="Oussama Labidi, Salem Amara, Ahmed Hammami",
                  subject="Plan d'affaires, modèle financier et analyse de marché de BatchTwin")
    cov = Frame(0, 0, A4[0], A4[1], id="cov",
                leftPadding=18 * mm, rightPadding=18 * mm, topPadding=0, bottomPadding=0)
    body = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cov], onPage=EN.on_cover),
        PageTemplate(id="body", frames=[body], onPage=on_body_fr),
    ])
    doc.multiBuild(story())
    return path


def build_safely():
    import os
    import tempfile
    final = OUT / "BUSINESS_PLAN_FR.pdf"
    tmp = Path(tempfile.gettempdir()) / f"BUSINESS_PLAN_FR.{os.getpid()}.pdf"
    _render(tmp)
    try:
        os.replace(tmp, final)
        return final, True
    except PermissionError:
        fallback = OUT / "BUSINESS_PLAN_FR.new.pdf"
        try:
            os.replace(tmp, fallback)
        except PermissionError:
            return tmp, False
        return fallback, False


if __name__ == "__main__":
    p, clean = build_safely()
    try:
        import fitz
        print(f"écrit {p}  ({fitz.open(str(p)).page_count} pages)")
    except Exception:
        print(f"écrit {p}")
    if not clean:
        print("NOTE : BUSINESS_PLAN_FR.pdf était verrouillé (ouvert dans un lecteur ?). "
              "Fermez-le et relancez pour le remplacer.")
