"""
Single-source generator for the BatchTwin idea submission.
Emits BOTH a Markdown file (the 'text' option) and a designed PDF from the same
content blocks, so the two never diverge.

    python docs/build_idea_doc.py
"""
from __future__ import annotations
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable, KeepTogether)

OUT = Path(__file__).resolve().parent
BLUE = colors.HexColor("#2a78d6"); INK = colors.HexColor("#1a1a19"); INK2 = colors.HexColor("#52514e")
MUTED = colors.HexColor("#898781"); GRID = colors.HexColor("#e1e0d9"); SOFT = colors.HexColor("#f3f3f0")
GOOD = colors.HexColor("#0ca30c"); TEAL = colors.HexColor("#1baf7a"); AMBER = colors.HexColor("#c98500")

TITLE = "BatchTwin — The Living Batch Record"
SUB = "Pharma-grade traceability, real cost, and carbon intelligence for SME supplement & pharma makers — natively on Odoo"
META = "Sector 3 · Industry   |   Design partner: Medicka Laboratories   |   Team leader: Oussama Labidi   ·   Members: Salem Amara, Ahmed Hammami"

# ---- content blocks (single source of truth) -------------------------------
BLOCKS = [
    {"t": "quote", "text": "Odoo tells you what <b>should</b> happen. BatchTwin captures what <b>actually</b> happens — and closes the gap in cost, quality, compliance, and carbon, automatically."},

    {"t": "h2", "text": "1. Problem statement"},
    {"t": "p", "text": "Makers of food supplements live and die by one document: the **batch record** (dossier de lot). It proves, batch by batch, what was made, from which raw materials, tested how, and released by whom — across four legally-required sections: **Production, Conditionnement (packaging), Qualité, and Libération (release)**. Our design partner, **Medicka Laboratories** (Nabeul, Tunisia — GMP-certified since 2010, ~100 staff, 309 products, two-thirds of them oral liquids), still keeps that entire record on **paper**."},
    {"t": "p", "text": "Paper batch records are slow, error-prone, and blind:"},
    {"t": "ul", "items": [
        "**Quality already costs manufacturers ~15% of revenue** (cost of poor quality). One missing signature, illegible weight, or transcription slip can put a whole batch on hold.",
        "**Release is slow.** QA reviews every page by hand; a batch can wait days to be released and sold.",
        "**Material loss is invisible.** At weighing (pesée), raw material is lost to dust and spillage — “some goes to the air, some drops.” The ERP deducts only the *theoretical* recipe quantity, so the loss never appears; it silently inflates cost and corrupts stock.",
        "**In-process quality data is thrown away.** Every 30 min an operator measures the fill of 10 bottles and writes it on paper — data that could predict an underfill *before* it happens, dying in a binder.",
        "**Energy and carbon per product are unknown.** No SME supplement maker can today state the kWh or CO2 behind one bottle.",
    ]},
    {"t": "p", "text": "Concrete example — a batch of 800 bottles of a magnesium + vitamin-B6 oral syrup (200 mL): QA cannot confirm the fill-volume checks stayed in tolerance without leafing through pages; the euros of syrup lost at dispensing never show up; and if a fill sample drifts low at 3 pm, nobody sees the trend until bottles are already underfilled and scrapped."},

    {"t": "h2", "text": "2. Our solution"},
    {"t": "p", "text": "**BatchTwin is the living batch record** — a digital layer on top of the factory's existing **Odoo** ERP that runs the batch as it actually happens (every gram, every check, every signature, every kilowatt-hour) and produces a paperless, compliant, one-click batch record."},
    {"t": "p", "text": "On the floor:"},
    {"t": "ul", "items": [
        "Every order, workstation, raw-material container, and machine carries a **QR / barcode**. The operator **scans to act** — scan the station, scan the material, confirm the weight. No typing, no wrong-material mistakes.",
        "**Device-agnostic and interruption-free.** Have a phone? Use the app. No phone, or phones kept off the floor? Use a **shared company tablet** at the station and scan the same codes. Nobody depends on a personal device, and no task is lost when someone steps out or leaves the company.",
        "**Role-by-sector, not role-per-person.** Access follows the four sectors; one person can hold several roles. The system shows each user only the tasks they may sign — and blocks the ones they may not.",
        "Every action is written to a **tamper-evident, hash-chained audit trail** and sealed with an **electronic signature**. Release is **gated**: no libération until all four sections are signed and every quality check passed.",
        "One click produces the **PDF batch record** — the paper binder, replaced.",
    ]},
    {"t": "p", "text": "**Value proposition:** pharma-grade traceability, real-time true cost, predictive quality, and per-batch carbon — at SME cost, without ripping out Odoo."},

    {"t": "h2", "text": "3. Innovation — what's different"},
    {"t": "p", "text": "Not “scan the paper into a PDF.” A unique combination:"},
    {"t": "ul", "items": [
        "**Odoo-native electronic Batch Record (eBR).** Enterprise MES/eBR are not built on Odoo — the ERP SMEs actually run. We extend Odoo, not replace it.",
        "**Live mass-balance loss reconciliation.** We capture the *real* consumed quantity (losses included) at each step and reconcile it against the theoretical bill of materials → **true cost per unit**, and invisible waste becomes a tracked KPI. Even large MES rarely close this loop.",
        "**Predictive SPC on in-process checks.** The 10-bottle fill sampling becomes a live control chart with Western Electric rules and a **drift forecast**: “trend toward underfill — spec breach in ~22 min — adjust the filler now,” before scrap is made.",
        "**Data integrity by construction.** A SHA-256 hash-chained audit trail makes every record tamper-evident — aligned with **ALCOA+ / FDA 21 CFR Part 11 / EU GMP Annex 11**. Alter one record and the chain visibly breaks.",
        "**Energy & carbon per batch, per dossier.** Low-cost IoT sensors (energy clamps, scales, temperature/vibration) meter each workstation; energy used during a batch is allocated to it and split across the four dossiers → **kWh and CO2 per unit**, a first for an SME supplement line.",
        "**Scan-to-act, device-agnostic execution.** Consumer-grade QR/barcode scanning on any phone or shared tablet brings zero-friction, error-proof capture to the floor.",
    ]},

    {"t": "h2", "text": "4. Quantified impact"},
    {"t": "p", "text": "Industry benchmarks: cost of poor quality ~**15% of revenue**; electronic batch records cut record-review effort **50–90%** (review-by-exception) and compress release from **days to hours**; AI-assisted monitoring cuts errors **20–50%**."},
    {"t": "p", "text": "Estimated impact for a typical SME line (~10 batches/week — assumptions below):"},
    {"t": "table", "head": ["Lever", "Before (paper)", "With BatchTwin", "Gain"], "rows": [
        ["QA batch-record review", "~3 h / batch", "~30 min / batch", "−~25 h / week"],
        ["Operator documentation", "~45 min / batch", "~15 min / batch", "−~5 h / week"],
        ["Documentation-error rework", "frequent, manual", "forced fields + e-sign", "~90% fewer"],
        ["Batch release lead time", "days", "hours", "faster cash + capacity"],
        ["Material loss at dispensing", "invisible", "measured & reduced", "0.5–1% of material (≈€20–45k/yr)"],
        ["Fill give-away", "~1–2% overfill", "tightened via SPC", "~1% fill material saved"],
        ["Energy per batch", "unknown", "metered & targeted", "10–15% reduction opportunity"],
    ]},
    {"t": "p", "text": "**Net:** on the order of **30 skilled hours saved per week**, **near-100% right-first-time** documentation, **release in hours not days**, direct **COGS + energy savings**, and a compliance-and-carbon record that did not exist before."},
    {"t": "small", "text": "Assumptions: ~10 batches/week; material cost ~€8k/batch; regional QA labour cost. Planning estimates, to be validated on Medickalab data."},

    {"t": "h2", "text": "5. Feasibility — the 48/72h plan"},
    {"t": "p", "text": "We are not starting from zero: a **working prototype already exists** — batch lifecycle, e-signatures, hash-chained audit trail, live mass-balance, predictive SPC, and a one-click PDF batch record, with an Odoo integration layer written to Odoo's real XML-RPC API contract. The hard core is proven, which de-risks the build."},
    {"t": "ul", "items": [
        "**0–12h — Odoo & data:** connect a real Odoo Community instance; finalize the batch / BOM / quality mapping.",
        "**12–30h — Execution app:** mobile/tablet PWA with QR/barcode scan; role-by-sector task screens for the four dossiers; offline-tolerant capture.",
        "**30–48h — IoT & carbon:** wire one live sensor (ESP32 + energy clamp / USB scale, or a phone sensor) to a workstation; allocate energy to the batch; compute kWh and CO2 per unit and per dossier.",
        "**48–72h — Polish & pitch:** cost / yield / energy / CO2 dashboards, UI refinement, PDF, and a scripted end-to-end demo.",
    ]},
    {"t": "p", "text": "**Resources:** 1 laptop, free **Odoo Community**, an **ESP32 + clamp meter or USB scale (~€20–40)** or phone sensors, and an open-source stack (Python/FastAPI, SQLite/Postgres, a PWA front-end). Total hardware under €50."},

    {"t": "h2", "text": "6. Originality — why it's memorable"},
    {"t": "ul", "items": [
        "**Pharma-grade compliance on a supplement-SME budget.** We repurpose consumer tech — a phone camera for QR, a ~€5 microcontroller + clamp meter for energy, a USB scale for mass balance — to deliver 21 CFR Part 11-style integrity that normally costs six figures.",
        "**The batch record becomes a sustainability passport.** By attaching energy and CO2 to each batch and dossier, BatchTwin already produces the provenance-and-carbon data the **EU Digital Product Passport** (under the Ecodesign for Sustainable Products Regulation) will soon require — turning a compliance chore into a future-proof asset.",
        "**Nobody is left out.** Scan-to-act, bring-your-own-device-or-use-ours: an operator with no phone is as fast as one with a phone, and no task is interrupted when someone leaves the floor.",
    ]},

    {"t": "h2", "text": "7. Target audience & use cases"},
    {"t": "p", "text": "Primary: **SME food-supplement and small-batch pharma / cosmetics manufacturers** running Odoo (or similar). **Medickalab** is our design partner."},
    {"t": "ul", "items": [
        "**Operators & packaging agents** — on the line, scanning stations and materials, confirming weights and fill checks (every batch, every shift).",
        "**QC technicians** — recording in-process checks, watching the SPC chart, catching drift.",
        "**QA / release managers** — reviewing by exception and releasing batches from the office.",
        "**Plant managers / owners** — watching cost, yield, energy and CO2 dashboards.",
    ]},
    {"t": "p", "text": "Frequency: continuous — one living record per batch, used at every step, every day."},

    {"t": "h2", "text": "8. Competitive differentiation"},
    {"t": "ul", "items": [
        "**Paper + Excel (status quo):** cheap but slow, error-prone, no real-time data, no integrity, no cost/energy visibility. We keep the low cost and remove the pain.",
        "**Enterprise MES / eBR (Tulip, MasterControl, Körber, Werum PAS-X):** powerful but **five-to-six-figure** cost, **6–18 month** rollouts, and **not Odoo-native** — overkill for an SME. We deliver the essential 20% that gives 80% of the value, in days, on Odoo.",
        "**Odoo's own Quality/MRP modules:** a solid ERP backbone, but no true GMP batch record (no e-signatures, no gated release, no mass-balance loss, no predictive SPC, no energy/CO2). We **extend** Odoo — complementary, not competing.",
    ]},
    {"t": "p", "text": "**Our position: the missing layer between paper and enterprise MES** — Odoo-native, IoT-ready, carbon-aware, at SME cost."},

    {"t": "h2", "text": "Vision — the future of the line"},
    {"t": "p", "text": "A factory where every batch carries a complete digital twin from raw material to release: self-documenting, self-costing, self-auditing, carbon-aware. The paper binder disappears; the operator just scans and works; QA releases by exception; and the owner sees, for the first time, the true cost and the true footprint of every bottle — built on the ERP the factory already owns."},
]

