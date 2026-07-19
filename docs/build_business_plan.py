"""
Generator for BUSINESS_PLAN.pdf -- the BatchTwin business plan and investment
dossier.

Every financial figure in the output is imported from finance_model.py and
formatted here. Nothing is typed twice, so the document cannot drift from the
model, and the model cannot drift from the code it measures.

    python docs/build_business_plan.py
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, Image,
                                KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

import finance_model as FM

OUT = Path(__file__).resolve().parent

# ------------------------------------------------------------------ palette
INK    = colors.HexColor("#12161f")
INK2   = colors.HexColor("#3d4351")
MUTED  = colors.HexColor("#7b8194")
BLUE   = colors.HexColor("#1c4e80")
CYAN   = colors.HexColor("#1b9aaa")
GRID   = colors.HexColor("#dfe3ea")
SOFT   = colors.HexColor("#f4f6f9")
GOOD   = colors.HexColor("#1f8a4c")
AMBER  = colors.HexColor("#b87500")
RED    = colors.HexColor("#b3261e")
PAPER  = colors.HexColor("#ffffff")

TAG_COLOR = {"SOURCED": BLUE, "MEASURED": GOOD, "DERIVED": CYAN, "ASSUMPTION": AMBER,
             # French edition uses the same four categories, same colours.
             "SOURCÉ": BLUE, "MESURÉ": GOOD, "CALCULÉ": CYAN, "HYPOTHÈSE": AMBER}

TITLE = "BatchTwin"
SUBTITLE = "Business Plan &amp; Investment Dossier"
STRAP = ("The paperless GMP batch record for SME manufacturers &mdash; "
         "built on the Odoo they already run")
TEAM = ("Oussama Labidi (team leader) &nbsp;&middot;&nbsp; "
        "Salem Amara &nbsp;&middot;&nbsp; Ahmed Hammami")
PARTNER = "Design partner: Laboratoires Medicka &mdash; Nabeul, Tunisia"
VERSION = "Version 1.0 &middot; 19 July 2026"

M = FM.build_model()
UE = FM.unit_economics()
BE = FM.breakeven(M)
SENS = FM.sensitivity(M)
MK = FM.market(M)
SVC = FM.services_table()


# Set to "fr" by the French builder before the story is generated. French uses a
# non-breaking space as thousands separator and a comma as decimal mark; leaving
# "170,674 TND" in a French document reads as an unedited translation.
LOCALE = "en"

NBSP = " "


def money(v, unit="TND") -> str:
    s = f"{v:,.0f}"
    if LOCALE == "fr":
        s = s.replace(",", NBSP)
    return f"{s} {unit}"


def num(v, dec=0) -> str:
    """A bare number, localised."""
    s = f"{v:,.{dec}f}"
    if LOCALE == "fr":
        s = s.replace(",", "\x00").replace(".", ",").replace("\x00", NBSP)
    return s


def pc(v, dec=1, sign=False) -> str:
    """A percentage, localised, with the space French typography requires."""
    plus = "+" if sign and v >= 0 else ""
    return f"{plus}{num(v, dec)}{NBSP}%"


# ------------------------------------------------------------------- styles
def styles():
    ss = getSampleStyleSheet()
    S = {}
    S["Body"] = ParagraphStyle("Body", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=9.3, leading=13.6, textColor=INK2,
                               spaceAfter=6, alignment=4)
    S["H1"] = ParagraphStyle("H1", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=19, leading=23, textColor=BLUE,
                             spaceBefore=0, spaceAfter=3)
    S["H2"] = ParagraphStyle("H2", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=12.4, leading=16, textColor=INK,
                             spaceBefore=13, spaceAfter=5)
    S["H3"] = ParagraphStyle("H3", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=10.2, leading=14, textColor=BLUE,
                             spaceBefore=10, spaceAfter=3)
    S["Small"] = ParagraphStyle("Small", parent=S["Body"], fontSize=7.9,
                                leading=11, textColor=MUTED)
    S["Bul"] = ParagraphStyle("Bul", parent=S["Body"], leftIndent=11,
                              bulletIndent=2, spaceAfter=3)
    S["Cell"] = ParagraphStyle("Cell", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=8.1, leading=11, textColor=INK2)
    S["CellB"] = ParagraphStyle("CellB", parent=S["Cell"], fontName="Helvetica-Bold",
                                textColor=INK)
    S["CellH"] = ParagraphStyle("CellH", parent=S["Cell"], fontName="Helvetica-Bold",
                                textColor=PAPER, fontSize=8.1)
    S["CellR"] = ParagraphStyle("CellR", parent=S["Cell"], alignment=TA_RIGHT)
    S["CellRB"] = ParagraphStyle("CellRB", parent=S["CellB"], alignment=TA_RIGHT)
    S["Quote"] = ParagraphStyle("Quote", parent=S["Body"], fontSize=10.4,
                                leading=15.5, textColor=BLUE, leftIndent=9,
                                fontName="Helvetica-Oblique", spaceBefore=4,
                                spaceAfter=8)
    S["CalloutT"] = ParagraphStyle("CalloutT", parent=S["Body"],
                                   fontName="Helvetica-Bold", fontSize=9.1,
                                   textColor=INK, spaceAfter=3)
    S["Code"] = ParagraphStyle("Code", parent=S["Body"], fontName="Courier",
                               fontSize=7.9, leading=11, textColor=INK,
                               leftIndent=7, spaceAfter=5)
    # cover
    S["CovT"] = ParagraphStyle("CovT", parent=ss["Normal"], fontName="Helvetica-Bold",
                               fontSize=54, leading=58, textColor=PAPER,
                               alignment=TA_CENTER)
    S["CovS"] = ParagraphStyle("CovS", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=17, leading=23, textColor=colors.HexColor("#a9c7e8"),
                               alignment=TA_CENTER)
    S["CovStrap"] = ParagraphStyle("CovStrap", parent=ss["Normal"], fontName="Helvetica",
                                   fontSize=10.4, leading=16, textColor=colors.HexColor("#8fa6c2"),
                                   alignment=TA_CENTER)
    S["CovMeta"] = ParagraphStyle("CovMeta", parent=ss["Normal"], fontName="Helvetica",
                                  fontSize=9, leading=15, textColor=colors.HexColor("#8fa6c2"),
                                  alignment=TA_CENTER)
    S["CovNum"] = ParagraphStyle("CovNum", parent=ss["Normal"], fontName="Helvetica-Bold",
                                 fontSize=25, leading=28, textColor=PAPER,
                                 alignment=TA_CENTER)
    S["CovLbl"] = ParagraphStyle("CovLbl", parent=ss["Normal"], fontName="Helvetica",
                                 fontSize=6.6, leading=10, textColor=colors.HexColor("#8fa6c2"),
                                 alignment=TA_CENTER)
    return S


SS = styles()


def inl(t: str) -> str:
    """**bold** -> <b>, *italic* -> <i>, `code` -> monospace, [TAG] -> coloured."""
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\*\w])\*([^*]+?)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r'<font face="Courier" size="8">\1</font>', t)
    for tag, col in TAG_COLOR.items():
        t = t.replace(f"[{tag}]",
                      f'<font color="#{col.hexval()[2:]}" size="7"><b>[{tag}]</b></font>')
    return t


# ------------------------------------------------------------------ flowables
def para(t, s="Body"):
    return Paragraph(inl(t), SS[s])


def heading(text, level):
    st = {0: "H1", 1: "H2", 2: "H3"}[level]
    p = Paragraph(inl(text), SS[st])
    p._toc_level = level
    p._toc_text = re.sub(r"<[^>]+>", "", inl(text))
    return p


def table(head, rows, widths, align_right=(), bold_rows=()):
    data = [[Paragraph(inl(h), SS["CellH"]) for h in head]]
    for i, r in enumerate(rows):
        line = []
        for j, c in enumerate(r):
            if i in bold_rows:
                st = "CellRB" if j in align_right else "CellB"
            else:
                st = "CellR" if j in align_right else "Cell"
            line.append(Paragraph(inl(str(c)), SS[st]))
        data.append(line)
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), BLUE),
             ("GRID", (0, 0), (-1, -1), 0.4, GRID),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAPER, SOFT]),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 4.5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 5),
             ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    for br in bold_rows:
        style.append(("BACKGROUND", (0, br + 1), (-1, br + 1), colors.HexColor("#e8eff7")))
    t.setStyle(TableStyle(style))
    return t


def callout(title, text, tone="info"):
    col = {"info": BLUE, "good": GOOD, "warn": AMBER, "bad": RED}[tone]
    bg = {"info": colors.HexColor("#eef4fb"), "good": colors.HexColor("#eaf6ee"),
          "warn": colors.HexColor("#fdf5e6"), "bad": colors.HexColor("#fbeceb")}[tone]
    inner = [Paragraph(inl(title), SS["CalloutT"]), Paragraph(inl(text), SS["Body"])]
    t = Table([[inner]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LINEBEFORE", (0, 0), (0, -1), 2.4, col),
                           ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 9)]))
    return t


def kpibox(title, rows):
    """rows: (metric, value, tag, where-it-comes-from)"""
    head = ["KPI", "Value", "Evidence", "Where it comes from"]
    t = table(head, [[a, b, f"[{c}]", d] for a, b, c, d in rows],
              [46 * mm, 27 * mm, 24 * mm, 73 * mm], align_right=(1,))
    return KeepTogether([Paragraph(inl(f"<b>{title}</b>"), SS["H3"]), t, Spacer(1, 3)])


def srcbox(items):
    body = " &nbsp;&bull;&nbsp; ".join(items)
    t = Table([[Paragraph(inl(f"<b>Sources</b> &nbsp; {body}"), SS["Small"])]],
              colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT),
                           ("LINEABOVE", (0, 0), (-1, 0), 0.7, GRID),
                           ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    return t


def bullets(items):
    return [Paragraph(inl(i), SS["Bul"], bulletText="•") for i in items]


def rule():
    return HRFlowable(width="100%", thickness=0.6, color=GRID,
                      spaceBefore=7, spaceAfter=7)


LOGO = Path(__file__).resolve().parent.parent / "logo" / "batchtwin_trimmed.png"


def logo_card(width_mm=96.0):
    """The logo on a white card.

    The mark is dark navy on white, so it cannot sit directly on the dark cover
    without disappearing. A white card keeps the brand colours exact and reads
    as a deliberate choice rather than a transparency accident.
    """
    if not LOGO.exists():
        return Spacer(1, 0)
    ir = ImageReader(str(LOGO))
    iw, ih = ir.getSize()
    w = width_mm * mm
    img = Image(str(LOGO), width=w, height=w * ih / iw)
    card = Table([[img]], colWidths=[w + 16 * mm])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    holder = Table([[card]], colWidths=[170 * mm])
    holder.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return holder


# ============================================================== FRONT MATTER
def front_matter():
    s = [heading("How to read the numbers in this document", 0),
         para("A business plan is worth exactly as much as the provenance of the figures "
              "inside it. Most plans blur three very different things &mdash; what was "
              "measured, what somebody else published, and what the authors hope. This one "
              "keeps them apart with a tag on every material number."),
         Spacer(1, 4),
         table(["Tag", "What it means", "Example in this document"],
               [["[MEASURED]", "Computed by code in the BatchTwin repository, against "
                 "Medicka's real files. Reproducible with a command listed in Appendix B.",
                 "1,205 dossier fields digitalised"],
                ["[SOURCED]", "Published third-party figure, cited in the References chapter.",
                 "55 licensed pharmaceutical manufacturers in Tunisia"],
                ["[DERIVED]", "Arithmetic on measured or sourced inputs, with the arithmetic "
                 "shown so a reader can check it or disagree with it.",
                 "714 TND consultant day rate"],
                ["[ASSUMPTION]", "Our estimate. Not validated. Every one is collected in "
                 "Appendix D so they can be attacked as a group.",
                 "10 new customers in year 3"]],
               [25 * mm, 73 * mm, 72 * mm]),
         Spacer(1, 8),
         callout("The rule behind every number here",
                 "No figure appears in this document unless it is measured, cited, or derived "
                 "in front of the reader. Where we do not have a number &mdash; and there are "
                 "several such places, including the size of our own addressable market "
                 "&mdash; the document says so and states what would produce it. A confident "
                 "number with no origin is the fastest way to lose a reader who checks "
                 "arithmetic.", "info"),
         Spacer(1, 8),
         para(f"**Currency.** All figures are in Tunisian dinar (TND). The product is sold in "
              f"Tunisia and the cost base is Tunisian; quoting a Tunisian QA Director in euro "
              f"starts a conversation about the exchange rate instead of about the product. "
              f"Where a euro figure is the original measurement it is converted at "
              f"**1 EUR = {FM.EUR_TND} TND** [SOURCED] Ref [19] and both are shown."),
         para("**Reproducibility.** Every financial figure in this document is produced by "
              "`docs/finance_model.py` and imported by the generator; none is typed twice, so "
              "the document cannot drift from the model and the model cannot drift from the "
              "code it measures. Running `python docs/finance_model.py` prints the whole "
              "model. Appendix B maps each measured claim to the command that reproduces it."),
         rule(),
         heading("Acronyms", 1),
         Spacer(1, 3)]
    acr = [
        ("ALCOA+", "Attributable, Legible, Contemporaneous, Original, Accurate &mdash; plus "
                   "Complete, Consistent, Enduring, Available. The data-integrity standard."),
        ("ARPA", "Average revenue per account"),
        ("ARR", "Annual recurring revenue"),
        ("BOM", "Bill of materials"),
        ("CAPA", "Corrective and preventive action"),
        ("DCOI / DCOII", "Dossier de conditionnement primaire / secondaire"),
        ("DCT", "Dossier de contr&ocirc;le de la qualit&eacute;"),
        ("DFA", "Dossier de fabrication"),
        ("eBR", "Electronic batch record"),
        ("ERP", "Enterprise resource planning"),
        ("FEFO", "First expired, first out"),
        ("GMP", "Good manufacturing practice"),
        ("IQ / OQ / PQ", "Installation / operational / performance qualification"),
        ("MES", "Manufacturing execution system"),
        ("OLS", "Ordinary least squares"),
        ("Part 11", "US 21 CFR Part 11 &mdash; electronic records and electronic signatures"),
        ("SPC", "Statistical process control"),
        ("TAM / SAM / SOM", "Total addressable / serviceable available / serviceable "
                            "obtainable market"),
        ("TND", "Tunisian dinar"),
        ("URS", "User requirement specification"),
    ]
    s += [table(["Acronym", "Meaning"], [[a, b] for a, b in acr], [30 * mm, 140 * mm]),
          PageBreak()]
    return s
