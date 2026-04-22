from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_setup_module():
    module_path = ROOT / "skills" / "research-workflow" / "scripts" / "setup_project.py"
    spec = importlib.util.spec_from_file_location("research_workflow_setup", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SetupProjectTests(unittest.TestCase):
    def test_setup_project_returns_needs_uv_after_bootstrap_when_uv_missing(self):
        setup = load_setup_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir) / "cwd"
            cwd.mkdir()
            destination = Path(tmpdir) / "project"

            result = setup.setup_project(
                cwd,
                dest=destination,
                bootstrapper=lambda target, force=False: {
                    "status": "bootstrapped",
                    "destination": str(target),
                },
                uv_path_finder=lambda _: None,
                uv_sync_runner=lambda _: None,
                web_resolver=lambda *_args, **_kwargs: {"status": "reused", "url": "http://127.0.0.1:8765"},
            )

        self.assertEqual(result["status"], "needs_uv")
        self.assertEqual(result["project_root"], str(destination.resolve()))
        self.assertTrue(result["project_bootstrapped"])

    def test_setup_project_returns_ready_and_reuses_existing_web(self):
        setup = load_setup_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "workflow.py").write_text("pass\n", encoding="utf-8")
            (root / "state.py").write_text("pass\n", encoding="utf-8")
            (root / "workspace" / "papers").mkdir(parents=True)

            result = setup.setup_project(
                root,
                dest=None,
                bootstrapper=lambda *_args, **_kwargs: self.fail("bootstrap should not run"),
                uv_path_finder=lambda _: "/usr/bin/uv",
                uv_sync_runner=lambda _: {"returncode": 0, "stderr": "", "stdout": ""},
                web_resolver=lambda *_args, **_kwargs: {
                    "status": "reused",
                    "url": "http://127.0.0.1:8765",
                    "port": 8765,
                },
            )

        self.assertEqual(result["status"], "ready")
        self.assertFalse(result["project_bootstrapped"])
        self.assertTrue(result["dependencies_synced"])
        self.assertEqual(result["web"]["status"], "reused")

    def test_setup_project_uses_existing_initialized_destination_without_rebootstrapping(self):
        setup = load_setup_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir) / "cwd"
            cwd.mkdir()
            destination = Path(tmpdir) / "project"
            (destination / "workflow.py").parent.mkdir(parents=True, exist_ok=True)
            (destination / "workflow.py").write_text("pass\n", encoding="utf-8")
            (destination / "state.py").write_text("pass\n", encoding="utf-8")
            (destination / "workspace" / "papers").mkdir(parents=True)

            result = setup.setup_project(
                cwd,
                dest=destination,
                bootstrapper=lambda *_args, **_kwargs: self.fail("bootstrap should not run"),
                uv_path_finder=lambda _: "/usr/bin/uv",
                uv_sync_runner=lambda _: {"returncode": 0, "stderr": "", "stdout": ""},
                web_resolver=lambda *_args, **_kwargs: {
                    "status": "reused",
                    "url": "http://127.0.0.1:8765",
                    "port": 8765,
                },
            )

        self.assertEqual(result["status"], "ready")
        self.assertFalse(result["project_bootstrapped"])
        self.assertEqual(result["project_root"], str(destination.resolve()))


if __name__ == "__main__":
    unittest.main()
