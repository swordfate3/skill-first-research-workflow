from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, TextIO
from urllib.error import URLError
from urllib.request import urlopen


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import bootstrap_project as bootstrap_module


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
WEB_START_TIMEOUT_SECONDS = 6.0

Bootstrapper = Callable[[Path, bool], dict]
UvPathFinder = Callable[[str], str | None]
UvSyncRunner = Callable[[Path], dict]
WebResolver = Callable[[Path, str, int], dict]


def is_project_root(path: Path) -> bool:
    path = Path(path).resolve()
    return (
        (path / "workflow.py").exists()
        and (path / "state.py").exists()
        and (path / "workspace" / "papers").exists()
    )


def setup_project(
    cwd: Path,
    *,
    dest: Path | None = None,
    bootstrapper: Bootstrapper | None = None,
    uv_path_finder: UvPathFinder | None = None,
    uv_sync_runner: UvSyncRunner | None = None,
    web_resolver: WebResolver | None = None,
    host: str = DEFAULT_HOST,
    port_start: int = DEFAULT_PORT,
) -> dict:
    cwd = Path(cwd).resolve()
    bootstrapper = bootstrapper or bootstrap_default
    uv_path_finder = uv_path_finder or shutil.which
    uv_sync_runner = uv_sync_runner or run_uv_sync
    web_resolver = web_resolver or ensure_web_ready

    project_root = cwd
    project_bootstrapped = False

    if not is_project_root(cwd):
        if dest is None:
            return {
                "status": "needs_destination",
                "message": "Project directory is not initialized. Please provide a destination path for bootstrap.",
                "current_directory": str(cwd),
            }

        project_root = Path(dest).resolve()
        if not is_project_root(project_root):
            bootstrap_result = bootstrapper(project_root, False)
            if bootstrap_result.get("status") == "conflict":
                return {
                    "status": "bootstrap_conflict",
                    "project_root": str(project_root),
                    "message": "Destination already contains conflicting files.",
                    "conflicts": bootstrap_result.get("conflicts", []),
                }
            if bootstrap_result.get("status") != "bootstrapped":
                return {
                    "status": "failed",
                    "project_root": str(project_root),
                    "message": bootstrap_result.get("message", "Project bootstrap failed."),
                }
            project_bootstrapped = True

    uv_path = uv_path_finder("uv")
    if not uv_path:
        return {
            "status": "needs_uv",
            "project_root": str(project_root),
            "project_bootstrapped": project_bootstrapped,
            "uv_available": False,
            "message": "uv is required before this project can run.",
        }

    sync_result = uv_sync_runner(project_root)
    if sync_result.get("returncode", 1) != 0:
        return {
            "status": "failed",
            "project_root": str(project_root),
            "project_bootstrapped": project_bootstrapped,
            "uv_available": True,
            "dependencies_synced": False,
            "message": "uv sync failed.",
            "stderr": sync_result.get("stderr", ""),
            "stdout": sync_result.get("stdout", ""),
        }

    web = web_resolver(project_root, host, port_start)
    if web.get("status") not in {"reused", "started"}:
        return {
            "status": "web_failed",
            "project_root": str(project_root),
            "project_bootstrapped": project_bootstrapped,
            "uv_available": True,
            "dependencies_synced": True,
            "message": web.get("message", "Web server could not be started."),
            "port_attempts": web.get("port_attempts", []),
        }

    return {
        "status": "ready",
        "project_root": str(project_root),
        "project_bootstrapped": project_bootstrapped,
        "uv_available": True,
        "dependencies_synced": True,
        "web": web,
        "next_step": "run_workflow",
    }


def bootstrap_default(destination: Path, force: bool = False) -> dict:
    return bootstrap_module.bootstrap_project(destination, force=force)


def run_uv_sync(project_root: Path) -> dict:
    completed = subprocess.run(
        ["uv", "sync"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def ensure_web_ready(project_root: Path, host: str = DEFAULT_HOST, port_start: int = DEFAULT_PORT) -> dict:
    attempts = []
    for port in range(port_start, port_start + 10):
        attempts.append(port)
        probe = probe_workflow_server(host, port)
        if probe.get("status") == "reusable" and probe.get("project_root") == str(project_root.resolve()):
            return {
                "status": "reused",
                "url": f"http://{host}:{port}",
                "port": port,
            }
        if probe.get("status") != "free":
            continue

        started = start_workflow_server(project_root, host, port)
        if started.get("status") == "started":
            return started

    return {
        "status": "failed",
        "message": "Web server could not be started.",
        "port_attempts": attempts,
    }


def probe_workflow_server(host: str, port: int) -> dict:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            pass
    except OSError:
        return {"status": "free"}

    url = f"http://{host}:{port}/api/state"
    try:
        with urlopen(url, timeout=0.8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        return {"status": "occupied"}

    if not isinstance(payload, dict) or "project_root" not in payload or "paper_count" not in payload:
        return {"status": "occupied"}

    return {
        "status": "reusable",
        "project_root": str(payload.get("project_root", "")),
    }


def start_workflow_server(project_root: Path, host: str, port: int) -> dict:
    log_dir = project_root / "workspace" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "server.log"

    with log_path.open("ab") as log_handle:
        process = subprocess.Popen(
            ["uv", "run", "python", "server.py", "--host", host, "--port", str(port)],
            cwd=project_root,
            stdout=log_handle,
            stderr=log_handle,
            start_new_session=True,
        )

    deadline = time.time() + WEB_START_TIMEOUT_SECONDS
    while time.time() < deadline:
        probe = probe_workflow_server(host, port)
        if probe.get("status") == "reusable" and probe.get("project_root") == str(project_root.resolve()):
            return {
                "status": "started",
                "url": f"http://{host}:{port}",
                "port": port,
                "pid": process.pid,
            }
        time.sleep(0.2)

    return {
        "status": "failed",
        "message": "Timed out while waiting for the web server to start.",
        "port_attempts": [port],
    }


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python setup_project.py")
    parser.add_argument("--dest", default=None, help="destination directory for bootstrap when the current directory is not initialized")
    parser.add_argument("--host", default=DEFAULT_HOST, help="web host to bind or probe")
    parser.add_argument("--port-start", type=int, default=DEFAULT_PORT, help="first port to probe for the local web service")
    args = parser.parse_args(argv)

    payload = setup_project(
        Path.cwd(),
        dest=Path(args.dest) if args.dest else None,
        host=args.host,
        port_start=args.port_start,
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if stdout is None:
        print(text)
    else:
        stdout.write(text)
        stdout.write("\n")
    return 0 if payload.get("status") == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
