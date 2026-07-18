"""
BatchTwin API — le dossier de lot vivant.

Run:  python -m uvicorn backend.main:app --reload --port 8000
Then open http://localhost:8000
"""
from __future__ import annotations
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel

from typing import Any

from . import (store, analytics, report, assistant, inventory, equipment,
               docx_parser, docx_forms)
from .odoo_adapter import MockOdoo

odoo = MockOdoo()
app = FastAPI(title="BatchTwin", version="0.1")
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
LOGO_DIR = ROOT / "logo"
DOSSIER_DIR = ROOT / "dossier"


@app.on_event("startup")
def _startup():
    store.init_db()


# ---- request bodies ---------------------------------------------------------
class Actor(BaseModel):
    user: str
    role: str


class ChecklistBody(Actor):
    ok: bool
    note: str = ""
    escalate_to: str | None = None


class DispenseBody(Actor):
    dispensed: float
    loss: float = 0.0


class QCBody(Actor):
    measurements: list[float]


class QCSimBody(Actor):
    drift: bool = False


class UnitsBody(Actor):
    good_units: int


class SignBody(Actor):
    stage: str
    meaning: str


class EnergyBody(Actor):
    stage: str
    machine: str
    kwh: float
    source: str = "iot"


# ---- meta -------------------------------------------------------------------
@app.get("/api/roles")
def roles():
    return {"roles": store.ROLES, "stages": store.STAGES, "stage_signer": store.STAGE_SIGNER}


@app.post("/api/seed")
def seed(reset: bool = True):
    """Reset and create the demo Dossier de Lot from the (mock) Odoo OF + OC."""
    store.init_db(reset=reset)
    ofs = odoo.search_read("mrp.production", [("order_kind", "=", "fabrication")], ["id"])
    ocs = odoo.search_read("mrp.production", [("order_kind", "=", "conditionnement")], ["id"])
    ids = [store.create_batch_from_odoo(odoo, of["id"], oc["id"], user="system")
           for of, oc in zip(ofs, ocs)]
    return {"batch_ids": ids, "batch_id": ids[0]}


# ---- batches ----------------------------------------------------------------
@app.get("/api/batches")
def batches():
    return store.list_batches()


@app.get("/api/dossier")
def dossier_index():
    docs = []
    tasks = []
    for path in sorted(DOSSIER_DIR.glob("*")):
        if path.is_file():
            docs.append({"name": path.name, "size_bytes": path.stat().st_size, "kind": path.suffix.lower()})
            if path.suffix.lower() == ".docx":
                tasks.extend(docx_parser.extract_docx_tasks(path))
    return {"documents": docs, "tasks": tasks}


STATIONS = [
    {"code": "vide", "label": "Vide de ligne", "icon": "🧹", "stage": "fabrication"},
    {"code": "pesee", "label": "Pesée / matières", "icon": "⚖️", "stage": "fabrication"},
    {"code": "qc", "label": "Contrôle contenance", "icon": "🔬", "stage": "qualite"},
    {"code": "sign", "label": "Signer / libérer", "icon": "✍️", "stage": None},
]


@app.get("/api/batch/{batch_id}/equipment")
def batch_equipment(batch_id: int):
    b = store.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "batch not found")
    return equipment.snapshot(b["product"])


@app.get("/api/batch/{batch_id}/codes")
def codes(batch_id: int):
    """Scannable code registry for the floor: the lot, each station, each material."""
    b = store.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "batch not found")
    lot = {"data": f"BT:LOT:{batch_id}", "label": f"Lot {b['lot_name']}", "kind": "lot"}
    stations = [{"data": f"BT:ST:{s['code']}", "label": s["label"], "icon": s["icon"], "kind": "station"}
                for s in STATIONS]
    materials = [{"data": f"BT:MAT:{d['id']}", "label": d["material"], "kind": "material"}
                 for d in b["dispense"]]
    return {"lot": lot, "stations": stations, "materials": materials}


@app.get("/api/qr")
def qr(data: str, scale: int = 6):
    """Render any payload as a scannable QR (SVG). Used to print floor codes."""
    import io as _io
    import segno
    buf = _io.BytesIO()
    segno.make(data, error="m").save(buf, kind="svg", scale=scale, border=2,
                                     dark="#0b0b0b", light="#ffffff")
    return Response(buf.getvalue().decode("utf-8"), media_type="image/svg+xml")


