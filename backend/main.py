"""
BatchTwin API — le dossier de lot vivant.

Run:  python -m uvicorn backend.main:app --reload --port 8000
Then open http://localhost:8000
"""
from __future__ import annotations
import copy
import random
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse, Response,
                               StreamingResponse)
from pydantic import BaseModel

from typing import Any

from . import (store, analytics, report, assistant, inventory, equipment,
               docx_parser, docx_forms, auth, anchor, products, label_scan,
               industry, observability, resilience, telemetry, advisor)
from .odoo_adapter import MockOdoo

odoo = MockOdoo()
app = FastAPI(title="BatchTwin", version="0.1")
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
LOGO_DIR = ROOT / "logo"
DOSSIER_DIR = ROOT / "dossier"


observability.setup()
_log = observability.log


@app.middleware("http")
async def _observe(request: Request, call_next):
    """Correlate, rate-limit, time and log every request; add security headers."""
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    observability.REQUEST_ID.set(rid)
    observability.CURRENT_USER.set("-")
    path, method = request.url.path, request.method

    if path.startswith("/api/"):
        bucket = observability.bucket_for(path, method)
        limit, window = observability.LIMITS[bucket]
        client = request.client.host if request.client else "unknown"
        ok, retry = observability.limiter.check(client, bucket, limit, window)
        if not ok:
            observability.event("http.rate_limited", path=path, bucket=bucket, client=client)
            return JSONResponse(
                {"detail": f"trop de requetes, reessayez dans {retry}s"},
                status_code=429,
                headers={"Retry-After": str(retry), "X-Request-Id": rid})

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # A stack trace on stdout is not an incident report. Log it structured,
        # correlated, and return something the operator can quote back to us.
        _log.exception("http.error", extra={"extra_fields": {
            "event": "http.error", "path": path, "method": method}})
        return JSONResponse(
            {"detail": "erreur interne", "request_id": rid},
            status_code=500, headers={"X-Request-Id": rid})

    ms = round((time.perf_counter() - started) * 1000, 1)
    if path.startswith("/api/"):
        observability.CURRENT_USER.set(getattr(request.state, "user", "-"))
        observability.event("http.request", path=path, method=method,
                            status=response.status_code, ms=ms)
    response.headers["X-Request-Id"] = rid
    for k, v in observability.SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    return response


@app.on_event("startup")
def _startup():
    store.init_db()
    telemetry.store.init()
    observability.event("app.start", profile=store.PROFILE["key"],
                        stages=len(store.STAGES))


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
    password: str          # Part 11: re-entered at every signature, never optional


class LoginBody(BaseModel):
    username: str
    password: str


class DeviationCloseBody(Actor):
    password: str
    disposition: str       # accept | rework | reject
    root_cause: str
    capa: str


class PackagingBody(Actor):
    code: str
    field: str             # issued | used | returned | waste
    value: float


class EnergyBody(Actor):
    stage: str
    machine: str
    kwh: float
    source: str = "iot"


# ---- authentication gate ----------------------------------------------------
# Identity is taken from the SESSION, never from the request body. Trusting a
# client-supplied {"user": ..., "role": ...} meant an anonymous caller could
# approve a formula change as QA or wipe the database: the role checks were
# real, but the role they checked was whatever the caller claimed.
def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.query_params.get("token", "")


def current_user(request: Request) -> dict:
    """Resolve the caller from their session token, or refuse."""
    with store._write_conn() as c:
        try:
            u = auth.resolve_session(c, _bearer(request))
        except auth.AuthError as e:
            raise HTTPException(401, str(e))
        observability.CURRENT_USER.set(u["username"])
        request.state.user = u["username"]     # survives back into the middleware
        return {"username": u["username"], "full_name": u["full_name"], "role": u["role"]}


def require_roles(*roles: str):
    """Authorisation, enforced server-side rather than in the UI."""
    def dep(me: dict = Depends(current_user)) -> dict:
        if me["role"] not in roles:
            raise HTTPException(
                403, f"role '{me['role']}' non autorise (requis: {', '.join(roles)})")
        return me
    return dep


Me = Depends(current_user)


# ---- identity ---------------------------------------------------------------
@app.post("/api/login")
def api_login(body: LoginBody):
    with store._write_conn() as c:
        try:
            return auth.login(c, body.username, body.password)
        except auth.AuthError as e:
            raise HTTPException(401, str(e))


