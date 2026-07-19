"""
Regenerate tests/fixtures/qr_cases.json.

    python tests/make_qr_fixtures.py

The fixtures are produced by segno, an independent QR implementation. That is
the point: decoding symbols made by our own encoder would only prove the two
agree with each other, whereas decoding segno's output proves frontend/qr.js
agrees with the standard.

Run this after changing /api/qr, so the fixtures keep matching what the floor
actually prints. Note make_qr(), not make(): segno.make() silently prefers
Micro QR for short payloads, which almost no scanner can read.
"""
from __future__ import annotations

import io
import json
import os

import segno

# (payload, error-correction level). Chosen to cover every code path that
# matters: all four ECC levels, several masks, versions 1 through 5, the
# alignment-pattern threshold at version 2+, and UTF-8 byte mode.
CASES = [
    ("BT:LOT:1", "m"),
    ("BT:ST:pesee", "m"),
    ("BT:ST:qc", "m"),
    ("BT:MAT:3", "m"),
    ("BT:LOT:12", "m"),
    ("BT:ST:sign", "l"),
    ("BT:MAT:17", "q"),
    ("BT:LOT:9", "h"),
    ("PF201-260718-001", "m"),
    ("Laboratoires Medicka - Nabeul", "m"),
    ("12345678901234567890", "m"),
    ("https://batchtwin.local/floor?lot=PF201-260718-001&st=pesee", "m"),
    ("Lot PF201 — contrôle à 15h30, opérateur Sana", "m"),
    ("A" * 120, "m"),
]

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "qr_cases.json")


def main() -> None:
    cases = []
    for data, err in CASES:
        q = segno.make_qr(data, error=err)
        matrix = [[1 if m else 0 for m in row] for row in q.matrix]
        cases.append({
            "data": data,
            "error": err,
            "version": q.version,
            "mask": q.mask,
            "dim": len(matrix),
            "matrix": matrix,
        })
        print(f"  v{q.version:<2} ecc={err.upper()} mask={q.mask} "
              f"dim={len(matrix):<3} {data[:44]}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(cases, f)
    print(f"\nwrote {len(cases)} fixtures to {OUT}")
    print("now run:  node tests/test_qr.js")


if __name__ == "__main__":
    main()