# ---- the pipeline diagram (drawn for PDF; mermaid for MD) -------------------
DOSSIERS = ["Production", "Conditionnement", "Qualité", "Libération"]


def md_inline(t):  # **x** -> **x** (keep), <b>x</b> -> **x**, *x* stays
    return t.replace("<b>", "**").replace("</b>", "**")


def pdf_inline(t):  # **x** -> <b>x</b>, *x* -> <i>x</i>
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    return t


def write_markdown():
    L = [f"# {TITLE}", f"### {SUB}", "", f"*{META}*", ""]
    for b in BLOCKS:
        if b["t"] == "quote":
            L += [f"> **{md_inline(b['text']).replace('**','').strip()}**", ""]
        elif b["t"] == "h2":
            L += [f"## {b['text']}", ""]
        elif b["t"] == "p":
            L += [md_inline(b["text"]), ""]
        elif b["t"] == "small":
            L += [f"_{md_inline(b['text'])}_", ""]
        elif b["t"] == "ul":
            L += [f"- {md_inline(i)}" for i in b["items"]] + [""]
        elif b["t"] == "table":
            L += ["| " + " | ".join(b["head"]) + " |",
                  "|" + "|".join(["---"] * len(b["head"])) + "|"]
            L += ["| " + " | ".join(r) + " |" for r in b["rows"]]
            L += [""]
    # architecture diagram as mermaid
    L += ["## Architecture at a glance", "",
          "```mermaid", "flowchart LR",
          "  O[Odoo OF/OC/BOM] --> S[Scan QR: station + material]",
          "  S --> P[Production] --> C[Conditionnement] --> Q[Qualite] --> L[Liberation]",
          "  IoT[IoT sensors: energie/poids/temp] --> P & C & Q",
          "  P & C & Q & L --> A[(Audit chaine par hash + Energie/CO2 par lot)]",
          "  A --> PDF[Dossier de Lot PDF + Passeport carbone]", "```", ""]
    (OUT / "BatchTwin_Idea_Document.md").write_text("\n".join(L), encoding="utf-8")