@app.get("/api/batch/{batch_id}")
def batch(batch_id: int):
    b = store.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "batch not found")
    mb = analytics.mass_balance(b["dispense"])
    kpis = analytics.batch_kpis(b, mb, b.get("good_units"))
    spc = analytics.spc(b["qc"], b["target_fill_g"], _lsl(b), _usl(b))
    energy = analytics.energy_summary(b["energy"], b.get("good_units"))
    return {"batch": b, "mass_balance": mb, "kpis": kpis, "spc": spc, "energy": energy}


def _lsl(b):
    return (b["target_fill_g"] or 0) - (b["fill_tol_g"] or 0)


def _usl(b):
    return (b["target_fill_g"] or 0) + (b["fill_tol_g"] or 0)


@app.post("/api/batch/{batch_id}/checklist/{item_id}")
def checklist(batch_id: int, item_id: int, body: ChecklistBody):
    store.update_checklist(item_id, int(body.ok), body.note, body.user, body.escalate_to)
    return {"ok": True}


@app.post("/api/batch/{batch_id}/dispense/{line_id}")
def dispense(batch_id: int, line_id: int, body: DispenseBody):
    store.record_dispense(line_id, body.dispensed, body.loss, body.user)
    return {"ok": True}


class FormFieldBody(Actor):
    field_key: str
    value: str = ""


_FORM_CACHE: dict[str, Any] = {}


def _forms() -> list[dict]:
    """Parsed once per file mtime -- edit the .docx and the app picks it up."""
    stamp = tuple(sorted((p.name, p.stat().st_mtime) for p in DOSSIER_DIR.glob("*.docx")))
    if _FORM_CACHE.get("stamp") != stamp:
        _FORM_CACHE["stamp"] = stamp
        _FORM_CACHE["forms"] = docx_forms.load_all(DOSSIER_DIR)
    return _FORM_CACHE["forms"]


@app.get("/api/forms")
def forms_index(batch_id: int | None = None):
    """The four real Medicka dossiers, parsed from the .docx into fillable specs."""
    forms = _forms()
    meta = [{k: f[k] for k in ("doc_key", "stage", "label", "title", "file", "field_count")}
            for f in forms]
    saved = sum(b.get("paper_rows", 1) - 1 for f in forms for s in f["sections"]
                for b in s["blocks"] if b.get("repeatable"))
    out = {"forms": meta, "paper_rows_eliminated": saved}
    if batch_id:
        out["progress"] = store.form_progress(batch_id, forms)
    return out


@app.get("/api/batch/{batch_id}/form/{doc_key}")
def form_get(batch_id: int, doc_key: str):
    form = next((f for f in _forms() if f["doc_key"] == doc_key), None)
    if not form:
        raise HTTPException(404, "dossier not found")
    b = store.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "batch not found")
    stage = next((s for s in b["stages"] if s["name"] == form["stage"]), None)
    return {"form": form, "values": store.get_form_values(batch_id, doc_key),
            "locked": bool(stage and stage["status"] == "signed"),
            "stage": form["stage"]}


@app.post("/api/batch/{batch_id}/form/{doc_key}")
def form_save(batch_id: int, doc_key: str, body: FormFieldBody):
    try:
        return store.save_form_field(batch_id, doc_key, body.field_key, body.value,
                                     body.user, body.role)
    except PermissionError as e:
        raise HTTPException(403, str(e))


class BomChangeBody(Actor):
    kind: str                       # add | amend | remove
    reason: str
    dispense_id: int | None = None
    material: str | None = None
    unit: str | None = None
    unit_cost: float = 0.0
    supplier: str | None = None
    rm_lot: str | None = None
    rm_expiry: str | None = None
    new_qty: float | None = None


class BomDecisionBody(Actor):
    approve: bool
    note: str = ""


@app.get("/api/materials")
def materials():
    """Quality-approved material catalog (Odoo). You can only add from this list."""
    return {"materials": store.material_catalog(odoo),
            "tolerance_pct": store.MINOR_TOLERANCE_PCT,
            "qa_roles": sorted(store.QA_ROLES),
            "requester_roles": sorted(store.CHANGE_REQUESTERS)}


