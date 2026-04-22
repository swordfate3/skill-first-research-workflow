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

    def test_app_js_and_index_html_include_type_filter_controls(self):
        root = Path(__file__).resolve().parents[1] / "web"
        app_js = (root / "app.js").read_text(encoding="utf-8")
        index_html = (root / "index.html").read_text(encoding="utf-8")

        self.assertIn('data-filter="all"', index_html)
        self.assertIn('data-filter="paper_card"', index_html)
        self.assertIn('data-filter="collision"', index_html)
        self.assertIn('data-filter="direction"', index_html)
        self.assertIn("/api/documents", app_js)
        self.assertIn("type=", app_js)
        self.assertIn("all", app_js)
        self.assertIn("paper_card", app_js)
        self.assertIn("collision", app_js)
        self.assertIn("direction", app_js)
        self.assertIn("document-group", app_js)
        self.assertIn("group-title", app_js)
        self.assertIn('id="uploadButton"', index_html)
        self.assertIn('id="paperUploadInput"', index_html)
        self.assertIn('id="uploadStatusList"', index_html)
        self.assertIn("/api/upload-papers", app_js)
        self.assertIn("/api/upload-status", app_js)

    def test_skill_template_web_assets_include_type_filter_controls(self):
        root = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "research-workflow"
            / "assets"
            / "project-template"
            / "web"
        )
        app_js = (root / "app.js").read_text(encoding="utf-8")
        index_html = (root / "index.html").read_text(encoding="utf-8")

        self.assertIn('data-filter="all"', index_html)
        self.assertIn('data-filter="paper_card"', index_html)
        self.assertIn('data-filter="collision"', index_html)
        self.assertIn('data-filter="direction"', index_html)
        self.assertIn("/api/documents", app_js)
        self.assertIn("type=", app_js)
        self.assertIn("all", app_js)
        self.assertIn("paper_card", app_js)
        self.assertIn("collision", app_js)
        self.assertIn("direction", app_js)
        self.assertIn("document-group", app_js)
        self.assertIn("group-title", app_js)

    def test_web_assets_include_upload_controls_and_status_polling(self):
        root = Path(__file__).resolve().parents[1] / "web"
        app_js = (root / "app.js").read_text(encoding="utf-8")
        index_html = (root / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="uploadButton"', index_html)
        self.assertIn('id="paperUploadInput"', index_html)
        self.assertIn('id="uploadStatusList"', index_html)
        self.assertIn("/api/upload-papers", app_js)
        self.assertIn("/api/upload-status", app_js)
        self.assertIn("pollUploadStatus", app_js)
        self.assertIn("renderUploadStatus", app_js)


if __name__ == "__main__":
    unittest.main()
