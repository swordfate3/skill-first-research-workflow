from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_server_module():
    module_path = ROOT / "server.py"
    spec = importlib.util.spec_from_file_location("skill_first_server", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RuntimeSmokeTests(unittest.TestCase):
    def test_real_workspace_outputs_are_browsable(self):
        outputs_root = ROOT / "workspace" / "outputs"
        if not list(outputs_root.glob("*.md")):
            self.skipTest("real workspace outputs are not present")

        server = load_server_module()
        documents = server.list_documents(doc_type="all")

        self.assertTrue(documents)
        self.assertIn("paper_card", {doc["type"] for doc in documents})
        self.assertIn("collision", {doc["type"] for doc in documents})
        self.assertIn("direction", {doc["type"] for doc in documents})

        direction_doc = next(doc for doc in documents if doc["type"] == "direction")
        loaded = server.load_document(direction_doc["name"])

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["type"], "direction")
        self.assertTrue(loaded["body"])


if __name__ == "__main__":
    unittest.main()
