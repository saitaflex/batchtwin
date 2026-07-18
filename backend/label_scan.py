"""
Read a product label from a photo, locally.

Two capture routes feed the same review step:

  * BARCODE / QR -- decoded in the browser (BarcodeDetector), then resolved
    against our own catalog. No third-party lookup: a manufacturer's product
    data has no business being sent to an external service, and the real use
    case is scanning your own product to find or re-version it.

  * NUTRITION LABEL -- OCR'd here by a local Ollama vision model. The image
    never leaves the machine, which matters for a GMP site.

Nothing this module returns is ever saved directly. It fills a form the user
reviews and corrects first: an OCR guess is not a specification.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
VISION_MODEL = os.environ.get("BATCHTWIN_VISION", "granite3.2-vision")

PROMPT = """Tu lis l'etiquette d'un complement alimentaire. Reponds UNIQUEMENT en JSON,
sans texte autour, avec exactement ces cles:

{
  "name": "nom commercial du produit",
  "strength": "dosage principal, ex: 50 000 UI ou 500 mg",
  "packaging": "presentation, ex: boite de 30 comprimes",
  "units_per_pack": 30,
  "manufacturer": "fabricant si visible",
  "barcode": "code-barres si lisible",
  "storage": "conditions de conservation si visibles",
  "nutrients": [
    {"label": "nom du nutriment", "amount": "valeur numerique",
     "unit": "mg|g|UI|µg", "basis": "per_unit|per_dose|per_100g|per_100ml",
     "nrv_pct": 100}
  ]
}

Regles:
- N'invente rien. Si une information est absente ou illisible, mets null.
- "amount" ne contient que le nombre, l'unite va dans "unit".
- "nrv_pct" est le % des apports de reference (AR / VNR), nombre seul ou null.
- Recopie les nutriments dans l'ordre du tableau de l'etiquette."""


class ScanError(RuntimeError):
    pass


def available() -> dict:
    """Is a vision model actually installed? The UI hides the button if not."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            names = [m["name"] for m in json.loads(r.read()).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return {"available": False, "model": VISION_MODEL, "models": []}
    base = VISION_MODEL.split(":")[0]
    hit = next((n for n in names if n.split(":")[0] == base), None)
    if not hit:   # any vision model at all is better than none
        hit = next((n for n in names if _is_capable(n)), None)
    return {"available": bool(hit), "model": hit or VISION_MODEL,
            "capable": bool(hit) and _is_capable(hit),
            "models": names}


