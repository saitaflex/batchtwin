"""
Equipment / machine digital-twin layer for BatchTwin.

Aligns the batch record with the standard GMP Batch Manufacturing Record
("Equipment used": machine identity + ID + calibration) AND adds the Pharma-4.0
angle the documentation implies: each machine exposes live telemetry over an
industrial protocol (OPC UA / Modbus TCP / Siemens S7 / EtherNet-IP).

Medicka does not publish exact brands, so these are representative industrial
models used on the same processes (capsule filling, liquid mixing/filling,
packaging). Telemetry is simulated — swap the `snapshot()` reader for a real
OPC UA / MQTT client to go live.
"""
from __future__ import annotations
import datetime as _dt
import random

TODAY = _dt.date.today()

# Each param: (label, unit, nominal, tolerance). status=alarm if any |v-nom|>tol.
CATALOG = {
    "liquid": [
        {"id": "MX-01", "name": "Cuve de mélange & agitation", "brand": "GEA", "model": "ECOMAX 500 L",
         "stage": "fabrication", "protocol": "OPC UA", "cal_due": 46,
         "params": [("Température", "°C", 24.0, 3.0), ("Vitesse agitateur", "rpm", 120, 15),
                    ("Niveau cuve", "%", 78, 10), ("pH", "", 4.2, 0.3)]},
        {"id": "HG-01", "name": "Homogénéisateur", "brand": "GEA", "model": "Ariete NS3006",
         "stage": "fabrication", "protocol": "Modbus TCP", "cal_due": 88,
         "params": [("Pression", "bar", 150, 20), ("Température", "°C", 30.0, 4.0)]},
        {"id": "FL-01", "name": "Remplisseuse liquide", "brand": "Marchesini", "model": "ML630",
         "stage": "conditionnement", "protocol": "Siemens S7 / PROFINET", "cal_due": 18,
         "params": [("Volume remplissage", "mL", 200, 3), ("Cadence", "flacons/min", 45, 6),
                    ("Rejets", "u", 2, 4)]},
        {"id": "CP-01", "name": "Boucheuse", "brand": "Marchesini", "model": "MC-500",
         "stage": "conditionnement", "protocol": "Siemens S7", "cal_due": 120,
         "params": [("Couple de bouchage", "Nm", 1.4, 0.2)]},
        {"id": "LB-01", "name": "Étiqueteuse", "brand": "HERMA", "model": "400",
         "stage": "conditionnement", "protocol": "EtherNet/IP", "cal_due": 61,
         "params": [("Vérif. étiquette", "%", 99.5, 1.0), ("Cadence", "u/min", 46, 6)]},
    ],
    "capsule": [
        {"id": "BL-02", "name": "Mélangeur de poudre", "brand": "Diosna", "model": "P100",
         "stage": "fabrication", "protocol": "OPC UA", "cal_due": 40,
         "params": [("Vitesse", "rpm", 22, 3), ("Temps de mélange", "min", 15, 2),
                    ("Température", "°C", 23.0, 3.0)]},
        {"id": "CF-01", "name": "Gélatineuse (capsule filler)", "brand": "IMA", "model": "Zanasi 40E",
         "stage": "conditionnement", "protocol": "OPC UA / PROFINET", "cal_due": 14,
         "params": [("Cadence", "gél./min", 850, 60), ("Poids gélule", "mg", 500, 12),
                    ("Rejets", "u", 14, 25), ("Codes erreur", "", 0, 2)]},
        {"id": "DD-01", "name": "Dépoussiéreur", "brand": "IMA", "model": "Deduster",
         "stage": "conditionnement", "protocol": "Modbus TCP", "cal_due": 102,
         "params": [("Gélules rejetées", "u", 9, 22)]},
        {"id": "PT-01", "name": "Compteuse / remplisseuse pilulier", "brand": "MG2", "model": "G140",
         "stage": "conditionnement", "protocol": "Siemens S7", "cal_due": 70,
         "params": [("Précision comptage", "%", 99.8, 0.8), ("Cadence", "pil./min", 12, 2)]},
        {"id": "LB-01", "name": "Étiqueteuse", "brand": "HERMA", "model": "400",
         "stage": "conditionnement", "protocol": "EtherNet/IP", "cal_due": 61,
         "params": [("Vérif. étiquette", "%", 99.6, 1.0)]},
    ],
}


def line_for(product_name: str) -> str:
    p = (product_name or "").lower()
    return "capsule" if ("gelul" in p or "gélul" in p or "spirul" in p or "capsule" in p) else "liquid"


def _telemetry(spec):
    label, unit, nom, tol = spec
    v = nom + random.gauss(0, tol / 3.0) if tol else nom
    v = max(0, v)
    v = round(v, 2 if abs(nom) < 10 else 1)
    ok = abs(v - nom) <= tol + 1e-9
    return {"label": label, "unit": unit, "value": v, "nominal": nom, "tol": tol, "ok": ok}


def snapshot(product_name: str) -> dict:
    """Live-ish machine snapshot for the batch's production line."""
    line = line_for(product_name)
    machines = []
    for m in CATALOG[line]:
        tel = [_telemetry(s) for s in m["params"]]
        any_out = any(not t["ok"] for t in tel)
        cal_soon = m["cal_due"] < 30
        status = "alarm" if any_out else ("warning" if cal_soon else "running")
        machines.append({
            "id": m["id"], "name": m["name"], "brand": m["brand"], "model": m["model"],
            "stage": m["stage"], "protocol": m["protocol"],
            "cal_due_days": m["cal_due"], "cal_ok": m["cal_due"] > 0, "cal_soon": cal_soon,
            "cal_date": (TODAY + _dt.timedelta(days=m["cal_due"])).isoformat(),
            "status": status, "telemetry": tel,
        })
    summary = {
        "line": line, "count": len(machines),
        "running": sum(1 for m in machines if m["status"] == "running"),
        "warning": sum(1 for m in machines if m["status"] == "warning"),
        "alarm": sum(1 for m in machines if m["status"] == "alarm"),
    }
    return {"machines": machines, "summary": summary}


def facts(product_name: str) -> str:
    """Compact machine summary for the AI copilot context."""
    snap = snapshot(product_name)
    parts = [f"Ligne {snap['summary']['line']}, {snap['summary']['count']} machines"]
    for m in snap["machines"]:
        flags = []
        if m["status"] == "alarm":
            flags.append("ALARME: " + ", ".join(f"{t['label']} {t['value']}{t['unit']}" for t in m["telemetry"] if not t["ok"]))
        if m["cal_soon"]:
            flags.append(f"calibration due dans {m['cal_due_days']}j")
        parts.append(f"  - {m['id']} {m['name']} ({m['brand']} {m['model']}, {m['protocol']}): {m['status']}"
                     + ("; " + "; ".join(flags) if flags else ""))
    return "\n".join(parts)
