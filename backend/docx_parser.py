from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import List, Dict


def extract_docx_text(path: str | Path) -> str:
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith("document.xml"):
                text = zf.read(name).decode("utf-8", errors="ignore")
                text = re.sub(r"<[^>]+>", " ", text)
                return re.sub(r"\s+", " ", text).strip()
    return ""


def extract_docx_tasks(path: str | Path) -> List[Dict[str, str]]:
    text = extract_docx_text(path)
    if not text:
        return []

    upper = text.upper()
    # Classify on the TITLE only. Every dossier mentions "contrôle" somewhere in
    # its body, so scanning the whole text makes each one look like the DCT.
    head = upper[:300].replace("Ô", "O")
    if "CONDITIONNEMENT SECONDAIRE" in head:
        doc_key = "DCOII"
    elif "CONDITIONNEMENT PRIMAIRE" in head:
        doc_key = "DCOI"
    elif "DOSSIER DE FABRICATION" in head:
        doc_key = "DFA"
    elif "DOSSIER DE CONTROLE" in head:
        doc_key = "DCT"
    else:
        doc_key = "DOC"

    # Translation keys, not prose: the UI renders these in EN / FR / AR.
    tasks = []
    if "OPERATEURSDEMISEENBLISTERS" in upper or "MISE EN BLISTERS" in upper:
        tasks.append({"key": "task_blister"})
    if "MISE EN ETUIS" in upper or "MISE EN CAISSES" in upper:
        tasks.append({"key": "task_carton"})
    if "PESÉE" in upper or "PESEE" in upper or "VERIFICATION PREALABLE" in upper:
        tasks.append({"key": "task_weighing"})
    if ("CONTRÔLE" in upper or "CONTROLE" in upper) and "IPC" in upper:
        tasks.append({"key": "task_ipc"})
    if not tasks:
        tasks.append({"key": "task_generic"})
    for t in tasks:
        t["doc_key"] = doc_key
    return tasks