def _extract_json(text: str) -> dict:
    """Vision models like to wrap JSON in prose or a code fence. Dig it out."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, depth = None, 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = None
    raise ScanError("le modele n'a pas renvoye de JSON exploitable")


_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def _num(v):
    if v is None:
        return None
    m = _NUM.search(str(v))
    return float(m.group().replace(",", ".")) if m else None


def _clean(raw: dict) -> dict:
    """Normalise into exactly the shape the product form expects, and drop
    anything the model hallucinated into the wrong type."""
    def s(v):
        v = (str(v).strip() if v is not None else "")
        return v if v and v.lower() not in ("null", "none", "n/a", "-") else None

    nutrients = []
    for n in (raw.get("nutrients") or [])[:40]:
        if not isinstance(n, dict):
            continue
        label = s(n.get("label"))
        if not label:
            continue
        amount = n.get("amount")
        nutrients.append({
            "label": label,
            "amount": None if _num(amount) is None else f"{_num(amount):g}",
            "unit": s(n.get("unit")),
            "basis": n.get("basis") if n.get("basis") in
                     ("per_unit", "per_dose", "per_100g", "per_100ml") else "per_dose",
            "nrv_pct": _num(n.get("nrv_pct")),
            "source": "scan_label",
        })

    units = _num(raw.get("units_per_pack"))
    return {
        "name": s(raw.get("name")),
        "strength": s(raw.get("strength")),
        "packaging": s(raw.get("packaging")),
        "units_per_pack": int(units) if units else None,
        "manufacturer": s(raw.get("manufacturer")),
        "barcode": s(raw.get("barcode")),
        "storage": s(raw.get("storage")),
        "nutrients": nutrients,
    }


# A phone camera produces 3-12 Mpx, and a vision model turns pixels into tokens:
# a 620x760 label already costs ~18k tokens against granite3.2-vision:2b's 16k
# window, and num_ctx does not raise it. How much fits depends entirely on the
# model, so rather than hardcode one size we start large and step down until the
# server accepts it -- a bigger model keeps the detail, a small one still works.
EDGE_LADDER = (1280, 1024, 768, 512, 448, 384)
JPEG_QUALITY = 82


def _encode(raw: bytes, max_edge: int) -> str:
    """Downscale to `max_edge` on the long side and re-encode as base64 JPEG."""
    try:
        from PIL import Image
    except ImportError:
        return base64.b64encode(raw).decode()      # best effort without Pillow
    import io as _io
    try:
        im = Image.open(_io.BytesIO(raw))
        im.load()
    except Exception:
        raise ScanError("image illisible")
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    if max(im.size) > max_edge:
        ratio = max_edge / max(im.size)
        im = im.resize((max(1, int(im.width * ratio)), max(1, int(im.height * ratio))),
                       Image.LANCZOS)
    buf = _io.BytesIO()
    im.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


# Models that actually read a nutrition table reliably. A 2B model will answer
# but frequently returns nothing usable, so we say so rather than pretend.
GOOD_VISION = ("llama3.2-vision", "qwen2.5vl", "qwen2-vl", "minicpm-v", "llava:13b")


def _is_capable(model: str) -> bool:
    base = model.split(":")[0].lower()
    return any(base.startswith(g.split(":")[0]) for g in GOOD_VISION)


def read_label(image_b64: str, timeout: int = 150) -> dict:
    """OCR one label photo -> draft product fields for human review."""
    if not image_b64:
        raise ScanError("aucune image recue")
    # accept a full data: URL as well as bare base64
    if image_b64.startswith("data:"):
        image_b64 = image_b64.split(",", 1)[-1]
    try:
        raw = base64.b64decode(image_b64, validate=True)
    except Exception:
        raise ScanError("image illisible (base64 invalide)")

    info = available()
    if not info["available"]:
        raise ScanError(
            f"aucun modele de vision installe. Lancez: ollama pull {VISION_MODEL}")

    last = ""
    for edge in EDGE_LADDER:
        payload = {"model": info["model"], "stream": False,
                   "messages": [{"role": "user", "content": PROMPT,
                                 "images": [_encode(raw, edge)]}],
                   "options": {"temperature": 0}}
        req = urllib.request.Request(OLLAMA + "/api/chat", json.dumps(payload).encode(),
                                     {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            # Ollama IS reachable here -- it refused. Say why, not "unreachable".
            last = e.read().decode("utf-8", "replace")[:400]
            if "context" in last or "exceed" in last:
                continue                    # too many image tokens: try smaller
            raise ScanError(f"Ollama a refuse la requete ({e.code}): {last}")
        except TimeoutError:
            raise ScanError(
                f"le modele de vision ({info['model']}) n'a pas repondu en "
                f"{timeout}s. Un modele plus capable est recommande: "
                f"ollama pull llama3.2-vision")
        except urllib.error.URLError as e:
            raise ScanError(f"Ollama injoignable: {e}")

        content = (out.get("message", {}) or {}).get("content", "") or ""
        if not content.strip():
            raise ScanError(
                f"{info['model']} n'a rien renvoye. Les petits modeles de vision "
                f"(2B) lisent mal les etiquettes: essayez "
                f"'ollama pull llama3.2-vision', ou saisissez la composition a la main.")
        fields = _clean(content and _extract_json(content))
        return {"fields": fields, "model": info["model"], "resolution": edge,
                "capable_model": _is_capable(info["model"]),
                "review_required": True,
                "note": "Verifiez chaque valeur avant enregistrement : une lecture "
                        "automatique n'est pas une specification."}

    raise ScanError("image trop grande pour ce modele de vision meme reduite "
                    f"({EDGE_LADDER[-1]} px). Detail: {last}")
