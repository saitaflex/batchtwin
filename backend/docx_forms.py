"""
Turn the real Medicka .docx dossiers into fillable digital forms.

The paper dossiers are Word tables where the blank cells (".........", "___ / ___",
"S NS", "C NC") are what an operator fills in with a pen. This module reads the
actual document.xml, keeps the table structure, and classifies every cell as
either a printed label or an input field -- so the app can render the very same
document on a tablet, with the same layout, and capture the answers.

Nothing here is hand-transcribed: change the .docx and the form changes with it.
"""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# A cell is "blank" once you strip the pen-guides Word uses: dot leaders,
# underscores, ellipses, non-breaking spaces and the odd private-use glyph.
_FILLER = re.compile(r"[.…_ \s-…·]+")
_DATE_PAT = re.compile(r"(_{2,}\s*/\s*_{2,})|(^\s*/\s*/\s*$)|(\d{2}\s*/\s*\d{2}\s*/)")
_TIME_PAT = re.compile(r"[…\.]{2,}\s*:\s*[…\.]{2,}|^\s*:\s*$")

DOC_TYPES = [
    ("DFA",   "fabrication",     "Dossier de Fabrication",
     ("DOSSIER DE FABRICATION",)),
    ("DCOI",  "cond_primaire", "Dossier de Conditionnement Primaire",
     ("DOSSIER DE CONDITIONNEMENT PRIMAIRE",)),
    ("DCOII", "cond_secondaire", "Dossier de Conditionnement Secondaire",
     ("DOSSIER DE CONDITIONNEMENT SECONDAIRE",)),
    ("DCT",   "qualite",         "Dossier de Controle Qualite",
     ("DOSSIER DE CONTROLE", "DOSSIER DE CONTRÔLE")),
]


def _text(el) -> str:
    """Flatten every run of text under an element, tabs included."""
    out = []
    for node in el.iter():
        if node.tag == W + "t":
            out.append(node.text or "")
        elif node.tag in (W + "tab", W + "br"):
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _blank(s: str) -> bool:
    return _FILLER.sub("", s).strip() == ""


def _classify(raw: str) -> dict:
    """Decide what a single table cell is: label, text/date/time input, or choice."""
    s = raw.strip()
    up = s.upper()
    compact = re.sub(r"[^A-Z/]", "", up)

    if compact in ("SNS", "NSS"):
        return {"type": "choice", "options": ["S", "NS"],
                "hint": "Satisfaisant / Non satisfaisant"}
    if compact in ("CNC", "NCC"):
        return {"type": "choice", "options": ["C", "NC"],
                "hint": "Conforme / Non conforme"}
    # what survives once the pen-guides are stripped tells you the field type
    skeleton = _FILLER.sub("", s).strip()
    if skeleton == ":":
        return {"type": "time"}
    if skeleton in ("/", "//"):
        return {"type": "date"}
    if _DATE_PAT.search(s):
        return {"type": "date"}
    if _blank(s):
        if _TIME_PAT.search(s):
            return {"type": "time"}
        return {"type": "text"}
    # a label that still carries a blank tail ("Net =............") is an input
    # whose printed prefix is the label itself
    if re.search(r"[:=]\s*[.…_]{3,}\s*$", s):
        return {"type": "text", "prefix": re.split(r"[:=]", s)[0].strip()}
    return {"type": "label", "text": s}


def _rows(tbl) -> list[list[str]]:
    out = []
    for tr in tbl.findall(W + "tr"):
        out.append([_text(tc) for tc in tr.findall(W + "tc")])
    return out


def _looks_like_header(row: list[str]) -> bool:
    filled = [c for c in row if not _blank(c)]
    return len(filled) >= 2 and len(filled) >= len(row) - 1


# In the paper dossiers a yes/no answer is printed as two adjacent cells the
# operator rings with a pen ("S" | "NS"), or as a column header ("C/NC") over a
# blank cell. Both must become one tappable choice.
CHOICE_SETS = [
    (("S", "NS"), "Satisfaisant / Non satisfaisant"),
    (("C", "NC"), "Conforme / Non conforme"),
    (("O", "N"), "Oui / Non"),
    (("OUI", "NON"), "Oui / Non"),
]
_HDR_CHOICE = {"C/NC": ("C", "NC"), "S/NS": ("S", "NS"), "O/N": ("O", "N"),
               "NC/C": ("C", "NC"), "NS/S": ("S", "NS")}


def _merge_choice_cells(row: list[dict]) -> list[dict]:
    """Collapse adjacent 'S' + 'NS' label cells into a single choice field."""
    out, i = [], 0
    while i < len(row):
        merged = False
        for opts, hint in CHOICE_SETS:
            n = len(opts)
            window = row[i:i + n]
            if len(window) == n and all(c["type"] == "label" for c in window) and \
                    tuple(c["text"].strip().upper() for c in window) == opts:
                out.append({"type": "choice", "options": list(opts), "hint": hint,
                            "raw": " ".join(opts)})
                i += n
                merged = True
                break
        if not merged:
            out.append(row[i])
            i += 1
    return out