@app.post("/api/logout")
def api_logout(token: str = ""):
    with store._write_conn() as c:
        auth.logout(c, token)
    return {"ok": True}


@app.get("/api/me")
def api_me(token: str = ""):
    with store._write_conn() as c:
        try:
            u = auth.resolve_session(c, token)
        except auth.AuthError as e:
            raise HTTPException(401, str(e))
        return {"username": u["username"], "full_name": u["full_name"], "role": u["role"]}


@app.get("/api/users")
def api_users():
    """Directory for the login screen. Passwords are never returned."""
    with store._conn() as c:
        return {"users": auth.list_users(c)}


# ---- product catalog --------------------------------------------------------
class NutrientBody(BaseModel):
    label: str
    amount: str | None = None
    unit: str | None = None
    basis: str = "per_dose"
    nrv_pct: float | None = None
    source: str = "manual"


class ProductBody(Actor):
    code: str | None = None
    name: str | None = None
    sku: str | None = None
    category: str | None = None
    dosage_form: str | None = None
    strength: str | None = None
    packaging: str | None = None
    units_per_pack: int | None = None
    manufacturer: str | None = None
    licensor: str | None = None
    barcode: str | None = None
    shelf_life_months: int | None = None
    fill_target: float | None = None
    fill_tolerance: float | None = None
    fill_unit: str | None = None
    storage: str | None = None
    notes: str | None = None
    nutrients: list[NutrientBody] | None = None
    change_reason: str | None = None   # required when creating a new version


def _product_payload(body: ProductBody) -> tuple[dict, list[dict] | None]:
    data = body.model_dump(exclude={"user", "role", "nutrients", "change_reason"})
    nutrients = None if body.nutrients is None else [n.model_dump() for n in body.nutrients]
    return data, nutrients


@app.get("/api/products")
def products_list(include_superseded: bool = False, me: dict = Me):
    with store._conn() as c:
        return {"products": products.listing(c, include_superseded),
                "dosage_forms": products.DOSAGE_FORMS,
                "categories": products.CATEGORIES,
                "nutrient_basis": products.NUTRIENT_BASIS}


@app.get("/api/products/{product_id}")
def product_get(product_id: int, me: dict = Me):
    with store._conn() as c:
        p = products.get(c, product_id)
    if not p:
        raise HTTPException(404, "produit introuvable")
    p["dossier_prefill"] = products.dossier_prefill(p)
    return p


@app.post("/api/products")
def product_create(body: ProductBody, me: dict = Depends(require_roles("smq", "prt"))):
    data, nutrients = _product_payload(body)
    try:
        with store._write_conn() as c:
            p = products.create(c, data, nutrients or [], me["username"])
            store.audit(c, me["username"], "product.create",
                        {"code": p["code"], "version": p["version"], "name": p["name"]})
    except products.ProductError as e:
        raise HTTPException(400, str(e))
    store.anchor_now()
    return p


@app.post("/api/products/{product_id}/version")
def product_version(product_id: int, body: ProductBody,
                    me: dict = Depends(require_roles("smq", "prt"))):
    """Supersede a specification. The old version stays readable forever."""
    data, nutrients = _product_payload(body)
    try:
        with store._write_conn() as c:
            p = products.new_version(c, product_id, data, nutrients,
                                     body.change_reason or "", me["username"])
            store.audit(c, me["username"], "product.version",
                        {"code": p["code"], "version": p["version"],
                         "reason": body.change_reason})
    except products.ProductError as e:
        raise HTTPException(400, str(e))
    store.anchor_now()
    return p


@app.post("/api/products/{product_id}/edit")
def product_edit(product_id: int, body: ProductBody,
                 me: dict = Depends(require_roles("smq", "prt"))):
    """Non-specification fields only (SKU, barcode, storage note, remarks)."""
    data, _ = _product_payload(body)
    try:
        with store._write_conn() as c:
            p = products.update_in_place(c, product_id, data, me["username"])
            store.audit(c, me["username"], "product.edit", {"code": p["code"]})
    except products.ProductError as e:
        raise HTTPException(400, str(e))
    store.anchor_now()
    return p


class ScanBody(BaseModel):
    image: str            # base64 (data: URL accepted)


