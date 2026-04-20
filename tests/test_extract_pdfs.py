from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_extract_module():
    module_path = Path(__file__).resolve().parents[1] / "extract_pdfs.py"
    spec = importlib.util.spec_from_file_location("skill_first_extract_pdfs", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExtractPdfsTests(unittest.TestCase):
    def test_extract_all_writes_structured_documents_and_skips_unchanged_pdf(self):
        extract_pdfs = load_extract_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers = root / "workspace" / "papers"
            papers.mkdir(parents=True)
            pdf = papers / "paper-a.pdf"
            pdf.write_bytes(b"fake pdf bytes")
            calls = []

            def fake_extractor(path: Path) -> str:
                calls.append(path.name)
                return "\n".join(
                    [
                        "A useful paper",
                        "Table 1: Main results",
                        "Model Accuracy F1",
                        "Baseline 0.80 0.75",
                        "Ours 0.86 0.82",
                        "Equation (1): L = CE(y, y_hat) + lambda ||w||_2",
                        "Figure 2: Overall architecture.",
                    ]
                )

            first = extract_pdfs.extract_all(root, extractor=fake_extractor)
            second = extract_pdfs.extract_all(root, extractor=fake_extractor)

            extracted = root / "workspace" / "extracted" / "paper-a"
            manifest = json.loads((extracted / "manifest.json").read_text(encoding="utf-8"))
            text_doc = (extracted / "text.md").read_text(encoding="utf-8")
            tables_doc = (extracted / "tables.md").read_text(encoding="utf-8")
            equations_doc = (extracted / "equations.md").read_text(encoding="utf-8")
            figures_doc = (extracted / "figures.md").read_text(encoding="utf-8")

        self.assertEqual(first["extracted"], ["paper-a.pdf"])
        self.assertEqual(second["skipped"], ["paper-a.pdf"])
        self.assertEqual(calls, ["paper-a.pdf"])
        self.assertIn("# Extracted Text", text_doc)
        self.assertIn("Table 1: Main results", tables_doc)
        self.assertIn("L = CE", equations_doc)
        self.assertIn("Figure 2", figures_doc)
        self.assertEqual(manifest["source"], "paper-a.pdf")
        self.assertEqual(manifest["status"], "extracted")
        self.assertEqual(
            sorted(manifest["files"]),
            ["equations.md", "figures.md", "tables.md", "text.md"],
        )

    def test_extract_all_reextracts_when_pdf_hash_changes(self):
        extract_pdfs = load_extract_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers = root / "workspace" / "papers"
            papers.mkdir(parents=True)
            pdf = papers / "paper-a.pdf"
            pdf.write_bytes(b"first pdf bytes")
            extracted_texts = iter(["first extraction", "second extraction"])

            def fake_extractor(path: Path) -> str:
                del path
                return next(extracted_texts)

            first = extract_pdfs.extract_all(root, extractor=fake_extractor)
            pdf.write_bytes(b"second pdf bytes")
            second = extract_pdfs.extract_all(root, extractor=fake_extractor)

            text = (
                root / "workspace" / "extracted" / "paper-a" / "text.md"
            ).read_text(encoding="utf-8")

        self.assertEqual(first["extracted"], ["paper-a.pdf"])
        self.assertEqual(second["changed"], ["paper-a.pdf"])
        self.assertIn("second extraction", text)


if __name__ == "__main__":
    unittest.main()