def _header_choices(header: list[str] | None, grid: list[list[dict]]) -> None:
    """A column headed 'C/NC' turns its blank cells into a conformity choice."""
    if not header:
        return
    for col, h in enumerate(header):
        opts = _HDR_CHOICE.get(re.sub(r"[^A-Z/]", "", h.upper()))
        if not opts:
            continue
        for row in grid:
            if col < len(row) and row[col]["type"] == "text":
                row[col].update({"type": "choice", "options": list(opts),
                                 "hint": "Conforme / Non conforme"})


def _shape(row: list[dict]) -> tuple:
    """Identity of a row: printed labels, and merely 'an input' everywhere else.
    Word vertically-merges a date cell across a run of otherwise identical lines,
    so the exact input type must not break the run -- only real label text does."""
    return tuple(("label", c["text"]) if c["type"] == "label" else ("in",) for c in row)


MIN_REPEAT = 3


def _collapse_repeat(block: dict) -> None:
    """Paper must pre-print 92 blank lines because you cannot add a row to paper.
    A screen can. Any run of >=3 identical blank rows collapses to ONE template
    row the operator grows on demand -- same record, none of the dead ink."""
    rows = block["rows"]
    if len(rows) < MIN_REPEAT + 1:
        return
    keep, removed, i = [], 0, 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and _shape(rows[j + 1]) == _shape(rows[i]):
            j += 1
        run = j - i + 1
        has_input = any(c["type"] != "label" for c in rows[i])
        if run >= MIN_REPEAT and has_input:
            keep.append(rows[i])          # one template line
            removed += run - 1
        else:
            keep.extend(rows[i:j + 1])
        i = j + 1
    if removed:
        block["rows"] = keep
        block["repeatable"] = True
        block["paper_rows"] = removed + 1


def parse_form(path: str | Path) -> dict[str, Any]:
    """Read one .docx into a renderable, fillable form spec."""
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        xml = next(zf.read(n) for n in zf.namelist() if n.endswith("word/document.xml"))
    body = ET.fromstring(xml).find(W + "body")

    title = ""
    doc_key, stage, label = "DOC", "fabrication", path.stem
    sections: list[dict] = []
    cur: dict | None = None
    t_idx = 0

    for child in list(body):
        if child.tag == W + "p":
            txt = _text(child)
            if not txt:
                continue
            if not title:
                title = txt
            # ALL-CAPS short lines are the section banners in these dossiers
            letters = [c for c in txt if c.isalpha()]
            is_head = (len(txt) <= 70 and letters
                       and sum(c.isupper() for c in letters) / len(letters) > 0.85)
            if is_head:
                cur = {"heading": txt, "blocks": []}
                sections.append(cur)
            else:
                if cur is None:
                    cur = {"heading": "", "blocks": []}
                    sections.append(cur)
                if len(txt) > 3:
                    cur["blocks"].append({"kind": "note", "text": txt})

        elif child.tag == W + "tbl":
            rows = _rows(child)
            if not rows:
                continue
            if cur is None:
                cur = {"heading": "", "blocks": []}
                sections.append(cur)
            header = rows[0] if (len(rows) > 1 and _looks_like_header(rows[0])) else None
            data = rows[1:] if header else rows
            grid = []
            for row in data:
                grid.append(_merge_choice_cells([_classify(raw) for raw in row]))
            _header_choices(header, grid)
            for r, cells in enumerate(grid):        # key AFTER merging, so keys are stable
                for c, spec in enumerate(cells):
                    if spec["type"] != "label":
                        spec["key"] = f"t{t_idx}.r{r}.c{c}"
            block = {"kind": "table", "index": t_idx, "header": header, "rows": grid}
            _collapse_repeat(block)
            cur["blocks"].append(block)
            t_idx += 1

    up = title.upper().replace("Ô", "O")
    for key, stg, lbl, needles in DOC_TYPES:
        if any(n in up for n in needles):
            doc_key, stage, label = key, stg, lbl
            break

    n_fields = sum(1 for s in sections for b in s["blocks"] if b["kind"] == "table"
                   for row in b["rows"] for c in row if c["type"] != "label")
    return {"doc_key": doc_key, "stage": stage, "label": label, "title": title,
            "file": path.name, "sections": [s for s in sections if s["blocks"]],
            "field_count": n_fields}


def stage_of(doc_key: str) -> str:
    for key, stage, *_ in DOC_TYPES:
        if key == doc_key:
            return stage
    return "fabrication"


def load_all(folder: str | Path) -> list[dict]:
    """Every dossier in the folder, ordered the way the batch actually flows."""
    order = {k: i for i, (k, *_ ) in enumerate(DOC_TYPES)}
    forms = []
    for p in sorted(Path(folder).glob("*.docx")):
        if p.name.startswith("~$"):
            continue
        try:
            forms.append(parse_form(p))
        except Exception:
            continue
    forms.sort(key=lambda f: order.get(f["doc_key"], 99))
    return forms
