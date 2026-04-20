from __future__ import annotations

import unittest
from pathlib import Path


class WebAssetTests(unittest.TestCase):
    def test_app_js_does_not_shadow_browser_document_when_rendering_list(self):
        app_js = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("for (const document of documents)", app_js)
        self.assertIn("globalThis.document.createElement", app_js)


if __name__ == "__main__":
    unittest.main()