@app.get("/api/scan/health")
def scan_health(me: dict = Me):
    """Tells the UI whether to offer the camera OCR button at all."""
    return label_scan.available()


@app.post("/api/scan/label")
def scan_label(body: ScanBody, me: dict = Me):
    """OCR a nutrition label locally -> draft fields for review, never saved."""
    try:
        return label_scan.read_label(body.image)
    except label_scan.ScanError as e:
        raise HTTPException(422, str(e))


@app.get("/api/products/barcode/{barcode}")
def product_by_barcode(barcode: str, me: dict = Me):
    """Resolve a scanned code against OUR OWN catalog.

    Deliberately not a third-party lookup: a manufacturer's product data is not
    something to send to an external service, and scanning your own product to
    find or re-version it is the actual use case.
    """
    with store._conn() as c:
        p = products.by_barcode(c, barcode)
    return {"found": bool(p), "product": p, "barcode": barcode}


# ---- telemetry: high-frequency data, deliberately in its own store ---------
class TelemetryBody(BaseModel):
    readings: list[dict]          # {machine, channel, value, unit?, at?, source?}
    batch_id: int | None = None


@app.post("/api/telemetry")
def telemetry_ingest(body: TelemetryBody, me: dict = Me):
    """Bulk ingest from an OPC UA / Modbus collector.

    Writes to telemetry.db, never to the record database: one sensor at 1 Hz is
    28,800 rows per shift and must not contend with signature transactions.
    """
    rows = [{**r, "batch_id": r.get("batch_id", body.batch_id)} for r in body.readings]
    try:
        n = telemetry.store.write_many(rows)
    except (KeyError, TypeError) as e:
        raise HTTPException(400, f"lecture invalide: {e}")
    return {"ingested": n}


@app.get("/api/telemetry/stats")
def telemetry_stats(me: dict = Me):
    """Proof the separation is real: size, retention and where it lives."""
    return telemetry.store.stats()


@app.get("/api/batch/{batch_id}/telemetry")
def telemetry_for_batch(batch_id: int, machine: str | None = None,
                        channel: str | None = None, me: dict = Me):
    """Raw series for investigation; aggregates are what the dossier carries."""
    return {"aggregate": telemetry.store.aggregate(batch_id),
            "series": telemetry.store.series(batch_id, machine, channel),
            "promoted": telemetry.promote_to_record(batch_id)}


# ---- recovery advisor: what this plant did last time, and did it hold -------
@app.get("/api/batch/{batch_id}/advice")
def batch_advice(batch_id: int, machine: str | None = None, me: dict = Me):
    """Recovery guidance drawn from the site's own closed deviations.

    Two triggers: an open deviation (what was done about this before?), and an
    SPC drift with no failure yet (what was done last time it drifted this way?).
    Every suggestion cites the lot it came from -- an operator can go and read it.
    """
    b = store.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "lot introuvable")
    every = [x for x in (store.get_batch(r["id"]) for r in store.list_batches()) if x]

    out = {"learning": advisor.learning_stats(every), "open": [], "drift": None}
    for d in b.get("deviations") or []:
        if d.get("status") == "open":
            out["open"].append({"deviation": {"ref": d["ref"], "title": d["title"],
                                              "severity": d["severity"]},
                                **advisor.recommend(d, b, every, machine)})
    spc = analytics.spc(b["qc"], b["target_fill_g"], _lsl(b), _usl(b))
    out["drift"] = advisor.drift_advice(spc, b, every, machine)
    return out


# ---- management KPIs --------------------------------------------------------
@app.get("/api/kpis")
def site_kpis(horizon_days: int = 90, me: dict = Me):
    """Site-level performance. Everything is derived from existing records, so
    no figure is maintained by hand or entered twice."""
    batches = [store.get_batch(b["id"]) for b in store.list_batches()]
    batches = [b for b in batches if b]
    return {"kpis": analytics.site_kpis(batches, horizon_days),
            "pareto": analytics.deviation_pareto(batches),
            "migration": store.migration_status()}


# ---- resilience: what happens when the hardware fails ----------------------
@app.get("/api/resilience")
def resilience_modes(me: dict = Me):
    """The failure-mode table. An auditor can read exactly what degrades how."""
    return resilience.summary()