@app.get("/api/batch/{batch_id}/changes")
def bom_changes(batch_id: int):
    return {"changes": store.list_bom_changes(batch_id)}


@app.post("/api/batch/{batch_id}/changes")
def bom_change_request(batch_id: int, body: BomChangeBody):
    try:
        return store.request_bom_change(
            batch_id, body.kind, body.user, body.role, body.reason,
            dispense_id=body.dispense_id, material=body.material, unit=body.unit,
            unit_cost=body.unit_cost, supplier=body.supplier, rm_lot=body.rm_lot,
            rm_expiry=body.rm_expiry, new_qty=body.new_qty)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/batch/{batch_id}/changes/{change_id}")
def bom_change_decide(batch_id: int, change_id: int, body: BomDecisionBody):
    try:
        return store.decide_bom_change(change_id, body.user, body.role, body.approve, body.note)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/batch/{batch_id}/qc")
def qc(batch_id: int, body: QCBody):
    if len(body.measurements) < 2:
        raise HTTPException(400, "need at least 2 measurements")
    return store.add_qc_sample(batch_id, body.measurements, body.user)


@app.post("/api/batch/{batch_id}/qc/simulate")
def qc_sim(batch_id: int, body: QCSimBody):
    """Generate one realistic 10-flacon contenance sample. Optional slow drift so
    the SPC forecast can predict an underfill before it happens."""
    b = store.get_batch(batch_id)
    target = b["target_fill_g"] or 200.0
    tol = b["fill_tol_g"] or 8.0
    existing = len(b["qc"])
    std = tol / 3.5                                    # scales to any product/unit
    bias = -(target * 0.009) * existing if body.drift else 0.0  # drift per prior sample
    sample = [round(random.gauss(target + bias, std), 1) for _ in range(10)]
    return store.add_qc_sample(batch_id, sample, body.user)


@app.post("/api/batch/{batch_id}/units")
def units(batch_id: int, body: UnitsBody):
    store.set_good_units(batch_id, body.good_units, body.user)
    return {"ok": True}


@app.post("/api/batch/{batch_id}/energy")
def energy(batch_id: int, body: EnergyBody):
    """IoT clamp / meter push (or manual entry) — one kWh reading for a stage."""
    store.record_energy(batch_id, body.stage, body.machine, body.kwh, body.source, body.user)
    return {"ok": True}


@app.post("/api/batch/{batch_id}/energy/simulate")
def energy_sim(batch_id: int, body: Actor):
    n = store.simulate_energy(batch_id, body.user)
    return {"readings": n}


@app.post("/api/batch/{batch_id}/sign")
def sign(batch_id: int, body: SignBody):
    try:
        return store.sign_stage(batch_id, body.stage, body.user, body.role, body.meaning)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- audit / data integrity -------------------------------------------------
@app.get("/api/audit")
def audit(batch_id: int | None = None):
    return {"entries": store.get_audit(batch_id), "integrity": store.verify_chain()}


# ---- AI copilot (Ollama, local) ---------------------------------------------
class ChatBody(BaseModel):
    batch_id: int
    message: str
    history: list[dict] = []
    lang: str = "fr"


@app.get("/api/assistant/health")
def assistant_health():
    return assistant.health()


@app.post("/api/assistant/chat")
def assistant_chat(body: ChatBody):
    try:
        return assistant.chat(body.batch_id, body.message, body.history, body.lang)
    except assistant.AssistantOffline:
        raise HTTPException(503, "Assistant IA hors ligne — démarrez Ollama (ollama serve)")
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/assistant/chat/stream")
def assistant_chat_stream(body: ChatBody):
    try:
        sources, gen = assistant.chat_stream(body.batch_id, body.message, body.history, body.lang)
    except assistant.AssistantOffline:
        raise HTTPException(503, "Assistant IA hors ligne — démarrez Ollama (ollama serve)")
    except ValueError as e:
        raise HTTPException(404, str(e))
    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8",
                             headers={"X-Sources": ",".join(sources), "Cache-Control": "no-cache"})


