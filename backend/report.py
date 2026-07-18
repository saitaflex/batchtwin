"""
Dossier de Lot -> PDF.

Generates the formal, GMP-style batch record that used to be a paper binder:
line clearance, pesee/bilan matiere, in-process SPC, the four role signatures,
and a tamper-evidence statement backed by the hash-chained audit trail.

The point for the pitch: this document is produced in one click from the SAME
records the operators signed - not re-typed, not reconciled by hand.
"""
from __future__ import annotations
import io
import hashlib
import datetime as _dt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)

from . import store, analytics

# --- palette (mirrors the dashboard) ---
BLUE = colors.HexColor("#2a78d6")
INK = colors.HexColor("#1a1a19")
INK2 = colors.HexColor("#52514e")
MUTED = colors.HexColor("#898781")
GRID = colors.HexColor("#e1e0d9")
GOOD = colors.HexColor("#0ca30c")
CRIT = colors.HexColor("#d03b3b")
SOFT = colors.HexColor("#f3f3f0")
GOODBG = colors.HexColor("#e6f4e6")
CRITBG = colors.HexColor("#fbe6e6")

STAGE_LABEL = {"fabrication": "Fabrication (DFA)",
               "cond_primaire": "Conditionnement Primaire (DCOI)",
               "cond_secondaire": "Conditionnement Secondaire (DCOII)",
               "qualite": "Controle Qualite (DCT)", "liberation": "Liberation"}
SEVERITY_LABEL = {"minor": "Mineure", "major": "Majeure", "critical": "Critique"}
DISPO_LABEL = {"accept": "Accepte en l'etat", "rework": "Retraitement", "reject": "Rejet"}
ROLE_LABEL = {"r_prod": "R. PROD - Responsable Production",
              "r_cq":   "R. CQ - Responsable Controle Qualite",
              "smq":    "SMQ - Assurance Qualite",
              "prt":    "PRT - Pharmacien Responsable Technique"}
CHANGE_KIND = {"add": "Ajout matiere", "amend": "Modification quantite", "remove": "Retrait matiere"}
CHANGE_STATUS = {"approved": "APPROUVE", "pending": "EN ATTENTE AQ", "rejected": "REFUSE"}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=11, textColor=BLUE,
                          spaceBefore=10, spaceAfter=5, leading=13))
    ss.add(ParagraphStyle("Small", fontName="Helvetica", fontSize=8, textColor=INK2, leading=11))
    ss.add(ParagraphStyle("Mono", fontName="Courier", fontSize=7, textColor=MUTED, leading=9))
    ss.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=8, textColor=INK, leading=10))
    ss.add(ParagraphStyle("CellR", parent=ss["Cell"], alignment=TA_RIGHT))
    ss.add(ParagraphStyle("Title2", fontName="Helvetica-Bold", fontSize=18, textColor=INK, leading=20))
    return ss


def _euro(v):
    return "-" if v is None else f"{v:,.2f} EUR".replace(",", " ")


def _fmt(v, d=2):
    return "-" if v is None else f"{v:,.{d}f}".replace(",", " ")