@app.get("/api/batch/{batch_id}/provenance")
def batch_provenance(batch_id: int, me: dict = Me):
    """How much of this lot was metered automatically vs typed by hand.

    QA needs this at release: a fully hand-entered lot is not the same evidence
    as one metered end to end, even when both are complete.
    """
    b = store.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "lot introuvable")
    prov = resilience.batch_data_provenance(b)
    last = max((r["at"] for r in (b.get("energy") or [])), default=None)
    prov["telemetry"] = resilience.reading_health(last)
    prov["manual_entry_required"] = resilience.manual_entry_required(prov["telemetry"])
    return prov


# ---- industry profile -------------------------------------------------------
class ProfileBody(Actor):
    key: str


@app.get("/api/industry")
def industry_get(me: dict = Me):
    """Which rulebook is active, and what else is available."""
    return {"active": store.PROFILE, "available": industry.available()}


@app.post("/api/industry")
def industry_set(body: ProfileBody, me: dict = Depends(require_roles("smq", "prt"))):
    """Switch the rulebook. QA only: it changes what the record legally means.

    Existing batches keep the stages they were created with -- a profile change
    must never rewrite a signed record.
    """
    try:
        p = store.use_profile(body.key)
    except industry.ProfileError as e:
        raise HTTPException(400, str(e))
    with store._write_conn() as c:
        store.audit(c, me["username"], "industry.profile", {"key": p["key"], "label": p["label"]})
    store.anchor_now()
    return {"active": p}


# ---- meta -------------------------------------------------------------------
@app.get("/api/roles")
def roles(me: dict = Me):
    return {"roles": store.ROLES, "stages": store.STAGES,
            "stage_signer": store.STAGE_SIGNER,
            "profile": {k: store.PROFILE[k] for k in ("key", "label", "regulation")},
            "terminology": store.PROFILE.get("terminology", {})}


@app.post("/api/seed")
def seed(reset: bool = True, me: dict = Depends(require_roles("smq", "prt"))):
    """Reset and create the demo Dossier de Lot from the (mock) Odoo OF + OC."""
    store.init_db(reset=reset)
    ofs = odoo.search_read("mrp.production", [("order_kind", "=", "fabrication")], ["id"])
    ocs = odoo.search_read("mrp.production", [("order_kind", "=", "conditionnement")], ["id"])
    with store._conn() as c:
        catalog = {p["sku"]: p["id"] for p in products.listing(c) if p.get("sku")}
    # Map the demo manufacturing orders onto real catalog products.
    ids = []
    for of, oc in zip(ofs, ocs):
        prod = odoo.read("mrp.production", [of["id"]], ["product_id"])[0]
        code = odoo.read("product.product", [prod["product_id"][0]], ["default_code"])[0]
        pid = catalog.get(code.get("default_code"))
        if pid:
            ids.append(store.create_batch_for_product(odoo, pid, of["id"], oc["id"], "system"))
        else:
            ids.append(store.create_batch_from_odoo(odoo, of["id"], oc["id"], "system"))
    return {"batch_ids": ids, "batch_id": ids[0]}


# ---- batches ----------------------------------------------------------------
@app.get("/api/batches")
def batches(product_code: str | None = None, me: dict = Me):
    return store.list_batches(product_code)


class NewBatchBody(Actor):
    product_id: int
    qty_target: int | None = None


@app.post("/api/batches")
def batch_create(body: NewBatchBody, me: dict = Me):
    """Open a Dossier de Lot for a product. The specification drives it."""
    ofs = odoo.search_read("mrp.production", [("order_kind", "=", "fabrication")], ["id"])
    ocs = odoo.search_read("mrp.production", [("order_kind", "=", "conditionnement")], ["id"])
    if not ofs or not ocs:
        raise HTTPException(400, "aucun ordre de fabrication disponible")
    try:
        bid = store.create_batch_for_product(odoo, body.product_id, ofs[0]["id"],
                                             ocs[0]["id"], me["username"], body.qty_target)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"batch_id": bid, "batch": store.get_batch(bid)}


@app.get("/api/dossier")
def dossier_index(me: dict = Me):
    docs = []
    tasks = []
    for path in sorted(DOSSIER_DIR.glob("*")):
        if path.is_file():
            docs.append({"name": path.name, "size_bytes": path.stat().st_size, "kind": path.suffix.lower()})
            if path.suffix.lower() == ".docx":
                tasks.extend(docx_parser.extract_docx_tasks(path))
    return {"documents": docs, "tasks": tasks}


