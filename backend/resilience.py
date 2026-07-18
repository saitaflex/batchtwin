"""
Failure modes, and what the system does about them.

A GMP auditor does not ask whether the happy path works. They ask what happens
when the sensor dies mid-batch, when the power drops, when Odoo is unreachable,
when the tablet battery goes flat with half a weighing entered.

The governing rule is stated once and applied everywhere below:

    **Losing an instrument must never block production, and must never let an
    unverified value enter the record silently.**

Those two together force the same answer every time: degrade to a manual entry
that is explicitly marked as manual, keep going, and make the gap visible to QA
at release. A system that halts the line on a dead sensor gets unplugged; a
system that guesses gets a warning letter.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

# A reading older than this is not "the last value", it is silence. Telemetry
# that stops must be reported as stale rather than displayed as if it were live:
# a frozen number on a screen is worse than a blank one.
STALE_AFTER_S = 120
DEAD_AFTER_S = 600

SOURCES = {
    "iot": "Capteur (automatique)",
    "manual": "Saisie manuelle (capteur indisponible)",
    "estimate": "Estimation (a justifier)",
}

# Every failure the audit raised, with the answer the system actually implements.
# Referenced by docs/RESILIENCE.md so the two cannot drift apart.
FAILURE_MODES = [
    {
        "id": "sensor_dead",
        "event": "Un capteur IoT tombe en panne pendant la production",
        "detect": "Aucune lecture depuis 120 s -> 'stale'; 600 s -> 'dead'",
        "behaviour": "La production continue. Le champ bascule en saisie manuelle "
                     "et la valeur est marquee source='manual'.",
        "record": "La source est imprimee dans le dossier: QA voit exactement "
                  "quelles valeurs sont automatiques et lesquelles sont saisies.",
        "recovery": "Le capteur revient -> les lectures reprennent en 'iot'. "
                    "Aucune valeur manuelle n'est ecrasee retroactivement.",
        "blocks_release": False,
    },
    {
        "id": "power_loss",
        "event": "Coupure electrique",
        "detect": "Perte de connexion du client; le serveur ne recoit plus rien",
        "behaviour": "SQLite est en WAL avec synchronous=NORMAL: une transaction "
                     "commitee survit. Une transaction en cours est annulee "
                     "entierement -- jamais a moitie ecrite.",
        "record": "Le journal d'audit est chaine: une coupure ne laisse pas de "
                  "trou silencieux, la chaine reste verifiable.",
        "recovery": "Redemarrage: l'operateur reprend le lot au dernier etat "
                    "commite. La file hors-ligne du client rejoue ce qui manque.",
        "blocks_release": False,
    },
    {
        "id": "network_loss",
        "event": "Le Wi-Fi disparait dans l'atelier",
        "detect": "navigator.onLine + echec des appels reseau",
        "behaviour": "La saisie continue et part dans une file locale idempotente "
                     "(op_id). LA SIGNATURE EST REFUSEE: verifier un mot de passe "
                     "hors ligne imposerait de mettre en cache des identifiants.",
        "record": "client_at conserve l'heure reelle de l'acte (ALCOA+ "
                  "Contemporaneous), distincte de l'heure de synchronisation.",
        "recovery": "Retour du reseau -> rejeu automatique, doublons ignores.",
        "blocks_release": False,
    },
    {
        "id": "odoo_down",
        "event": "Odoo est indisponible",
        "detect": "Timeout ou erreur XML-RPC a l'ouverture d'un lot",
        "behaviour": "Les lots deja ouverts continuent normalement: BatchTwin ne "
                     "depend d'Odoo que pour CREER un lot depuis un OF. "
                     "L'integration est en lecture seule, donc Odoo ne peut pas "
                     "etre corrompu par une panne de notre cote.",
        "record": "Aucune donnee perdue; la creation de lot est simplement "
                  "reportee ou saisie manuellement.",
        "recovery": "Odoo revient -> reprise immediate, rien a reconcilier.",
        "blocks_release": False,
    },
    {
        "id": "scan_fail",
        "event": "Le code-barres ne se lit pas (etiquette abimee, camera HS)",
        "detect": "Aucun code detecte apres 25 s",
        "behaviour": "Le champ reste saisissable au clavier. Le scan n'est jamais "
                     "un passage oblige -- c'est un raccourci.",
        "record": "Identique: la valeur est la meme, seule la methode differe.",
        "recovery": "Aucune action requise.",
        "blocks_release": False,
    },
    {
        "id": "tablet_dead",
        "event": "La batterie de la tablette lache en pleine pesee",
        "detect": "Session interrompue",
        "behaviour": "Chaque champ est enregistre a la saisie, pas a la validation "
                     "d'un formulaire: seule la frappe en cours est perdue.",
        "record": "L'operateur se reconnecte sur n'importe quelle tablette et "
                  "retrouve le lot exactement ou il en etait.",
        "recovery": "Reconnexion. La file hors-ligne du poste mort est rejouee "
                    "quand il redemarre, sans doublon.",
        "blocks_release": False,
    },
    {
        "id": "no_phone_allowed",
        "event": "Les telephones sont interdits en zone de production",
        "detect": "Contrainte du site, pas une panne",
        "behaviour": "Le mode poste (/floor) fonctionne sur une tablette fixe "
                     "lavable montee sur la ligne. Le scan est optionnel; toute "
                     "la saisie se fait au doigt sur des cibles de 44 px.",
        "record": "Identique.",
        "recovery": "Sans objet.",
        "blocks_release": False,
    },
    {
        "id": "server_down",
        "event": "Le serveur BatchTwin tombe",
        "detect": "Le client recoit une erreur reseau",
        "behaviour": "La saisie continue hors ligne. La signature attend. Si "
                     "l'arret se prolonge, le site REPREND LE PAPIER pour le lot "
                     "en cours -- c'est la procedure de secours, et elle est "
                     "documentee dans le plan de migration.",
        "record": "Le lot papier devient l'enregistrement legal de ce lot; il est "
                  "reference dans BatchTwin a la reprise.",
        "recovery": "Restauration depuis la sauvegarde; le journal d'ancrage "
                    "externe confirme que la base restauree n'a pas ete alteree.",
        "blocks_release": False,
    },
]


def reading_health(last_seen_iso: str | None, now: _dt.datetime | None = None) -> dict:
    """Classify a telemetry channel: live, stale, dead, or never seen.

    A screen that keeps showing the last known number when the sensor has
    stopped is actively dangerous -- the operator has no way to tell.
    """
    if not last_seen_iso:
        return {"state": "never", "age_s": None, "label": "Aucune lecture",
                "usable": False}
    now = now or _dt.datetime.now().astimezone()
    try:
        seen = _dt.datetime.fromisoformat(last_seen_iso)
    except ValueError:
        return {"state": "never", "age_s": None, "label": "Horodatage illisible",
                "usable": False}
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=now.tzinfo)
    age = (now - seen).total_seconds()
    if age <= STALE_AFTER_S:
        return {"state": "live", "age_s": round(age), "label": "En direct", "usable": True}
    if age <= DEAD_AFTER_S:
        return {"state": "stale", "age_s": round(age),
                "label": f"Silencieux depuis {round(age)} s", "usable": False}
    return {"state": "dead", "age_s": round(age),
            "label": f"Hors service depuis {round(age / 60)} min", "usable": False}


def manual_entry_required(health: dict) -> bool:
    """Should the UI offer a manual field instead of a live value?"""
    return health["state"] in ("stale", "dead", "never")


def batch_data_provenance(batch: dict) -> dict:
    """How much of this lot was captured automatically vs typed in.

    QA needs this at release: a lot where every energy reading was typed by hand
    is not the same evidence as one metered end to end, even if both are complete.
    """
    energy = batch.get("energy") or []
    counts: dict[str, int] = {}
    for row in energy:
        counts[row.get("source") or "iot"] = counts.get(row.get("source") or "iot", 0) + 1
    total = sum(counts.values())
    auto = counts.get("iot", 0)
    return {
        "readings": total,
        "by_source": {k: {"n": v, "label": SOURCES.get(k, k)} for k, v in counts.items()},
        "automatic_pct": round(auto / total * 100) if total else None,
        "manual_present": any(k != "iot" for k in counts),
    }


def summary() -> dict:
    """The failure-mode table, for the UI and for an auditor who asks."""
    return {"modes": FAILURE_MODES, "stale_after_s": STALE_AFTER_S,
            "dead_after_s": DEAD_AFTER_S, "sources": SOURCES}
