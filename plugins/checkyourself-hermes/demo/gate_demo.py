#!/usr/bin/env python3
"""Completion-evidence gate demo for the native CheckYourself Hermes plugin.

Uses this repository's Python CLI. Does not install Hermes, call npm, publish,
restart a gateway, or read a real HERMES_HOME.

Exit 0 when the gate blocks missing evidence, follows a real scan score, allows
a numeric score with no open P0/P1, blocks an open P0, and finishes in under
90 seconds.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLUGIN = ROOT / "plugins" / "checkyourself-hermes" / "__init__.py"
CLI = ROOT / "tools" / "checkyourself.py"
LIMIT_SECONDS = 90


def load_plugin():
    spec = importlib.util.spec_from_file_location("checkyourself_hermes_plugin_demo", PLUGIN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load plugin from {PLUGIN}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Ctx:
    def __init__(self, command: str):
        self.command = command

    def get_config(self, key, default=None):
        if key == "checkyourself_command":
            return self.command
        if key == "timeout_seconds":
            return 60
        if key == "max_files":
            return 200
        return default


def main() -> int:
    started = time.monotonic()
    home = Path(tempfile.mkdtemp(prefix="checkyourself-gate-demo-"))
    os.environ["HERMES_HOME"] = str(home)
    os.environ.pop("HERMES_SESSION_ID", None)
    os.environ.pop("HERMES_SESSION_KEY", None)
    os.environ.pop("HERMES_PLATFORM", None)
    plugin = load_plugin()
    command = f"{shlex.quote(sys.executable)} {shlex.quote(str(CLI))}"
    plugin._ctx = _Ctx(command)

    print("1. kanban_complete with no score")
    missing = plugin._on_pre_tool("kanban_complete", {})
    if not missing or missing.get("action") != "block":
        print("FAIL: missing evidence was not blocked", missing)
        return 1
    print("   BLOCKED")

    project = home / "fixture"
    project.mkdir()
    (project / "package.json").write_text('{"name":"gate-demo","private":true}\n', encoding="utf-8")
    (project / "index.js").write_text("console.log('gate demo')\n", encoding="utf-8")
    print("2. read-only scan of a tiny fixture, then gate on that score")
    scanned = plugin.scan(str(project))
    if not scanned.get("ok"):
        print("FAIL: scan did not succeed", scanned.get("error"))
        return 1
    scanned_gate = plugin.evaluate_completion_gate("kanban_complete", {})
    counts = scanned_gate.get("counts") or {}
    print(
        f"   score={scanned_gate.get('score')} P0={counts.get('P0')} P1={counts.get('P1')} "
        f"-> {'ALLOWED' if scanned_gate.get('allowed') else 'BLOCKED'}"
    )
    expects_allow = counts.get("P0") == 0 and counts.get("P1") == 0 and scanned_gate.get("score") is not None
    if bool(scanned_gate.get("allowed")) != expects_allow:
        print("FAIL: gate did not follow the scan score", scanned_gate)
        return 1

    clean = home / "clean.json"
    dirty = home / "dirty.json"
    clean.write_text("[]\n", encoding="utf-8")
    dirty.write_text(
        json.dumps([{"id": "F1", "severity": "P0", "title": "open p0"}]) + "\n",
        encoding="utf-8",
    )
    print("3. findings with no open P0/P1")
    allowed = plugin.evaluate_completion_gate(
        "kanban_complete",
        {"metadata": {"checkyourself": {"findings_path": str(clean)}}},
    )
    hook = plugin._on_pre_tool(
        "kanban_complete",
        {"metadata": {"checkyourself": {"findings_path": str(clean)}}},
    )
    print(f"   score={allowed.get('score')} -> ALLOWED")
    if not allowed.get("allowed") or hook is not None:
        print("FAIL: clean score did not allow completion", allowed, hook)
        return 1

    print("4. findings with an open P0")
    blocked = plugin.evaluate_completion_gate(
        "kanban_complete",
        {"metadata": {"checkyourself": {"findings_path": str(dirty)}}},
    )
    hook = plugin._on_pre_tool(
        "kanban_complete",
        {"metadata": {"checkyourself": {"findings_path": str(dirty)}}},
    )
    print(f"   score={blocked.get('score')} P0={blocked.get('counts', {}).get('P0')} -> BLOCKED")
    if blocked.get("allowed") or not hook or hook.get("action") != "block":
        print("FAIL: P0 score did not block completion", blocked, hook)
        return 1
    if str(blocked.get("score")) not in hook.get("message", ""):
        print("FAIL: block message did not include the score")
        return 1

    elapsed = time.monotonic() - started
    print(f"elapsed_seconds={elapsed:.3f}")
    if elapsed >= LIMIT_SECONDS:
        print(f"FAIL: demo exceeded {LIMIT_SECONDS}s")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
