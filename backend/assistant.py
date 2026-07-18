"""
BatchTwin AI copilot — Challenge 3 (operator assistant) + Challenge 8 (generative
reports / root-cause), running fully local on Ollama.

Grounding = real RAG:
  * a small GMP procedure corpus (SOPs) embedded with `nomic-embed-text` and
    retrieved by cosine similarity, PLUS
  * the LIVE state of the batch (gating, deviations, mass balance, SPC, energy),
    formatted as facts the model must answer from.

Nothing leaves the machine — no cloud, no API key. If Ollama is down the API
degrades gracefully instead of crashing.
"""
from __future__ import annotations
import json
import math
import os
import urllib.request
import urllib.error

from . import store, analytics

OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
CHAT_MODEL = os.environ.get("BATCHTWIN_MODEL", "llama3.2")
EMBED_MODEL = os.environ.get("BATCHTWIN_EMBED", "nomic-embed-text")

# --- GMP procedure corpus (the knowledge the copilot retrieves over) ---------
SOP = [
    ("vide-de-ligne",
     "Vide de ligne (line clearance) : avant tout demarrage, verifier que la zone est vide "
     "du lot precedent, propre et validee, la machine de remplissage operationnelle, les cartons "
     "de matiere premiere sortis de la zone, et la documentation du lot presente. Toute anomalie "
     "est escaladee au responsable de production avant demarrage."),
    ("pesee-bilan",
     "Pesee et bilan matiere : chaque matiere premiere est pesee selon la nomenclature. La perte "
     "(poussiere en suspension, gouttes) est saisie separement. Une perte superieure a 1,5% sur "
     "une ligne doit etre investiguee (contenant, methode de transfert, calibration balance)."),
    ("contenance-spc",
     "Controle contenance : toutes les 30 minutes, prelever 10 flacons et mesurer le remplissage. "
     "La carte de controle X-barre applique les regles Western Electric ; une derive prevue vers la "
     "limite basse annonce un sous-remplissage. Action : ajuster la remplisseuse immediatement pour "
     "eviter le rebut et la non-conformite d'etiquetage."),
    ("liberation-gating",
     "Liberation du lot : le lot ne peut etre libere que si les quatre etapes (fabrication, "
     "conditionnement, qualite, liberation) sont signees et si tous les controles contenance sont "
     "conformes. La liberation est reservee au role Assurance Qualite."),
    ("energie-co2",
     "Energie et empreinte carbone : les capteurs IoT mesurent la consommation de chaque poste. "
     "L'energie du lot est repartie sur les quatre dossiers et convertie en CO2 via le facteur reseau. "
     "Un poste anormalement energivore signale une maintenance ou un reglage."),
    ("integrite-alcoa",
     "Integrite des donnees (ALCOA+ / 21 CFR Part 11) : chaque action est horodatee, attribuee a un "
     "utilisateur et scellee dans une piste d'audit chainee par hash. Toute modification ulterieure "
     "rompt la chaine et est detectee. Les signatures electroniques attestent d'une revue humaine."),
    ("deviation-capa",
     "Deviation et CAPA : toute non-conformite (controle hors tolerance, perte excessive, anomalie "
     "vide de ligne) doit etre documentee, sa cause racine identifiee, et un plan d'action correctif "
     "et preventif (CAPA) propose avant liberation."),
    # --- VERA inventory / supply-chain procedures ---
    ("point-de-commande",
     "Point de commande (reorder point) : commander quand le stock projete passe sous "
     "conso_moyenne x delai_fournisseur + stock_de_securite. Le stock de securite couvre la "
     "variabilite de la demande et du delai (facteur de service 1,65 pour 95%). Si la rupture est "
     "prevue avant la fin du delai, il faut expedier en urgence."),
    ("fefo-peremption",
     "FEFO (First-Expiry-First-Out) : consommer en priorite les lots qui perimeront le plus tot. "
     "Un lot dont la quantite restante depasse la consommation prevue avant sa date de peremption "
     "sera detruit (perte seche). Action : ne pas recommander, reduire les commandes futures, "
     "ecouler par promotion ou transfert."),
    ("besoin-reel-vera",
     "Besoin reel vs theorique : l'ERP deduit les quantites theoriques de la nomenclature et ignore "
     "les pertes de process. Le besoin reel = theorique x (1 + taux_de_perte). Ne pas corriger ce "
     "biais entraine un sous-approvisionnement chronique et des ruptures surprises sur les matieres "
     "a fort taux de perte."),
    ("lean-jit",
     "Lean / juste-a-temps : minimiser le stock immobilise et les pertes tout en garantissant la "
     "disponibilite. On arbitre le cout total = possession + rupture + peremption. Les matieres "
     "importees a long delai exigent plus de stock de securite ; les perissables exigent des "
     "commandes plus petites et frequentes."),
]
_EMB_CACHE: dict[str, list[float]] | None = None


