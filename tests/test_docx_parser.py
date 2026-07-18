import unittest
from pathlib import Path

from backend import docx_parser, docx_forms

DOSSIER = Path(__file__).resolve().parents[1] / "dossier"


def _find(doc_key: str) -> Path:
    """Locate a dossier by what it *is*, not by its filename -- the source files
    get renamed by whoever exports them from Word."""
    for p in sorted(DOSSIER.glob("*.docx")):
        if docx_forms.parse_form(p)["doc_key"] == doc_key:
            return p
    raise AssertionError(f"no {doc_key} dossier in {DOSSIER}")


class DocxParserTests(unittest.TestCase):
    def test_docx_parser_extracts_operational_tasks(self):
        doc_path = _find("DCOI")
        text = docx_parser.extract_docx_text(doc_path)
        self.assertIn("OPERATEURSDEMISEENBLISTERS", text)

        tasks = docx_parser.extract_docx_tasks(doc_path)
        self.assertTrue(tasks)
        # Tasks carry translation keys, not English sentences: the operators are
        # French-speaking and the UI renders EN / FR / AR from the same payload.
        self.assertIn("task_blister", [t["key"] for t in tasks])
        for t in tasks:
            self.assertRegex(t["key"], r"^task_[a-z]+$")
            self.assertNotIn("title", t, "no prose may travel from the server")
        self.assertEqual({t["doc_key"] for t in tasks}, {"DCOI"})


class DocxFormTests(unittest.TestCase):
    def test_all_four_dossiers_are_recognised(self):
        keys = {f["doc_key"] for f in docx_forms.load_all(DOSSIER)}
        self.assertEqual(keys, {"DFA", "DCOI", "DCOII", "DCT"})

    def test_fields_are_typed_and_keyed(self):
        form = docx_forms.parse_form(_find("DFA"))
        cells = [c for s in form["sections"] for b in s["blocks"]
                 if b["kind"] == "table" for r in b["rows"] for c in r]
        inputs = [c for c in cells if c["type"] != "label"]
        self.assertGreater(len(inputs), 50)
        self.assertTrue(all("key" in c for c in inputs), "every input needs a stable key")
        self.assertEqual(len({c["key"] for c in inputs}), len(inputs), "keys must be unique")
        self.assertTrue({c["type"] for c in inputs} <= {"text", "date", "time", "choice"})

    def test_choice_cells_are_merged(self):
        """'S' and 'NS' are two adjacent pen-ring cells on paper; one tap here."""
        form = docx_forms.parse_form(_find("DCOI"))
        choices = [c for s in form["sections"] for b in s["blocks"]
                   if b["kind"] == "table" for r in b["rows"] for c in r
                   if c["type"] == "choice"]
        self.assertTrue(choices)
        self.assertTrue(any(c["options"] == ["S", "NS"] for c in choices))

    def test_repeated_blank_rows_collapse(self):
        """Paper pre-prints dozens of identical blank lines; we keep one template."""
        form = docx_forms.parse_form(_find("DCT"))
        rep = [b for s in form["sections"] for b in s["blocks"] if b.get("repeatable")]
        self.assertTrue(rep)
        self.assertTrue(all(b["paper_rows"] >= 3 for b in rep))


if __name__ == "__main__":
    unittest.main()
