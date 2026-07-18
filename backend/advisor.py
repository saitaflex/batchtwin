"""
Recovery advisor -- learns from what operators actually did, and what worked.

The evaluator asked for adaptive intelligence: recommend a recovery strategy
during a drift, informed by past operator adjustments. This does that WITHOUT a
trained model, and the choice is deliberate rather than a shortcut.

How it works: every deviation closed by QA carries a root cause, a CAPA and a
disposition. That is a case base written by the plant itself. When a new drift
appears, the advisor builds a signature for it -- product, machine, direction,
kind -- retrieves closed cases with the same signature, and reports what was
done and whether it held.

Why not a trained model:

  * **It cites its evidence.** Every recommendation names the lot, the date and
    the person who signed the CAPA. An operator can go and read that dossier.
    A learned model would say "0.83" and a GMP operator cannot act on 0.83.
  * **It is validatable.** The retrieval is a documented query. An inspector can
    follow it. Qualifying a trained model means qualifying its training data,
    versioning weights and re-proving behaviour after every retrain.
  * **It works from lot one.** No cold start, no dataset to collect. With no
    history it says so, instead of guessing.

It is adaptive in the sense that matters: the recommendations change as the
plant accumulates history, and an action that stopped recurrence outranks one
that did not.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

# A case is only worth quoting once QA has closed it -- an open deviation has no
# outcome yet, and an outcome is the entire point.
MIN_CASES_FOR_CONFIDENCE = 2
RECENCY_HALF_LIFE_DAYS = 365.0


def _age_days(iso: str | None) -> float:
    if not iso:
        return 9_999.0
    try:
        t = _dt.datetime.fromisoformat(iso)
    except ValueError:
        return 9_999.0
    now = _dt.datetime.now().astimezone()
    if t.tzinfo is None:
        t = t.replace(tzinfo=now.tzinfo)
    return max((now - t).total_seconds() / 86400.0, 0.0)


def _parse(iso: str | None) -> _dt.datetime | None:
    if not iso:
        return None
    try:
        t = _dt.datetime.fromisoformat(iso)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=_dt.datetime.now().astimezone().tzinfo)


def _after(a: str | None, b: str | None) -> bool:
    """Did `a` happen at or after `b`? Ties count as after, because a deviation
    opened in the same second as a closure is not evidence the fix worked."""
    ta, tb = _parse(a), _parse(b)
    return bool(ta and tb and ta >= tb)


def signature(deviation: dict, batch: dict, machine: str | None = None) -> dict:
    """What makes two problems 'the same problem'.

    Deliberately coarse: product + kind + title is what a supervisor means when
    they say "this again". Machine narrows it when we know which one.
    """
    spec = batch.get("product_spec") or {}
    return {
        "product_code": spec.get("code") or batch.get("product"),
        "kind": deviation.get("kind"),
        "title": (deviation.get("title") or "").strip(),
        "machine": machine,
    }


def _matches(sig: dict, case: dict) -> float:
    """0..1 similarity. Same title on the same product is a strong match; the
    same failure kind on a different product is weak but not nothing."""
    score = 0.0
    if case["kind"] == sig["kind"]:
        score += 0.4
    if case["title"] and case["title"] == sig["title"]:
        score += 0.4
    if sig["product_code"] and case["product_code"] == sig["product_code"]:
        score += 0.2
    return score


def _recency_weight(days: float) -> float:
    """Recent practice beats old practice: a CAPA from last month reflects the
    line as it is now, one from three years ago may predate a machine change."""
    return 0.5 ** (days / RECENCY_HALF_LIFE_DAYS)


def build_case_base(batches: list[dict]) -> list[dict]:
    """Every closed deviation, with whether the fix actually held.

    'Held' means: on later lots of the same product, the same deviation kind and
    title did not come back. That is the outcome signal, and it is what makes
    one recommendation better than another.
    """
    cases: list[dict] = []
    for b in batches:
        spec = b.get("product_spec") or {}
        code = spec.get("code") or b.get("product")
        for d in (b.get("deviations") or []):
            if d.get("status") != "closed":
                continue
            cases.append({
                "ref": d.get("ref"), "kind": d.get("kind"),
                "title": (d.get("title") or "").strip(),
                "severity": d.get("severity"),
                "product_code": code,
                "lot": b.get("lot_name"), "batch_id": b.get("id"),
                "root_cause": d.get("root_cause"), "capa": d.get("capa"),
                "disposition": d.get("disposition"),
                "closed_by": d.get("closed_by"), "closed_at": d.get("closed_at"),
                "opened_at": d.get("opened_at"),
            })

    # Did it come back after this CAPA was applied? Compare timestamps directly:
    # deriving order from "days ago" floats collapses when several events land
    # in the same second, which is exactly what happens on a seeded demo.
    for c in cases:
        recurred = [x for x in cases
                    if x["ref"] != c["ref"]
                    and x["product_code"] == c["product_code"]
                    and x["title"] == c["title"]
                    and _after(x["opened_at"], c["closed_at"])]
        c["recurred"] = len(recurred)
        c["held"] = not recurred
    return cases


def recommend(deviation: dict, batch: dict, batches: list[dict],
              machine: str | None = None, top: int = 3) -> dict:
    """What has this plant done before, and did it work?"""
    sig = signature(deviation, batch, machine)
    cases = [c for c in build_case_base(batches) if c["batch_id"] != batch.get("id")]

    scored = []
    for c in cases:
        sim = _matches(sig, c)
        if sim < 0.4:                       # unrelated: do not pad the list
            continue
        rec = _recency_weight(_age_days(c["closed_at"]))
        outcome = 1.0 if c["held"] else 0.35   # a fix that did not hold ranks low
        scored.append({**c, "similarity": round(sim, 2),
                       "score": round(sim * 0.5 + rec * 0.2 + outcome * 0.3, 3)})
    scored.sort(key=lambda c: -c["score"])
    hits = scored[:top]

    if not hits:
        return {"signature": sig, "cases": [], "confidence": "none",
                "recommendation": None,
                "note": "Aucun precedent dans l'historique de ce site. "
                        "La premiere cloture de ce type constituera la reference."}

    held = [c for c in hits if c["held"]]
    best = (held or hits)[0]
    confidence = ("high" if len(held) >= MIN_CASES_FOR_CONFIDENCE
                  else "medium" if held else "low")
    return {
        "signature": sig,
        "cases": hits,
        "confidence": confidence,
        "recommendation": {
            "root_cause": best["root_cause"],
            "capa": best["capa"],
            "disposition": best["disposition"],
            "from_lot": best["lot"], "from_ref": best["ref"],
            "closed_by": best["closed_by"], "closed_at": best["closed_at"],
            "held": best["held"], "recurred": best["recurred"],
        },
        "note": ("Propose a partir de l'historique du site, pas d'un modele. "
                 "Verifiez le dossier cite avant d'appliquer."),
    }


def drift_advice(spc: dict, batch: dict, batches: list[dict],
                 machine: str | None = None) -> dict | None:
    """Called when SPC forecasts a breach, BEFORE a deviation exists.

    This is the case the evaluator asked about: the chart is drifting, nothing
    has failed yet, and the operator wants to know what was done last time.
    """
    forecast = (spc or {}).get("forecast")
    if not forecast:
        return None
    toward = forecast.get("toward", "")
    pseudo = {
        "kind": "qc_fail",
        "title": "Controle contenance hors specification",
        "severity": "critical",
    }
    out = recommend(pseudo, batch, batches, machine)
    out["trigger"] = {
        "reason": "spc_drift",
        "toward": toward,
        "samples_to_breach": forecast.get("samples_to_spec_breach"),
        "minutes_to_breach": forecast.get("minutes_to_spec_breach"),
    }
    out["preemptive"] = True
    return out


def learning_stats(batches: list[dict]) -> dict:
    """How much this site has learned so far -- the honest measure of whether
    the advisor is worth listening to yet."""
    cases = build_case_base(batches)
    held = [c for c in cases if c["held"]]
    by_kind: dict[str, int] = {}
    for c in cases:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
    return {
        "cases": len(cases),
        "fixes_that_held": len(held),
        "effectiveness_pct": round(len(held) / len(cases) * 100) if cases else None,
        "by_kind": by_kind,
        "ready": len(cases) >= MIN_CASES_FOR_CONFIDENCE,
        "note": ("L'advisor s'ameliore a mesure que l'AQ cloture des deviations : "
                 "chaque cloture ajoute un cas reference."),
    }
