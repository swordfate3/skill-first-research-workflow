from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_bootstrap_module():
    module_path = ROOT / "skills" / "research-workflow" / "scripts" / "bootstrap_project.py"
    spec = importlib.util.spec_from_file_location("research_workflow_bootstrap", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_setup_module():
    module_path = ROOT / "skills" / "research-workflow" / "scripts" / "setup_project.py"
    spec = importlib.util.spec_from_file_location("research_workflow_setup", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SkillPackagingTests(unittest.TestCase):
    def test_skill_bundle_contains_project_template_files(self):
        template_root = (
            ROOT / "skills" / "research-workflow" / "assets" / "project-template"
        )

        expected_files = [
            "pyproject.toml",
            "workflow.py",
            "state.py",
            "extract_pdfs.py",
            "migrate_outputs.py",
            "server.py",
            "templates/paper-card.md",
            "templates/paper-memory.json",
            "templates/collision-ideas.md",
            "templates/direction.md",
            "templates/prototype.md",
            "templates/draft.md",
            "web/index.html",
            "web/app.js",
            "web/styles.css",
            "workspace/papers/.gitkeep",
            "workspace/outputs/index.json",
            "workspace/outputs/paper-cards/.gitkeep",
            "workspace/outputs/collisions/.gitkeep",
            "workspace/outputs/directions/.gitkeep",
            "workspace/extracted/.gitkeep",
            "workspace/approvals/.gitkeep",
            "workspace/memory/papers/.gitkeep",
        ]

        self.assertTrue((ROOT / "skills" / "research-workflow" / "scripts" / "setup_project.py").exists())

        for relative in expected_files:
            with self.subTest(relative=relative):
                self.assertTrue((template_root / relative).exists())

    def test_bootstrap_project_copies_template_to_destination(self):
        bootstrap = load_bootstrap_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "demo-project"
            result = bootstrap.bootstrap_project(destination)

            self.assertEqual(result["status"], "bootstrapped")
            self.assertTrue((destination / "workflow.py").exists())
            self.assertTrue((destination / "templates" / "paper-card.md").exists())
            self.assertTrue((destination / "web" / "app.js").exists())
            self.assertTrue((destination / "workspace" / "papers" / ".gitkeep").exists())

    def test_bootstrap_project_reports_conflicts_without_force(self):
        bootstrap = load_bootstrap_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir)
            (destination / "workflow.py").write_text("existing", encoding="utf-8")

            result = bootstrap.bootstrap_project(destination)

        self.assertEqual(result["status"], "conflict")
        self.assertIn("workflow.py", result["conflicts"])

    def test_setup_project_requires_destination_when_current_dir_is_not_initialized(self):
        setup = load_setup_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = setup.setup_project(Path(tmpdir), dest=None)

        self.assertEqual(result["status"], "needs_destination")


if __name__ == "__main__":
    unittest.main()