class AssistantOffline(RuntimeError):
    pass


def fr_qty(v):
    return ("%g" % v)


def _post(path: str, payload: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(OLLAMA + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise AssistantOffline(str(e))


def health() -> dict:
    try:
        req = urllib.request.Request(OLLAMA + "/api/tags")
        with urllib.request.urlopen(req, timeout=4) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
        return {"available": True, "chat_model": CHAT_MODEL, "embed_model": EMBED_MODEL, "models": models}
    except Exception:
        return {"available": False, "chat_model": CHAT_MODEL}


def _embed(text: str) -> list[float]:
    out = _post("/api/embeddings", {"model": EMBED_MODEL, "prompt": text}, timeout=30)
    return out["embedding"]


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _retrieve(query: str, k: int = 3) -> list[tuple[str, str]]:
    global _EMB_CACHE
    if _EMB_CACHE is None:
        _EMB_CACHE = {sid: _embed(text) for sid, text in SOP}
    qv = _embed(query)
    scored = sorted(((_cos(qv, _EMB_CACHE[sid]), sid, text) for sid, text in SOP),
                    key=lambda x: x[0], reverse=True)
    return [(sid, text) for _, sid, text in scored[:k]]


# --- live batch facts (the other half of grounding) --------------------------
def batch_facts(batch_id: int) -> tuple[str, list[str]]:
    b = store.get_batch(batch_id)
    if not b:
        raise ValueError("batch not found")
    mb = analytics.mass_balance(b["dispense"])
    kpis = analytics.batch_kpis(b, mb, b.get("good_units"))
    lo = (b["target_fill_g"] or 0) - (b["fill_tol_g"] or 0)
    hi = (b["target_fill_g"] or 0) + (b["fill_tol_g"] or 0)
    spc = analytics.spc(b["qc"], b["target_fill_g"], lo, hi)
    energy = analytics.energy_summary(b["energy"], b.get("good_units"))

    signed = {s["name"] for s in b["stages"] if s["status"] == "signed"}
    missing = [s["name"] for s in b["stages"] if s["status"] != "signed"]
    qc_fail = sum(1 for s in b["qc"] if s["verdict"] == "FAIL")
    deviations = []
    if qc_fail:
        deviations.append(f"{qc_fail} controle(s) contenance HORS TOLERANCE")
    if spc.get("forecast"):
        f = spc["forecast"]
        deviations.append(f"derive contenance prevue vers {f['toward']} dans ~{f['minutes_to_spec_breach']:.0f} min")
    for l in mb["lines"]:
        if l["loss_pct"] is not None and l["loss_pct"] > 1.5:
            deviations.append(f"perte elevee {l['loss_pct']:.1f}% sur {l['material']}")
    for c in b["checklist"]:
        if c["ok"] == 0:
            deviations.append(f"vide de ligne non conforme: {c['label']}")

    materials = ", ".join(f"{l['material']} ({fr_qty(l['target'])} {l['unit']})" for l in mb["lines"])
    lines = [
        f"Lot: {b['lot_name']} | produit: {b['product']} | etat: {b['state']}",
        f"Cible: {b['qty_target']} unites, contenance {b['target_fill_g']} {b.get('fill_unit') or 'mL'} +/- {b['fill_tol_g']} {b.get('fill_unit') or 'mL'}",
        f"Matieres premieres et articles (nomenclature): {materials}",
        f"Etapes signees: {sorted(signed) or 'aucune'} | manquantes: {missing or 'aucune'}",
        f"Bilan matiere: cout theorique {mb['theoretical_cost']} EUR, "
        f"reel {mb['real_cost']} EUR, perte {mb['loss_cost']} EUR" if mb["complete"] else "Bilan matiere: pesee incomplete",
        f"Rendement: {kpis['yield_pct']}% | cout matiere reel/unite: {kpis['true_unit_material_cost']} EUR",
        f"Controle contenance: {len(b['qc'])} releves, {qc_fail} hors tolerance",
        f"Energie: {energy['total_kwh']} kWh, {energy['total_co2_kg']} kg CO2, "
        f"{energy['co2_g_per_unit']} g CO2/unite" if energy["complete"] else "Energie: non renseignee",
        f"Deviations detectees: {deviations or 'aucune'}",
    ]
    from . import equipment
    lines.append("=== EQUIPEMENTS (jumeau numerique) ===\n" + equipment.facts(b["product"]))
    return "\n".join(lines), deviations


SYSTEM = (
    "You are the GMP copilot of BatchTwin for the Medicka Laboratories plant (food supplements). "
    "You assist operators and quality assurance. Be brief, concrete and actionable. "
    "Base your answer ONLY on the provided CONTEXT (live batch state + procedures). "
    "If information is missing, say so instead of inventing. For any non-conformity, propose a concrete action."
)
LANG_NAME = {"en": "English", "fr": "French", "ar": "Arabic"}


def _lang_line(lang: str) -> str:
    return f"\nIMPORTANT: respond STRICTLY in {LANG_NAME.get(lang, 'French')}."


def chat(batch_id: int, message: str, history: list[dict] | None = None, lang: str = "fr") -> dict:
    facts, _ = batch_facts(batch_id)
    docs = _retrieve(message, k=3)
    sources = [sid for sid, _ in docs]
    kb = "\n\n".join(f"[{sid}] {text}" for sid, text in docs)
    context = f"=== ETAT DU LOT (donnees en direct) ===\n{facts}\n\n=== PROCEDURES PERTINENTES ===\n{kb}"
    msgs = [{"role": "system", "content": SYSTEM + _lang_line(lang) + "\n\n" + context}]
    for h in (history or [])[-4:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": message})
    out = _post("/api/chat", {"model": CHAT_MODEL, "stream": False, "messages": msgs,
                              "options": {"temperature": 0.2}})
    return {"answer": out["message"]["content"].strip(), "sources": sources}


VERA_SYSTEM = (
    "Tu es VERA, le copilote d'approvisionnement de Medicka Laboratories. Tu aides a decider quoi "
    "commander, combien et quand, en evitant a la fois les ruptures et les pertes par peremption. "
    "Reponds en francais, bref et actionnable. Base-toi UNIQUEMENT sur le CONTEXTE (etat des stocks "
    "et decisions calculees + procedures). Chiffre tes recommandations. Si l'info manque, dis-le."
)


def vera_facts() -> str:
    from . import inventory
    v = inventory.VERA
    k = v.kpis()
    lines = [
        f"Horizon d'analyse: {k['horizon']} jours. Matieres suivies: {k['materials_total']}.",
        f"Biais ERP (besoin reel vs theorique): +{k['truth_gap_pct']}% soit ~{k['truth_gap_eur']} EUR/an sous-comptes.",
        f"Ruptures urgentes (avant fin du delai fournisseur): {k['urgent_count']} "
        f"(la plus proche J+{k['urgent_soonest']}).",
        f"A commander cette semaine: {k['order_now_count']} matieres.",
        f"Valeur menacee de peremption: {k['expiry_value']} EUR. Stock dormant (>180j): {k['dead_stock_value']} EUR.",
        f"Valeur totale du stock matieres: {k['inventory_value']} EUR.",
        "Decisions prioritaires:",
    ]
    for r in v.decision_queue()[:6]:
        lines.append(f"  - [{r['action']}] {r['name']}: {r['qty']} {r['unit']} d'ici J+{r['order_by_day']} "
                     f"(~{r['value']} EUR, {r['supplier']}) — {r['reason']}")
    return "\n".join(lines)


def vera_chat(message: str, history: list[dict] | None = None) -> dict:
    facts = vera_facts()
    docs = _retrieve(message, k=3)
    sources = [sid for sid, _ in docs]
    kb = "\n\n".join(f"[{sid}] {text}" for sid, text in docs)
    context = f"=== ETAT DES STOCKS & DECISIONS (calcul en direct) ===\n{facts}\n\n=== PROCEDURES ===\n{kb}"
    msgs = [{"role": "system", "content": VERA_SYSTEM + "\n\n" + context}]
    for h in (history or [])[-4:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": message})
    out = _post("/api/chat", {"model": CHAT_MODEL, "stream": False, "messages": msgs,
                              "options": {"temperature": 0.2}})
    return {"answer": out["message"]["content"].strip(), "sources": sources}


def chat_stream(batch_id: int, message: str, history: list[dict] | None = None, lang: str = "fr"):
    """Same grounding as chat(), but streams tokens from Ollama as they arrive.
    Returns (sources, generator) so the API can put sources in a header."""
    facts, _ = batch_facts(batch_id)
    docs = _retrieve(message, k=3)          # may raise AssistantOffline before streaming
    sources = [sid for sid, _ in docs]
    kb = "\n\n".join(f"[{sid}] {text}" for sid, text in docs)
    context = f"=== ETAT DU LOT (donnees en direct) ===\n{facts}\n\n=== PROCEDURES PERTINENTES ===\n{kb}"
    msgs = [{"role": "system", "content": SYSTEM + _lang_line(lang) + "\n\n" + context}]
    for h in (history or [])[-4:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": message})
    payload = {"model": CHAT_MODEL, "stream": True, "messages": msgs, "options": {"temperature": 0.2}}
    req = urllib.request.Request(OLLAMA + "/api/chat", json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})

    def gen():
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                for line in r:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    tok = obj.get("message", {}).get("content", "")
                    if tok:
                        yield tok
                    if obj.get("done"):
                        break
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            yield "\n⚠ connexion interrompue avec l'assistant local."

    return sources, gen


def generate_report(batch_id: int, lang: str = "fr") -> dict:
    """Challenge 8: auto-generate a batch deviation / release summary."""
    facts, deviations = batch_facts(batch_id)
    prompt = (
        f"Write a concise, professional BATCH RECORD SUMMARY (GMP format) in {LANG_NAME.get(lang, 'French')}, "
        "from the data below. Structure: 1) Summary, 2) Deviations and likely root causes, "
        "3) Corrective actions (CAPA), 4) Release recommendation (yes/no and why). "
        "Be factual and rely only on the data.\n\n=== BATCH DATA ===\n" + facts
    )
    out = _post("/api/chat", {"model": CHAT_MODEL, "stream": False,
                              "messages": [{"role": "system", "content": SYSTEM + _lang_line(lang)},
                                           {"role": "user", "content": prompt}],
                              "options": {"temperature": 0.3}})
    return {"report": out["message"]["content"].strip(), "deviations": deviations}