# Translation keys, not prose: the shop floor reads these in FR, EN or AR and
# the server has no business choosing which.
STATIONS = [
    {"code": "vide", "key": "station_vide", "icon": "🧹", "stage": "fabrication"},
    {"code": "pesee", "key": "station_pesee", "icon": "⚖️", "stage": "fabrication"},
    {"code": "qc", "key": "station_qc", "icon": "🔬", "stage": "qualite"},
    {"code": "sign", "key": "station_sign", "icon": "✍️", "stage": None},
]


@app.get("/api/batch/{batch_id}/equipment")
def batch_equipment(batch_id: int, me: dict = Me):
    b = store.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "batch not found")
    return equipment.snapshot(b["product"])


@app.get("/api/batch/{batch_id}/codes")
def codes(batch_id: int, me: dict = Me):
    """Scannable code registry for the floor: the lot, each station, each material."""
    b = store.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "batch not found")
    lot = {"data": f"BT:LOT:{batch_id}", "label": f"Lot {b['lot_name']}", "kind": "lot"}
    stations = [{"data": f"BT:ST:{s['code']}", "key": s["key"], "icon": s["icon"],
                 "kind": "station"} for s in STATIONS]
    materials = [{"data": f"BT:MAT:{d['id']}", "label": d["material"], "kind": "material"}
                 for d in b["dispense"]]
    return {"lot": lot, "stations": stations, "materials": materials}


@app.get("/api/qr")
def qr(data: str, scale: int = 6):
    """Render any payload as a scannable QR (SVG). Used to print floor codes."""
    import io as _io
    import segno
    buf = _io.BytesIO()
    # make_qr(), NOT make(): segno.make() silently prefers Micro QR for short
    # payloads like "BT:ST:qc", and Micro QR has one finder pattern instead of
    # three. Most scanner apps and every BarcodeDetector implementation treat it
    # as a separate format they do not support, so the printed floor codes were
    # unreadable. Forcing a full QR costs a few millimetres of paper.
    segno.make_qr(data, error="m").save(buf, kind="svg", scale=scale, border=2,
                                        dark="#0b0b0b", light="#ffffff")
    return Response(buf.getvalue().decode("utf-8"), media_type="image/svg+xml")


@app.get("/api/batch/{batch_id}")
def batch(batch_id: int, me: dict = Me):
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
def checklist(batch_id: int, item_id: int, body: ChecklistBody, me: dict = Me):
    store.update_checklist(item_id, int(body.ok), body.note, me["username"], body.escalate_to)
    return {"ok": True}


@app.post("/api/batch/{batch_id}/dispense/{line_id}")
def dispense(batch_id: int, line_id: int, body: DispenseBody, me: dict = Me):
    store.record_dispense(line_id, body.dispensed, body.loss, me["username"])
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
def forms_index(batch_id: int | None = None, me: dict = Me):
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
def form_get(batch_id: int, doc_key: str, me: dict = Me):
    form = next((f for f in _forms() if f["doc_key"] == doc_key), None)
    if not form:
        raise HTTPException(404, "dossier not found")
    b = store.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "batch not found")
    stage = next((s for s in b["stages"] if s["name"] == form["stage"]), None)
    # Deep-copy before overlaying: _forms() is a process-wide cache and the
    # overlay is per batch. Mutating the cache would leak one product's data
    # into every other batch's dossier.
    form = copy.deepcopy(form)
    spec = b.get("product_spec")
    store.apply_product_to_form(form, spec)
    return {"form": form, "values": store.get_form_values(batch_id, doc_key),
            "locked": bool(stage and stage["status"] == "signed"),
            "stage": form["stage"],
            "product": None if not spec else {
                "id": spec["id"], "code": spec["code"], "version": spec["version"],
                "name": spec["name"], "status": spec["status"]}}


@app.post("/api/batch/{batch_id}/form/{doc_key}")
def form_save(batch_id: int, doc_key: str, body: FormFieldBody, me: dict = Me):
    try:
        return store.save_form_field(batch_id, doc_key, body.field_key, body.value,
                                     me["username"], me["role"])
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
def materials(me: dict = Me):
    """Quality-approved material catalog (Odoo). You can only add from this list."""
    return {"materials": store.material_catalog(odoo),
            "tolerance_pct": store.MINOR_TOLERANCE_PCT,
            "qa_roles": sorted(store.QA_ROLES),
            "requester_roles": sorted(store.CHANGE_REQUESTERS)}