def build_pdf():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("Ttl", fontName="Helvetica-Bold", fontSize=20, textColor=INK, leading=23))
    ss.add(ParagraphStyle("Sub", fontName="Helvetica", fontSize=10.5, textColor=INK2, leading=14, spaceBefore=3))
    ss.add(ParagraphStyle("Meta", fontName="Helvetica", fontSize=8, textColor=MUTED, leading=11, spaceBefore=4))
    ss.add(ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=12.5, textColor=BLUE, spaceBefore=12, spaceAfter=5, leading=15))
    ss.add(ParagraphStyle("Body", fontName="Helvetica", fontSize=9.5, textColor=INK, leading=13.5, spaceAfter=4))
    ss.add(ParagraphStyle("Small", fontName="Helvetica-Oblique", fontSize=8, textColor=MUTED, leading=11, spaceAfter=4))
    ss.add(ParagraphStyle("Bul", fontName="Helvetica", fontSize=9.5, textColor=INK, leading=13.5, leftIndent=12, spaceAfter=3, bulletIndent=2))
    ss.add(ParagraphStyle("Quote", fontName="Helvetica-Bold", fontSize=11.5, textColor=INK, leading=15, leftIndent=8, rightIndent=8))
    ss.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=8.5, textColor=INK, leading=11))
    ss.add(ParagraphStyle("CellH", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white, leading=11))

    story = []
    story += [Paragraph(TITLE, ss["Ttl"]), Paragraph(SUB, ss["Sub"]), Paragraph(META, ss["Meta"]),
              Spacer(1, 4), HRFlowable(width="100%", color=BLUE, thickness=1.4), Spacer(1, 6)]

    for b in BLOCKS:
        if b["t"] == "quote":
            q = Table([[Paragraph(pdf_inline(b["text"]), ss["Quote"])]], colWidths=[170 * mm])
            q.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("LINEBEFORE", (0, 0), (0, -1), 3, TEAL),
                                   ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12)]))
            story += [q, Spacer(1, 4)]
        elif b["t"] == "h2":
            story += [Paragraph(b["text"], ss["H2"])]
        elif b["t"] == "p":
            story += [Paragraph(pdf_inline(b["text"]), ss["Body"])]
        elif b["t"] == "small":
            story += [Paragraph(pdf_inline(b["text"]), ss["Small"])]
        elif b["t"] == "ul":
            for it in b["items"]:
                story += [Paragraph(pdf_inline(it), ss["Bul"], bulletText="•")]
        elif b["t"] == "table":
            head = [Paragraph(h, ss["CellH"]) for h in b["head"]]
            rows = [[Paragraph(pdf_inline(c), ss["Cell"]) for c in r] for r in b["rows"]]
            t = Table([head] + rows, colWidths=[44 * mm, 38 * mm, 44 * mm, 44 * mm], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
            story += [Spacer(1, 2), t, Spacer(1, 4)]

    # ---- architecture diagram --------------------------------------------
    story += [Paragraph("Architecture at a glance", ss["H2"])]
    top = Table([[Paragraph("<b>Odoo</b><br/>OF / OC / BOM", ss["Cell"]),
                  Paragraph("→", ss["Cell"]),
                  Paragraph("<b>Scan QR</b><br/>station + material", ss["Cell"])]],
                colWidths=[45 * mm, 8 * mm, 45 * mm])
    top.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.6, BLUE), ("BOX", (2, 0), (2, 0), 0.6, TEAL),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "CENTER"),
                             ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    cells, cw = [], 40 * mm
    for i, d in enumerate(DOSSIERS):
        cells.append(Paragraph(f"<b>{i+1}. {d}</b>", ss["Cell"]))
        if i < 3:
            cells.append(Paragraph("→", ss["Cell"]))
    flow = Table([cells], colWidths=[cw, 6 * mm] * 3 + [cw])
    flow.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef4fc")),
                              ("BOX", (0, 0), (0, 0), 0.6, BLUE), ("BOX", (2, 0), (2, 0), 0.6, BLUE),
                              ("BOX", (4, 0), (4, 0), 0.6, BLUE), ("BOX", (6, 0), (6, 0), 0.6, GOOD),
                              ("ALIGN", (1, 0), (1, 0), "CENTER"), ("ALIGN", (3, 0), (3, 0), "CENTER"),
                              ("ALIGN", (5, 0), (5, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    band = Table([[Paragraph("<b>IoT sensors</b> (energie / poids / temperature) feed every stage &nbsp;&bull;&nbsp; "
                             "all actions → <b>hash-chained audit + energy/CO2 per lot</b> → "
                             "<b>PDF batch record + carbon passport</b>", ss["Cell"])]], colWidths=[170 * mm])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                              ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                              ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    story += [KeepTogether([top, Spacer(1, 4), flow, Spacer(1, 4), band])]

    buf = OUT / "BatchTwin_Idea_Document.pdf"
    doc = BaseDocTemplate(str(buf), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=16 * mm, bottomMargin=15 * mm, title="BatchTwin - Idea Document")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="m")
    doc.addPageTemplates([PageTemplate(id="t", frames=[frame], onPage=_foot)])
    doc.build(story)


def _foot(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7); canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 9 * mm, "BatchTwin — idea submission — Sector 3 Industry")
    canvas.drawRightString(190 * mm, 9 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(GRID); canvas.line(20 * mm, 11 * mm, 190 * mm, 11 * mm)
    canvas.restoreState()


if __name__ == "__main__":
    write_markdown()
    build_pdf()
    print("wrote BatchTwin_Idea_Document.md and .pdf in", OUT)