@app.post("/api/assistant/report")
def assistant_report(batch_id: int, lang: str = "fr"):
    try:
        return assistant.generate_report(batch_id, lang)
    except assistant.AssistantOffline:
        raise HTTPException(503, "Assistant IA hors ligne — démarrez Ollama (ollama serve)")


# ---- VERA: self-correcting inventory brain ----------------------------------
@app.get("/api/vera/overview")
def vera_overview(product: str | None = None):
    v = inventory.VERA
    return {"kpis": v.kpis(product), "decisions": v.decision_queue(product), "products": v.products()}


@app.get("/api/vera/skus")
def vera_skus(product: str | None = None):
    return inventory.VERA.sku_list(product)


@app.get("/api/vera/sku/{code}")
def vera_sku(code: str):
    p = inventory.VERA.project(code)
    if not p:
        raise HTTPException(404, "unknown material")
    return {"projection": p, "recommendation": inventory.VERA.recommend(code)}


@app.get("/api/vera/forecast/{fg}")
def vera_forecast(fg: str):
    fs = inventory.VERA.forecast_series(fg)
    if not fs:
        raise HTTPException(404, "unknown finished good")
    return fs


class VeraChatBody(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/api/vera/chat")
def vera_chat(body: VeraChatBody):
    try:
        return assistant.vera_chat(body.message, body.history)
    except assistant.AssistantOffline:
        raise HTTPException(503, "Assistant IA hors ligne — démarrez Ollama (ollama serve)")


@app.post("/api/vera/seed")
def vera_seed(seed: int = 42):
    inventory.reseed(seed)
    return {"ok": True}


@app.get("/vera")
def vera_page():
    return FileResponse(FRONTEND / "vera.html")


@app.get("/vera.js")
def vera_js():
    return FileResponse(FRONTEND / "vera.js")


@app.post("/api/demo/tamper/{audit_id}")
def tamper(audit_id: int):
    res = store.demo_tamper(audit_id)
    return {"tamper": res, "integrity": store.verify_chain()}


@app.get("/api/batch/{batch_id}/report.pdf")
def report_pdf(batch_id: int):
    try:
        pdf, _ = report.build_batch_pdf(batch_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    b = store.get_batch(batch_id)
    fname = f"Dossier_de_Lot_{b['lot_name']}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ---- frontend ---------------------------------------------------------------
@app.get("/")
def index():
    return FileResponse(FRONTEND / "landing.html")


@app.get("/landing")
def landing():
    return FileResponse(FRONTEND / "landing.html")


@app.get("/app")
def dashboard():
    return FileResponse(FRONTEND / "index.html")


@app.get("/app.js")
def appjs():
    return FileResponse(FRONTEND / "app.js")


@app.get("/i18n.js")
def i18njs():
    return FileResponse(FRONTEND / "i18n.js", media_type="application/javascript")


@app.get("/floor")
def floor():
    return FileResponse(FRONTEND / "floor.html")


@app.get("/floor.js")
def floorjs():
    return FileResponse(FRONTEND / "floor.js")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(FRONTEND / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(FRONTEND / "sw.js", media_type="application/javascript")


@app.get("/logo/{name}")
def logo(name: str):
    p = (LOGO_DIR / name).resolve()
    if p.parent != LOGO_DIR.resolve() or not p.exists():
        raise HTTPException(404, "not found")
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }.get(p.suffix.lower(), "application/octet-stream")
    return FileResponse(p, media_type=media_type)


@app.get("/dossier/{name}")
def dossier_file(name: str):
    p = (DOSSIER_DIR / name).resolve()
    if p.parent != DOSSIER_DIR.resolve() or not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, media_type="application/octet-stream")


@app.get("/icons/{name}")
def icon(name: str):
    p = (FRONTEND / "icons" / name).resolve()
    if p.parent != (FRONTEND / "icons").resolve() or not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, media_type="image/png")


@app.get("/vendor/{name}")
def vendor(name: str):
    p = (FRONTEND / "vendor" / name).resolve()
    if p.parent != (FRONTEND / "vendor").resolve() or not p.exists():
        raise HTTPException(404, "not found")
    mt = {".woff2": "font/woff2", ".css": "text/css"}.get(p.suffix, "application/javascript")
    return FileResponse(p, media_type=mt)


@app.get("/projections")
def projections():
    return FileResponse(FRONTEND / "projections.html")