def build_batch_pdf(batch_id: int) -> tuple[bytes, str]:
    b = store.get_batch(batch_id)
    if not b:
        raise ValueError("batch not found")
    mb = analytics.mass_balance(b["dispense"])
    kpis = analytics.batch_kpis(b, mb, b.get("good_units"))
    lo = (b["target_fill_g"] or 0) - (b["fill_tol_g"] or 0)
    hi = (b["target_fill_g"] or 0) + (b["fill_tol_g"] or 0)
    spc = analytics.spc(b["qc"], b["target_fill_g"], lo, hi)
    energy = analytics.energy_summary(b.get("energy", []), b.get("good_units"))
    audit = store.get_audit(batch_id)
    integ = store.verify_chain()
    sig_by_stage = {s["stage"]: s for s in b["signatures"]}
    ss = _styles()
    gen_at = _dt.datetime.now().astimezone().isoformat(timespec="seconds")

    doc_hash = hashlib.sha256(
        f"{b['lot_name']}|{integ.get('head','')}|{len(audit)}|{gen_at}".encode()
    ).hexdigest()

    story = []
    P = lambda t, s="Cell": Paragraph(t, ss[s])

    # ---- header block ------------------------------------------------------
    released = b["state"] == "released"
    parallel = b.get("run_mode") == "parallel"
    # During a parallel run this document must never be mistaken for the legal
    # record -- the paper dossier still is. Say so on the stamp, not in a footnote.
    stamp_text = ("QUALIFICATION" if parallel
                  else "LOT LIBERE" if released else "EN COURS - NON LIBERE")
    stamp_bg = (colors.HexColor("#6C63FF") if parallel
                else GOOD if released else colors.HexColor("#c98500"))
    stamp = Table([[Paragraph(
        stamp_text,
        ParagraphStyle("stamp", fontName="Helvetica-Bold", fontSize=11,
                       textColor=colors.white, alignment=TA_CENTER))]],
        colWidths=[45 * mm])
    stamp.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), stamp_bg),
                               ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                               ("ROUNDEDCORNERS", [4, 4, 4, 4])]))
    head = Table([[
        [Paragraph("DOSSIER DE LOT", ss["Title2"]),
         Paragraph("BatchTwin - le dossier de lot vivant &bull; Medickalab", ss["Small"])],
        stamp,
    ]], colWidths=[120 * mm, 50 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story += [head, Spacer(1, 4), HRFlowable(width="100%", color=BLUE, thickness=1.4), Spacer(1, 8)]

    if parallel:
        banner = Table([[Paragraph(
            "<b>DOUBLE SAISIE — CE DOCUMENT NE FAIT PAS FOI.</b><br/>"
            f'Le dossier de lot papier <b>{b.get("paper_ref") or "-"}</b> reste '
            "l'enregistrement legal de ce lot. Ce document sert a qualifier "
            "BatchTwin par comparaison, conformement au plan de migration.",
            ss["Cell"])]], colWidths=[170 * mm])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eeecff")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#6C63FF")),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 9)]))
        story += [banner, Spacer(1, 8)]

    # ---- metadata ----------------------------------------------------------
    meta = [
        ["Numero de lot", b["lot_name"], "Produit", b["product"]],
        ["Ordre fabrication", b["of_ref"] or "-", "Ordre conditionnement", b["oc_ref"] or "-"],
        ["Commande client", b["sale_order"] or "-", "Quantite cible", f'{b["qty_target"]} unites'],
        ["Contenance cible", f'{_fmt(b["target_fill_g"],0)} {b.get("fill_unit") or "mL"} (+/- {_fmt(b["fill_tol_g"],0)} {b.get("fill_unit") or "mL"})',
         "Cree le", b["created_at"][:16].replace("T", " ")],
        ["Date de fabrication", b.get("mfg_date") or "-", "Date de peremption", b.get("expiry_date") or "-"],
    ]
    mt = Table([[P(f"<b>{r[0]}</b>", "Small"), P(r[1]), P(f"<b>{r[2]}</b>", "Small"), P(r[3])] for r in meta],
               colWidths=[35 * mm, 55 * mm, 38 * mm, 42 * mm])
    mt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
                            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
    story += [mt, Spacer(1, 6)]

    # ---- KPI strip ---------------------------------------------------------
    kpi_cells = [
        ("Cout matiere reel / unite", _euro(kpis["true_unit_material_cost"])),
        ("Rendement lot", "-" if kpis["yield_pct"] is None else f'{kpis["yield_pct"]:.1f} %'),
        ("Perte matiere (hors Odoo)", _euro(mb["loss_cost"])),
        ("Ecart vs theorique Odoo", _euro(mb["cost_gap"])),
    ]
    kt = Table([[Paragraph(f'<font size=7 color="#898781">{k}</font><br/><font size=13><b>{v}</b></font>', ss["Cell"])
                 for k, v in kpi_cells]], colWidths=[42.5 * mm] * 4)
    kt.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, GRID), ("INNERGRID", (0, 0), (-1, -1), 0.5, GRID),
                            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                            ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    story += [kt, Spacer(1, 4)]

    # ---- 1. Fabrication ----------------------------------------------------
    story += [P("1. Fabrication - Vide de ligne", "H")]
    clr_rows = [[P("<b>Controle</b>", "Small"), P("<b>Resultat</b>", "Small")]]
    for c in b["checklist"]:
        ok = c["ok"]
        res = "Conforme" if ok == 1 else ("NON CONFORME -> " + (c["escalated_to"] or "responsable") if ok == 0 else "non verifie")
        col = GOOD if ok == 1 else CRIT if ok == 0 else MUTED
        clr_rows.append([P(c["label"]), Paragraph(res, ParagraphStyle("r", parent=ss["Cell"], textColor=col))])
    clr = Table(clr_rows, colWidths=[120 * mm, 50 * mm])
    clr.setStyle(_tbl_style())
    story += [clr, Spacer(1, 6), P("1. Fabrication - Pesee &amp; bilan matiere", "H")]

    disp_rows = [[P("<b>Matiere premiere</b>", "Small"), P("<b>Unite</b>", "Small"),
                  P("<b>Theorique</b>", "Small"), P("<b>Pese</b>", "Small"),
                  P("<b>Perte</b>", "Small"), P("<b>Perte %</b>", "Small"), P("<b>Cout</b>", "Small")]]
    for i, r in enumerate(b["dispense"]):
        l = mb["lines"][i]
        mat = (f'{r["material"]}<br/><font size=6 color="#898781">'
               f'{r.get("supplier") or ""} · lot {r.get("rm_lot") or ""} · per. {r.get("rm_expiry") or ""}</font>')
        disp_rows.append([P(mat), P(r["unit"], "CellR"), P(_fmt(l["target"], 2), "CellR"),
                          P(_fmt(l["dispensed"], 2), "CellR"), P(_fmt(l["loss"], 3), "CellR"),
                          P("-" if l["loss_pct"] is None else f'{l["loss_pct"]:.2f}%', "CellR"),
                          P(_euro(l["line_cost"]), "CellR")])
    disp_rows.append([P("<b>Total consomme reel</b>", "Cell"), P(""), P(""), P(""), P(""),
                      P(f'<b>{_euro(mb["loss_cost"])} perte</b>', "CellR"),
                      P(f'<b>{_euro(mb["real_cost"])}</b>', "CellR")])
    disp = Table(disp_rows, colWidths=[52 * mm, 16 * mm, 22 * mm, 22 * mm, 20 * mm, 18 * mm, 20 * mm])
    disp.setStyle(_tbl_style(total_row=True))
    story += [disp, Spacer(1, 4)]

    # ---- 1bis. Change control (formula modifications) ----------------------
    changes = b.get("changes") or []
    if changes:
        story += [P("1. Fabrication - Controle des changements de formule", "H")]
        ch_rows = [[P("<b>Type</b>", "Small"), P("<b>Matiere</b>", "Small"),
                    P("<b>Avant</b>", "Small"), P("<b>Apres</b>", "Small"),
                    P("<b>Motif</b>", "Small"), P("<b>Demande / Approuve par</b>", "Small"),
                    P("<b>Statut</b>", "Small")]]
        for ch in changes:
            st = ch["status"]
            col = GOOD if st == "approved" else CRIT if st == "rejected" else colors.HexColor("#c98500")
            who = (f'{ch["requested_by"]} ({ROLE_LABEL.get(ch["requested_role"], ch["requested_role"])})'
                   f'<br/><font size=6 color="#898781">'
                   + (f'AQ: {ch["decided_by"]} - {(ch["decided_at"] or "")[:10]}' if ch["decided_by"]
                      else "en attente d'approbation") + '</font>')
            lbl = CHANGE_KIND.get(ch["kind"], ch["kind"])
            if ch["route"] == "minor":
                lbl += f'<br/><font size=6 color="#898781">ajustement en plage</font>'
            ch_rows.append([
                P(lbl), P(ch["material"]),
                P("-" if ch["old_qty"] is None else _fmt(ch["old_qty"], 2), "CellR"),
                P("-" if ch["new_qty"] is None else _fmt(ch["new_qty"], 2), "CellR"),
                P(ch["reason"] or "-"), P(who),
                Paragraph(CHANGE_STATUS.get(st, st),
                          ParagraphStyle("cs", parent=ss["Cell"], textColor=col))])
        cht = Table(ch_rows, colWidths=[24 * mm, 32 * mm, 15 * mm, 15 * mm, 30 * mm, 32 * mm, 22 * mm])
        cht.setStyle(_tbl_style())
        story += [cht, Spacer(1, 3), Paragraph(
            "Toute modification de la formule est tracee, motivee et nominative. Un ecart superieur "
            "a +/-5 % ou tout ajout/retrait de matiere exige l'approbation de l'Assurance Qualite (SMQ/PRT) "
            "avant liberation.", ss["Small"]), Spacer(1, 4)]

    story += [_sig_block(b, "fabrication", sig_by_stage, ss)]

    # ---- 2. Conditionnement primaire (DCOI) & secondaire (DCOII) -----------
    story += [P("2. Conditionnement Primaire (DCOI)", "H")]
    cond = Table([[P(f'Unites bonnes produites : <b>{kpis["good_units"] if kpis["good_units"] is not None else "-"}</b> '
                     f'/ {kpis["target_units"]} cibles &nbsp;&nbsp;&bull;&nbsp;&nbsp; '
                     f'Rendement : <b>{"-" if kpis["yield_pct"] is None else f"{kpis["yield_pct"]:.1f} %"}</b>')]],
                 colWidths=[170 * mm])
    cond.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                              ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                              ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    story += [cond, Spacer(1, 4),
              _packaging_table(b, "cond_primaire", ss),
              _sig_block(b, "cond_primaire", sig_by_stage, ss)]

    story += [P("2bis. Conditionnement Secondaire (DCOII)", "H"),
              _packaging_table(b, "cond_secondaire", ss),
              _sig_block(b, "cond_secondaire", sig_by_stage, ss)]

    # ---- 3. Qualite (SPC) --------------------------------------------------
    story += [P("3. Controle Qualite - Contenance (10 flacons / 30 min)", "H")]
    _u = b.get("fill_unit") or "mL"
    qc_rows = [[P("<b>Heure</b>", "Small"), P(f"<b>Moyenne / 10 unites ({_u})</b>", "Small"),
                P(f"<b>Etendue ({_u})</b>", "Small"), P("<b>Verdict</b>", "Small")]]
    for p in spc["points"]:
        col = GOOD if p["verdict"] == "PASS" else CRIT
        qc_rows.append([P(p["at"][11:16]), P(_fmt(p["mean"], 1), "CellR"), P(_fmt(p["range"], 1), "CellR"),
                        Paragraph(p["verdict"], ParagraphStyle("v", parent=ss["CellR"], textColor=col))])
    if len(spc["points"]) == 0:
        qc_rows.append([P("Aucun echantillon enregistre"), P(""), P(""), P("")])
    qc = Table(qc_rows, colWidths=[40 * mm, 45 * mm, 45 * mm, 40 * mm])
    qc.setStyle(_tbl_style())
    story += [qc]
    if spc.get("forecast"):
        f = spc["forecast"]
        story += [Spacer(1, 3), Paragraph(
            f'&#9888; Prevision de derive : tendance vers {f["toward"]}, franchissement des '
            f'specifications dans ~{f["samples_to_spec_breach"]:.0f} echantillons '
            f'({f["minutes_to_spec_breach"]:.0f} min).',
            ParagraphStyle("fc", parent=ss["Small"], textColor=colors.HexColor("#8a6d00")))]
    story += [Spacer(1, 4), _sig_block(b, "qualite", sig_by_stage, ss)]

    # ---- deviations & CAPA -------------------------------------------------
    story += _deviation_section(b, ss)

    # ---- 4. Liberation -----------------------------------------------------
    story += [P("4. Liberation", "H")]
    lib_txt = ("Le present lot a ete revu et <b>libere</b> pour la vente : les quatre etapes sont "
               "signees et l'ensemble des controles contenance sont conformes."
               if released else
               "Lot <b>non libere</b> - la liberation est bloquee tant que les etapes ne sont pas "
               "toutes signees et la qualite conforme.")
    story += [P(lib_txt, "Cell"), Spacer(1, 4), _sig_block(b, "liberation", sig_by_stage, ss),
              Spacer(1, 8)]

    # ---- energy & carbon ---------------------------------------------------
    if energy["complete"]:
        story += [P("Energie &amp; empreinte carbone (passeport produit)", "H")]
        en_rows = [[P("<b>Dossier</b>", "Small"), P("<b>kWh</b>", "Small"), P("<b>kg CO2</b>", "Small")]]
        by = {s["stage"]: s for s in energy["per_stage"]}
        for st in STAGE_LABEL:
            s = by.get(st, {"kwh": 0, "co2_kg": 0})
            en_rows.append([P(STAGE_LABEL[st]), P(_fmt(s["kwh"], 2), "CellR"), P(_fmt(s["co2_kg"], 2), "CellR")])
        en_rows.append([P("<b>Total</b>", "Cell"), P(f'<b>{_fmt(energy["total_kwh"],2)}</b>', "CellR"),
                        P(f'<b>{_fmt(energy["total_co2_kg"],2)}</b>', "CellR")])
        en = Table(en_rows, colWidths=[90 * mm, 40 * mm, 40 * mm])
        en.setStyle(_tbl_style(total_row=True))
        story += [en, Spacer(1, 3),
                  P(f'Soit <b>{_fmt(energy["kwh_per_unit"],3)} kWh</b> et '
                    f'<b>{_fmt(energy["co2_g_per_unit"],0)} g CO2</b> par unite '
                    f'(facteur reseau {energy["co2_factor"]} kg CO2/kWh).', "Cell"),
                  Spacer(1, 8)]

    # ---- equipment used (standard BMR requirement) -------------------------
    from . import equipment
    snap = equipment.snapshot(b["product"])
    story += [P("Equipements utilises (jumeau numerique)", "H")]
    eq_rows = [[P("<b>ID</b>", "Small"), P("<b>Machine</b>", "Small"), P("<b>Modele</b>", "Small"),
               P("<b>Protocole</b>", "Small"), P("<b>Etalonnage</b>", "Small"), P("<b>Statut</b>", "Small")]]
    _stt = {"running": "OK", "warning": "ALERTE", "alarm": "ALARME"}
    for mc in snap["machines"]:
        eq_rows.append([P(mc["id"]), P(mc["name"]), P(f'{mc["brand"]} {mc["model"]}'),
                        P(mc["protocol"]), P(f'{mc["cal_date"]} (J+{mc["cal_due_days"]})'),
                        P(_stt.get(mc["status"], mc["status"]))])
    eq = Table(eq_rows, colWidths=[14 * mm, 40 * mm, 37 * mm, 33 * mm, 26 * mm, 20 * mm])
    eq.setStyle(_tbl_style())
    story += [eq, Spacer(1, 8)]

    # ---- data integrity ----------------------------------------------------
    story += [HRFlowable(width="100%", color=GRID, thickness=0.6), Spacer(1, 4),
              P("Integrite des donnees (ALCOA+ / 21 CFR Part 11)", "H")]
    ok = integ["valid"]
    integ_tbl = Table([[
        Paragraph(("&#10003; CHAINE INTACTE" if ok else "&#10007; FALSIFICATION DETECTEE"),
                  ParagraphStyle("i", fontName="Helvetica-Bold", fontSize=9,
                                 textColor=GOOD if ok else CRIT)),
        P(f'{len(audit)} evenements traces, chaines par hash SHA-256. '
          f'{"Aucune alteration." if ok else "Rupture a l&#39;entree #" + str(integ.get("broken_at"))}', "Small"),
    ]], colWidths=[45 * mm, 125 * mm])
    integ_tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOODBG if ok else CRITBG),
                                   ("BOX", (0, 0), (-1, -1), 0.5, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    anc = integ.get("anchor") or {}
    anc_txt = ("chaine confirmee par le journal d'ancrage externe "
               f"({anc.get('anchor_lines', 0)} ancrages)" if anc.get("valid")
               else f"ANCRAGE EXTERNE NON CONCORDANT: {anc.get('reason', '-')}")
    story += [integ_tbl, Spacer(1, 3),
              Paragraph(f"Empreinte du document (SHA-256) : {doc_hash}", ss["Mono"]),
              Paragraph(f"Tete de chaine d'audit : {integ.get('head','-')}", ss["Mono"]),
              Paragraph(f"Temoin externe : {anc_txt}", ss["Mono"]),
              Paragraph("Ce document imprime la tete de chaine : archive separement, il constitue "
                        "un troisieme temoin independant de la base et du journal d'ancrage.",
                        ss["Small"]),
              Paragraph(f"Genere le {gen_at} - toute modification ulterieure invalide l'empreinte.", ss["Mono"])]

    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=16 * mm, bottomMargin=16 * mm, title=f"Dossier de Lot {b['lot_name']}")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="t", frames=[frame],
                                       onPage=lambda c, d: _chrome(c, d, b["lot_name"], gen_at))])
    doc.build(story)
    return buf.getvalue(), doc_hash