@app.get("/api/batch/{batch_id}/changes")
def bom_changes(batch_id: int, me: dict = Me):
    return {"changes": store.list_bom_changes(batch_id)}


@app.post("/api/batch/{batch_id}/changes")
def bom_change_request(batch_id: int, body: BomChangeBody, me: dict = Me):
    try:
        return store.request_bom_change(
            batch_id, body.kind, me["username"], me["role"], body.reason,
            dispense_id=body.dispense_id, material=body.material, unit=body.unit,
            unit_cost=body.unit_cost, supplier=body.supplier, rm_lot=body.rm_lot,
            rm_expiry=body.rm_expiry, new_qty=body.new_qty)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/batch/{batch_id}/changes/{change_id}")
def bom_change_decide(batch_id: int, change_id: int, body: BomDecisionBody, me: dict = Me):
    try:
        return store.decide_bom_change(change_id, me["username"], me["role"], body.approve, body.note)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/batch/{batch_id}/qc")
def qc(batch_id: int, body: QCBody, me: dict = Me):
    if len(body.measurements) < 2:
        raise HTTPException(400, "need at least 2 measurements")
    return store.add_qc_sample(batch_id, body.measurements, me["username"])


@app.post("/api/batch/{batch_id}/qc/simulate")
def qc_sim(batch_id: int, body: QCSimBody, me: dict = Me):
    """Generate one realistic 10-flacon contenance sample. Optional slow drift so
    the SPC forecast can predict an underfill before it happens."""
    b = store.get_batch(batch_id)
    target = b["target_fill_g"] or 200.0
    tol = b["fill_tol_g"] or 8.0
    existing = len(b["qc"])
    std = tol / 3.5                                    # scales to any product/unit
    bias = -(target * 0.009) * existing if body.drift else 0.0  # drift per prior sample
    sample = [round(random.gauss(target + bias, std), 1) for _ in range(10)]
    return store.add_qc_sample(batch_id, sample, me["username"])


@app.post("/api/batch/{batch_id}/units")
def units(batch_id: int, body: UnitsBody, me: dict = Me):
    store.set_good_units(batch_id, body.good_units, me["username"])
    return {"ok": True}


@app.post("/api/batch/{batch_id}/energy")
def energy(batch_id: int, body: EnergyBody, me: dict = Me):
    """IoT clamp / meter push (or manual entry) — one kWh reading for a stage."""
    store.record_energy(batch_id, body.stage, body.machine, body.kwh, body.source, me["username"])
    return {"ok": True}


@app.post("/api/batch/{batch_id}/energy/simulate")
def energy_sim(batch_id: int, body: Actor, me: dict = Me):
    n = store.simulate_energy(batch_id, me["username"])
    return {"readings": n}


