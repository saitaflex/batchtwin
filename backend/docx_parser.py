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

    lowered = text.upper()
    title = ""
    if "Dossier de conditionnement primaire" in text or "DCOI" in text.upper():
        title = "Primary packaging workflow"
    elif "Dossier de conditionnement secondaire" in text or "DCOII" in text.upper():
        title = "Secondary packaging workflow"
    elif "Dossier de fabrication" in text or "DFA" in text.upper():
        title = "Manufacturing workflow"
    elif "Dossier de contrôle" in text or "DCT" in text.upper():
        title = "Quality control workflow"
    else:
        title = "Document workflow"

    tasks = []
    if "OPERATEURSDEMISEENBLISTERS" in lowered or "mise en blisters" in lowered:
        tasks.append({"title": "Primary packaging line clearance", "detail": "Verify the primary packaging line, maintain the blisters and aluminium roll setup, and confirm the operator log is complete."})
    if "mise en etuis" in lowered or "mise en caisses" in lowered:
        tasks.append({"title": "Secondary packaging handoff", "detail": "Confirm carton and label availability, verify the pack-out sequence, and complete the secondary packaging sign-off."})
    if "pesée" in lowered or "verification prealable" in lowered:
        tasks.append({"title": "Weighing and line preparation", "detail": "Complete the pre-use verification, weigh the active ingredients, and attach the required release evidence."})
    if "contrôle" in lowered and "ipc" in lowered:
        tasks.append({"title": "In-process quality review", "detail": "Review the IPC checks, confirm sampling and acceptance criteria, and escalate any deviation before release."})
    if not tasks:
        tasks.append({"title": title, "detail": "Review the source dossier and close the corresponding GMP step before release."})
    return tasks