def _tbl_style(total_row: bool = False):
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4fc")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, BLUE),
        ("GRID", (0, 1), (-1, -1), 0.3, GRID),
        ("BOX", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    if total_row:
        cmds += [("BACKGROUND", (0, -1), (-1, -1), SOFT), ("LINEABOVE", (0, -1), (-1, -1), 0.6, INK2)]
    return TableStyle(cmds)


def _packaging_table(b, stage, ss):
    """Bilan des articles de conditionnement: issued must equal used + returned
    + waste. An unexplained variance is exactly what an inspector looks for."""
    P = lambda t, s="Cell": Paragraph(t, ss[s])
    lines = [x for x in (b.get("packaging") or {}).get("lines", []) if x["stage"] == stage]
    if not lines:
        return Spacer(1, 2)
    rows = [[P("<b>Code</b>", "Small"), P("<b>Article</b>", "Small"),
             P("<b>Fourni</b>", "Small"), P("<b>Utilise</b>", "Small"),
             P("<b>Retourne</b>", "Small"), P("<b>Dechet</b>", "Small"),
             P("<b>Ecart</b>", "Small")]]
    for x in lines:
        if x["variance"] is None:
            var, col = "non solde", MUTED
        else:
            var = f'{x["variance"]:+,.0f} ({x["variance_pct"]:.2f}%)'.replace(",", " ")
            col = GOOD if x["ok"] else CRIT
        rows.append([P(x["code"]), P(x["label"]),
                     P(_fmt(x["issued"], 0), "CellR"), P(_fmt(x["used"], 0), "CellR"),
                     P(_fmt(x["returned"], 0), "CellR"), P(_fmt(x["waste"], 0), "CellR"),
                     Paragraph(var, ParagraphStyle("v", parent=ss["CellR"], textColor=col))])
    t = Table(rows, colWidths=[20 * mm, 54 * mm, 20 * mm, 20 * mm, 20 * mm, 18 * mm, 28 * mm])
    t.setStyle(_tbl_style())
    caption = Paragraph(
        "Bilan des articles de conditionnement : fourni = utilise + retourne + dechet.",
        ss["Small"])
    return KeepTogether([caption, Spacer(1, 2), t, Spacer(1, 4)])


def _deviation_section(b, ss):
    """Every deviation, its disposition, root cause and CAPA. Release is blocked
    while any of these is open."""
    P = lambda t, s="Cell": Paragraph(t, ss[s])
    devs = b.get("deviations") or []
    if not devs:
        return []
    out = [P("Deviations &amp; CAPA", "H")]
    rows = [[P("<b>Ref</b>", "Small"), P("<b>Constat</b>", "Small"),
             P("<b>Gravite</b>", "Small"), P("<b>Cause racine / CAPA</b>", "Small"),
             P("<b>Decision</b>", "Small"), P("<b>Statut</b>", "Small")]]
    for d in devs:
        closed = d["status"] == "closed"
        col = GOOD if closed else CRIT
        cause = (f'{d["root_cause"] or "-"}<br/><font size=6 color="#898781">'
                 f'CAPA: {d["capa"] or "-"}</font>') if closed else "en investigation"
        who = (f'{DISPO_LABEL.get(d["disposition"], d["disposition"] or "-")}'
               f'<br/><font size=6 color="#898781">{d["closed_by"] or ""} '
               f'{(d["closed_at"] or "")[:10]}</font>') if closed else "-"
        rows.append([P(d["ref"]),
                     P(f'{d["title"]}<br/><font size=6 color="#898781">{d["detail"] or ""}</font>'),
                     P(SEVERITY_LABEL.get(d["severity"], d["severity"])),
                     P(cause), P(who),
                     Paragraph("CLOTUREE" if closed else "OUVERTE",
                               ParagraphStyle("s", parent=ss["Cell"], textColor=col))])
    t = Table(rows, colWidths=[24 * mm, 50 * mm, 18 * mm, 40 * mm, 24 * mm, 24 * mm])
    t.setStyle(_tbl_style())
    return out + [t, Spacer(1, 6)]


def _sig_block(b, stage, sig_by_stage, ss):
    sig = sig_by_stage.get(stage)
    label = STAGE_LABEL[stage]
    if sig:
        role = ROLE_LABEL.get(sig["role"], sig["role"])
        left = Paragraph(
            f'<font size=7 color="#898781">SIGNATURE ELECTRONIQUE - {label}</font><br/>'
            f'<b>{sig["user"]}</b> &bull; {role}<br/>'
            f'<font size=7 color="#52514e">{sig["meaning"]}</font><br/>'
            f'<font size=7 color="#52514e">{sig["signed_at"].replace("T", " ")}</font>', ss["Cell"])
        right = Paragraph(f'<font size=6 color="#898781">Hash de l\'enregistrement signe :</font><br/>'
                          f'{sig["record_hash"]}', ss["Mono"])
        bg = GOODBG
    else:
        left = Paragraph(f'<font size=7 color="#898781">SIGNATURE - {label}</font><br/>'
                         f'<b><font color="#d03b3b">NON SIGNE</font></b>', ss["Cell"])
        right = Paragraph("", ss["Mono"])
        bg = colors.HexColor("#fbf3e6")
    t = Table([[left, right]], colWidths=[85 * mm, 85 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    return KeepTogether(t)


def _chrome(canvas, doc, lot, gen_at):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 10 * mm,
                      f"Dossier de Lot {lot} - genere par BatchTwin le {gen_at}")
    canvas.drawRightString(190 * mm, 10 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(GRID)
    canvas.line(20 * mm, 12 * mm, 190 * mm, 12 * mm)
    canvas.restoreState()
