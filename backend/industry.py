"""
Industry profiles -- what makes BatchTwin work outside pharma.

The GMP vocabulary was hardcoded: five French stage names, four Medicka
signatory roles, a fixed line-clearance checklist. That is fine for one customer
and fatal for a product, because a cosmetics or food manufacturer runs the same
*mechanics* (staged record, role-gated signatures, mass balance, deviations)
under different names and a different rulebook.

So the mechanics stay in code and the rulebook becomes data. A profile declares:

    stages          the lifecycle and the order it runs in
    roles           who exists, and which stage each may sign
    checklist       the line-clearance points
    terminology     what the customer calls a "lot", a "deviation", a "release"
    rules           tolerances and gates that differ by sector

Adding an industry is writing a profile, not editing the engine. Switching
profile never rewrites history: existing batches keep the stages they were
created with.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROFILE_DIR = Path(__file__).with_name("profiles")


# ---------------------------------------------------------------------------
# Built-in profiles. A customer can drop a JSON file in profiles/ to add theirs.
# ---------------------------------------------------------------------------
PHARMA_GMP = {
    "key": "pharma_gmp",
    "label": "Pharmaceutique / Complément alimentaire (GMP)",
    "regulation": "EU GMP Annex 11 · FDA 21 CFR Part 11 · ALCOA+",
    "stages": [
        {"name": "fabrication", "label": "Fabrication", "doc": "DFA", "signer": "r_prod"},
        {"name": "cond_primaire", "label": "Conditionnement primaire", "doc": "DCOI", "signer": "r_prod"},
        {"name": "cond_secondaire", "label": "Conditionnement secondaire", "doc": "DCOII", "signer": "r_prod"},
        {"name": "qualite", "label": "Contrôle qualité", "doc": "DCT", "signer": "r_cq"},
        {"name": "liberation", "label": "Libération", "doc": None, "signer": "prt"},
    ],
    "roles": {
        "r_prod": "R. PROD — Responsable Production",
        "r_cq": "R. CQ — Responsable Contrôle Qualité",
        "smq": "SMQ — Assurance Qualité",
        "prt": "PRT — Pharmacien Responsable Technique",
    },
    "qa_roles": ["smq", "prt"],
    "change_requesters": ["r_prod", "smq", "prt"],
    "checklist": [
        "Zone de production vide du lot precedent",
        "Zone et equipements propres (nettoyage valide)",
        "Machine de remplissage operationnelle",
        "Cartons de matiere premiere sortis de la zone (securite)",
        "Documentation du lot presente et conforme",
    ],
    "terminology": {"batch": "Lot", "record": "Dossier de Lot",
                    "release": "Libération", "deviation": "Déviation"},
    "rules": {
        "minor_tolerance_pct": 5.0,      # in-range formula adjustment
        "packaging_variance_pct": 1.0,   # article reconciliation tolerance
        "qualification_lots": 3,         # parallel lots before cutover
        "require_packaging_recon": True,
        "require_password_each_signature": True,
    },
}

COSMETICS = {
    "key": "cosmetics",
    "label": "Cosmétique (ISO 22716)",
    "regulation": "ISO 22716 · Règlement (CE) 1223/2009",
    "stages": [
        {"name": "fabrication", "label": "Fabrication du vrac", "doc": "DFA", "signer": "r_prod"},
        {"name": "cond_primaire", "label": "Remplissage", "doc": "DCOI", "signer": "r_prod"},
        {"name": "qualite", "label": "Contrôle qualité", "doc": "DCT", "signer": "r_cq"},
        {"name": "liberation", "label": "Mise sur le marché", "doc": None, "signer": "smq"},
    ],
    "roles": {
        "r_prod": "Responsable Production",
        "r_cq": "Responsable Contrôle Qualité",
        "smq": "Responsable Assurance Qualité",
        "prt": "Personne Responsable (art. 4)",
    },
    "qa_roles": ["smq", "prt"],
    "change_requesters": ["r_prod", "smq", "prt"],
    "checklist": [
        "Ligne vide du lot precedent",
        "Cuve et circuits nettoyes (proprete validee)",
        "Materiel de remplissage operationnel",
        "Matieres premieres identifiees et conformes",
    ],
    "terminology": {"batch": "Lot", "record": "Dossier de Fabrication",
                    "release": "Mise sur le marché", "deviation": "Anomalie"},
    "rules": {
        "minor_tolerance_pct": 5.0,
        "packaging_variance_pct": 2.0,
        "qualification_lots": 2,
        "require_packaging_recon": True,
        # ISO 22716 does not impose Part 11 e-signatures; keep them but do not
        # force the password challenge unless the customer wants it.
        "require_password_each_signature": False,
    },
}

FOOD_HACCP = {
    "key": "food_haccp",
    "label": "Agroalimentaire (HACCP / IFS)",
    "regulation": "Règlement (CE) 852/2004 · HACCP · IFS Food",
    "stages": [
        {"name": "fabrication", "label": "Production", "doc": "DFA", "signer": "r_prod"},
        {"name": "cond_primaire", "label": "Conditionnement", "doc": "DCOI", "signer": "r_prod"},
        {"name": "qualite", "label": "Contrôle CCP", "doc": "DCT", "signer": "r_cq"},
        {"name": "liberation", "label": "Libération", "doc": None, "signer": "smq"},
    ],
    "roles": {
        "r_prod": "Chef de production",
        "r_cq": "Responsable qualité",
        "smq": "Responsable HACCP",
        "prt": "Directeur qualité",
    },
    "qa_roles": ["smq", "prt"],
    "change_requesters": ["r_prod", "smq", "prt"],
    "checklist": [
        "Ligne vide du lot precedent",
        "Nettoyage et desinfection realises",
        "Temperatures CCP conformes",
        "Absence de corps etrangers (controle visuel)",
    ],
    "terminology": {"batch": "Lot", "record": "Dossier de production",
                    "release": "Libération", "deviation": "Non-conformité"},
    "rules": {
        "minor_tolerance_pct": 10.0,     # food recipes tolerate wider adjustment
        "packaging_variance_pct": 3.0,
        "qualification_lots": 2,
        "require_packaging_recon": False,
        "require_password_each_signature": False,
    },
}

MEDICAL_DEVICE = {
    "key": "medical_device",
    "label": "Dispositif médical (ISO 13485)",
    "regulation": "ISO 13485 · MDR (UE) 2017/745 · 21 CFR Part 820",
    "stages": [
        {"name": "fabrication", "label": "Fabrication", "doc": "DFA", "signer": "r_prod"},
        {"name": "cond_primaire", "label": "Conditionnement stérile", "doc": "DCOI", "signer": "r_prod"},
        {"name": "cond_secondaire", "label": "Conditionnement secondaire", "doc": "DCOII", "signer": "r_prod"},
        {"name": "qualite", "label": "Contrôle et essais", "doc": "DCT", "signer": "r_cq"},
        {"name": "liberation", "label": "Libération (DHR)", "doc": None, "signer": "prt"},
    ],
    "roles": {
        "r_prod": "Responsable Production",
        "r_cq": "Responsable Contrôle Qualité",
        "smq": "Responsable Système Qualité",
        "prt": "Responsable Réglementaire",
    },
    "qa_roles": ["smq", "prt"],
    "change_requesters": ["r_prod", "smq", "prt"],
    "checklist": [
        "Zone vide du lot precedent",
        "Environnement controle conforme (particules, pression)",
        "Equipements qualifies et etalonnes",
        "Composants identifies et traçables",
    ],
    "terminology": {"batch": "Lot", "record": "Device History Record (DHR)",
                    "release": "Libération", "deviation": "Non-conformité"},
    "rules": {
        "minor_tolerance_pct": 2.0,      # tightest: device tolerances are narrow
        "packaging_variance_pct": 0.5,
        "qualification_lots": 3,
        "require_packaging_recon": True,
        "require_password_each_signature": True,
    },
}

BUILTIN = {p["key"]: p for p in (PHARMA_GMP, COSMETICS, FOOD_HACCP, MEDICAL_DEVICE)}
DEFAULT_KEY = "pharma_gmp"

REQUIRED = ("key", "label", "stages", "roles", "qa_roles", "checklist", "rules")


class ProfileError(ValueError):
    pass


def validate(p: dict) -> dict:
    """Refuse a profile that would produce an unusable or unsafe lifecycle."""
    for field in REQUIRED:
        if not p.get(field):
            raise ProfileError(f"profil incomplet: '{field}' manquant")
    names = [s["name"] for s in p["stages"]]
    if len(set(names)) != len(names):
        raise ProfileError("noms d'etapes dupliques")
    if names[-1] != "liberation":
        raise ProfileError("la derniere etape doit etre 'liberation'")
    for s in p["stages"]:
        if s["signer"] not in p["roles"]:
            raise ProfileError(f"l'etape '{s['name']}' est signee par un role inconnu: {s['signer']}")
    for r in p["qa_roles"]:
        if r not in p["roles"]:
            raise ProfileError(f"role AQ inconnu: {r}")
    if not p["qa_roles"]:
        raise ProfileError("au moins un role d'assurance qualite est obligatoire")
    return p


def load(key: str | None = None) -> dict:
    """Built-in profile, or a customer profile dropped into backend/profiles/."""
    key = key or DEFAULT_KEY
    if key in BUILTIN:
        return validate(dict(BUILTIN[key]))
    path = PROFILE_DIR / f"{key}.json"
    if not path.exists():
        raise ProfileError(f"profil inconnu: {key}")
    return validate(json.loads(path.read_text(encoding="utf-8")))


def available() -> list[dict]:
    out = [{"key": k, "label": v["label"], "regulation": v.get("regulation", ""),
            "stages": len(v["stages"]), "builtin": True} for k, v in BUILTIN.items()]
    if PROFILE_DIR.exists():
        for path in sorted(PROFILE_DIR.glob("*.json")):
            try:
                p = validate(json.loads(path.read_text(encoding="utf-8")))
            except (ProfileError, json.JSONDecodeError):
                continue
            if p["key"] not in BUILTIN:
                out.append({"key": p["key"], "label": p["label"],
                            "regulation": p.get("regulation", ""),
                            "stages": len(p["stages"]), "builtin": False})
    return out


# --- derived views the engine consumes -------------------------------------
def stage_names(p: dict) -> list[str]:
    return [s["name"] for s in p["stages"]]


def stage_signer(p: dict) -> dict[str, str]:
    return {s["name"]: s["signer"] for s in p["stages"]}


def stage_doc(p: dict) -> dict[str, str]:
    return {s["name"]: s["doc"] for s in p["stages"] if s.get("doc")}


def rule(p: dict, name: str, default: Any = None) -> Any:
    return p.get("rules", {}).get(name, default)