@app.post("/api/batch/{batch_id}/sign")
def sign(batch_id: int, body: SignBody, me: dict = Me):
    try:
        return store.sign_stage(batch_id, body.stage, me["username"], me["role"],
                                body.meaning, body.password)
    except auth.AuthError as e:
        raise HTTPException(401, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- offline replay ---------------------------------------------------------
class SyncOp(BaseModel):
    op_id: str                  # client UUID -> idempotency key
    kind: str                   # form | dispense | qc | checklist | packaging | units
    batch_id: int
    client_at: str              # when the operator actually acted, on the tablet
    payload: dict


class SyncBody(Actor):
    ops: list[SyncOp]


@app.post("/api/sync")
def sync(body: SyncBody, me: dict = Me):
    """Replay work captured while the tablet was offline.

    Signing is deliberately absent: it needs a live password check, so it is
    never queued. See store.OFFLINE_KINDS.
    """
    applied, skipped, failed = [], [], []
    for op in body.ops:
        if op.kind not in store.OFFLINE_KINDS:
            failed.append({"op_id": op.op_id, "error": f"'{op.kind}' ne peut pas etre differe"})
            continue
        if store.already_applied(op.op_id):
            skipped.append(op.op_id)          # duplicate replay -> no double-apply
            continue
        try:
            result = _apply_op(op, me["username"], me["role"])
            store.mark_applied(op.op_id, op.kind, op.batch_id, op.client_at, result)
            applied.append(op.op_id)
        except Exception as e:                # keep going: one bad op must not
            failed.append({"op_id": op.op_id, "error": str(e)})   # block the rest
    return {"applied": applied, "skipped": skipped, "failed": failed}


def _apply_op(op: SyncOp, user: str, role: str):
    p = op.payload
    if op.kind == "form":
        return store.save_form_field(op.batch_id, p["doc_key"], p["field_key"],
                                     p.get("value", ""), user, role)
    if op.kind == "dispense":
        return store.record_dispense(p["line_id"], p["dispensed"], p.get("loss", 0), user)
    if op.kind == "qc":
        return store.add_qc_sample(op.batch_id, p["measurements"], user)
    if op.kind == "checklist":
        return store.update_checklist(p["item_id"], int(p["ok"]), p.get("note", ""),
                                      user, p.get("escalate_to"))
    if op.kind == "packaging":
        return store.set_packaging_recon(op.batch_id, p["code"], p["field"], p["value"], user)
    if op.kind == "units":
        return store.set_good_units(op.batch_id, p["good_units"], user)
    raise ValueError(f"kind inconnu: {op.kind}")


@app.get("/api/sync/stats")
def sync_stats(batch_id: int | None = None, me: dict = Me):
    return store.sync_stats(batch_id)


# ---- migration: parallel run -> cutover -------------------------------------
class RunModeBody(Actor):
    mode: str                  # parallel | live
    paper_ref: str = ""


@app.get("/api/migration")
def migration(product_code: str | None = None, me: dict = Me):
    """Where each product line stands on its way off paper."""
    return store.migration_status(product_code)


@app.post("/api/batch/{batch_id}/run-mode")
def run_mode(batch_id: int, body: RunModeBody,
             me: dict = Depends(require_roles("smq", "prt"))):
    """Hand the legal record from paper to BatchTwin, or back. QA only."""
    try:
        return store.set_run_mode(batch_id, body.mode, me["username"], me["role"],
                                  body.paper_ref)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- deviations / CAPA ------------------------------------------------------
@app.get("/api/batch/{batch_id}/deviations")
def deviations(batch_id: int, me: dict = Me):
    return {"deviations": store.list_deviations(batch_id),
            "dispositions": store.DISPOSITIONS}


@app.post("/api/batch/{batch_id}/deviation/{deviation_id}/close")
def deviation_close(batch_id: int, deviation_id: int, body: DeviationCloseBody, me: dict = Me):
    try:
        return store.close_deviation(deviation_id, me["username"], me["role"], body.password,
                                     body.disposition, body.root_cause, body.capa)
    except auth.AuthError as e:
        raise HTTPException(401, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- packaging article reconciliation (DCOI / DCOII) ------------------------
@app.get("/api/batch/{batch_id}/packaging")
def packaging(batch_id: int, me: dict = Me):
    return store.packaging_balance(batch_id)


@app.post("/api/batch/{batch_id}/packaging")
def packaging_set(batch_id: int, body: PackagingBody, me: dict = Me):
    try:
        return store.set_packaging_recon(batch_id, body.code, body.field,
                                         body.value, me["username"])
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- audit / data integrity -------------------------------------------------
@app.get("/api/audit")
def audit(batch_id: int | None = None, me: dict = Me):
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
def assistant_chat(body: ChatBody, me: dict = Me):
    try:
        return assistant.chat(body.batch_id, body.message, body.history, body.lang)
    except assistant.AssistantOffline:
        raise HTTPException(503, "Assistant IA hors ligne — démarrez Ollama (ollama serve)")
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/assistant/chat/stream")
def assistant_chat_stream(body: ChatBody, me: dict = Me):
    try:
        sources, gen = assistant.chat_stream(body.batch_id, body.message, body.history, body.lang)
    except assistant.AssistantOffline:
        raise HTTPException(503, "Assistant IA hors ligne — démarrez Ollama (ollama serve)")
    except ValueError as e:
        raise HTTPException(404, str(e))
    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8",
                             headers={"X-Sources": ",".join(sources), "Cache-Control": "no-cache"})


@app.post("/api/assistant/report")
def assistant_report(batch_id: int, lang: str = "fr", me: dict = Me):
    try:
        return assistant.generate_report(batch_id, lang)
    except assistant.AssistantOffline:
        raise HTTPException(503, "Assistant IA hors ligne — démarrez Ollama (ollama serve)")


# ---- VERA: self-correcting inventory brain ----------------------------------
@app.get("/api/vera/overview")
def vera_overview(product: str | None = None, me: dict = Me):
    v = inventory.VERA
    return {"kpis": v.kpis(product), "decisions": v.decision_queue(product), "products": v.products()}


@app.get("/api/vera/skus")
def vera_skus(product: str | None = None, me: dict = Me):
    return inventory.VERA.sku_list(product)


@app.get("/api/vera/sku/{code}")
def vera_sku(code: str, me: dict = Me):
    p = inventory.VERA.project(code)
    if not p:
        raise HTTPException(404, "unknown material")
    return {"projection": p, "recommendation": inventory.VERA.recommend(code)}


@app.get("/api/vera/forecast/{fg}")
def vera_forecast(fg: str, me: dict = Me):
    fs = inventory.VERA.forecast_series(fg)
    if not fs:
        raise HTTPException(404, "unknown finished good")
    return fs


class VeraChatBody(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/api/vera/chat")
def vera_chat(body: VeraChatBody, me: dict = Me):
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
def tamper(audit_id: int, me: dict = Depends(require_roles("smq", "prt"))):
    res = store.demo_tamper(audit_id)
    return {"tamper": res, "integrity": store.verify_chain()}


@app.get("/api/batch/{batch_id}/report.pdf")
def report_pdf(batch_id: int, me: dict = Me):
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


@app.get("/session.js")
def session_js():
    return FileResponse(FRONTEND / "session.js", media_type="application/javascript")


@app.get("/barcode.js")
def barcode_js():
    """EAN decoder used where the browser has no BarcodeDetector (Firefox,
    Safari, most Chrome desktop builds). Served locally, never from a CDN."""
    return FileResponse(FRONTEND / "barcode.js", media_type="application/javascript")


@app.get("/qr.js")
def qr_js():
    """QR decoder, same fallback role as barcode.js -- without it the /floor
    station and material codes cannot be scanned outside Chrome."""
    return FileResponse(FRONTEND / "qr.js", media_type="application/javascript")


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
    # A cached service worker is how a stale build survives a deploy: tell the
    # browser to always revalidate this one file.
    return FileResponse(FRONTEND / "sw.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/reset")
def reset_client():
    """Escape hatch: unregister the service worker and drop every cache.

    Browser caches are the one piece of state the server cannot reach, so when a
    stale build is stuck this page fixes it without hunting through devtools.
    """
    return HTMLResponse("""<!doctype html><meta charset=utf-8>
<title>BatchTwin — reset</title>
<style>body{font-family:system-ui,sans-serif;background:#05070B;color:#fff;display:grid;
place-items:center;height:100vh;margin:0;text-align:center}
.c{max-width:420px;padding:28px}h1{font-size:20px;margin:0 0 8px}
p{color:#A5B4C3;font-size:14px;line-height:1.6}code{color:#38BDF8}
a{display:inline-block;margin-top:18px;padding:12px 22px;border-radius:999px;
background:linear-gradient(100deg,#6C63FF,#38BDF8);color:#fff;text-decoration:none;font-weight:600}</style>
<div class=c><h1 id=s>Nettoyage…</h1><p id=d>Suppression des caches et du service worker.</p>
<a href="/app">Ouvrir /app</a></div>
<script>
(async () => {
  let n = 0;
  if ("serviceWorker" in navigator) {
    for (const r of await navigator.serviceWorker.getRegistrations()) { await r.unregister(); n++; }
  }
  const keys = window.caches ? await caches.keys() : [];
  for (const k of keys) await caches.delete(k);
  try { localStorage.removeItem("bt_token"); } catch (e) {}
  document.getElementById("s").textContent = "Cache vidé";
  document.getElementById("d").innerHTML =
    n + " service worker(s) désinscrit(s), " + keys.length + " cache(s) supprimé(s).<br>" +
    "Ouvrez <code>/app</code> — la version actuelle sera chargée.";
})();
</script>""")


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
