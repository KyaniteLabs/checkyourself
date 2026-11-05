"""Regression tests for plugins/checkyourself-hermes (Reviewer review on PR #50)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "checkyourself-hermes"
sys.path.insert(0, str(PLUGIN_DIR.parent))

# Import the plugin module directly by path so we do not require Hermes installed.
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "checkyourself_hermes_plugin",
    PLUGIN_DIR / "__init__.py",
)
cy = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cy)


class _FakeSessionCtx:
    """Minimal stand-in for gateway.session_context ContextVar binding."""

    def __init__(self):
        self.vars = {}

    def set_session_vars(self, **kwargs):
        if "platform" in kwargs:
            self.vars["HERMES_SESSION_PLATFORM"] = kwargs["platform"]
        if "session_id" in kwargs:
            self.vars["HERMES_SESSION_ID"] = kwargs["session_id"]
        if "cwd" in kwargs:
            self.vars["__cwd__"] = kwargs["cwd"]

    def get_session_env(self, name, default=""):
        if name in self.vars:
            return self.vars[name]
        return os.getenv(name, default)


class HermesPluginKaiFixes(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.td = Path(self._tmpdir.name)
        self.data = self.td / "plugin-data" / "checkyourself"
        self.data.mkdir(parents=True)
        self._patches = [
            mock.patch.object(cy, "_data_dir", lambda: self.data),
            mock.patch.dict(os.environ, {"HERMES_HOME": str(self.td)}, clear=False),
        ]
        for p in self._patches:
            p.start()
        # Clear process-level platform leftovers between tests.
        os.environ.pop("HERMES_PLATFORM", None)
        os.environ.pop("HERMES_SESSION_PLATFORM", None)
        os.environ.pop("HERMES_SESSION_ID", None)
        cy._call_session_id = None
        cy._ctx = None

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    # --- P1: gateway ContextVars -------------------------------------------

    def test_gateway_reads_session_contextvar_not_os_environ(self):
        fake = _FakeSessionCtx()
        fake.set_session_vars(platform="telegram")
        # os.environ deliberately unset / wrong
        os.environ.pop("HERMES_SESSION_PLATFORM", None)
        os.environ.pop("HERMES_PLATFORM", None)

        with mock.patch.dict(sys.modules, {
            "gateway": mock.MagicMock(),
            "gateway.session_context": mock.MagicMock(get_session_env=fake.get_session_env),
        }):
            # Ensure import path used by plugin resolves to our fake
            import types
            mod = types.ModuleType("gateway.session_context")
            mod.get_session_env = fake.get_session_env
            sys.modules["gateway.session_context"] = mod
            sys.modules["gateway"] = types.ModuleType("gateway")
            self.assertTrue(cy._on_gateway())
            self.assertEqual(cy._session_platform(), "telegram")

    def test_gateway_false_for_cli_platform(self):
        fake = _FakeSessionCtx()
        fake.set_session_vars(platform="cli")
        import types
        mod = types.ModuleType("gateway.session_context")
        mod.get_session_env = fake.get_session_env
        with mock.patch.dict(sys.modules, {"gateway.session_context": mod, "gateway": types.ModuleType("gateway")}):
            self.assertFalse(cy._on_gateway())

    # --- P1: session cwd ---------------------------------------------------

    def test_resolve_project_uses_resolve_agent_cwd(self):
        project_a = self.td / "project-a"
        project_a.mkdir()
        launch = self.td / "launch-dir"
        launch.mkdir()

        import types
        rcwd = types.ModuleType("agent.runtime_cwd")
        rcwd.resolve_agent_cwd = lambda: project_a
        agent_mod = types.ModuleType("agent")
        with mock.patch.dict(sys.modules, {"agent": agent_mod, "agent.runtime_cwd": rcwd}):
            with mock.patch("pathlib.Path.cwd", return_value=launch):
                resolved = cy._resolve_project(".")
        self.assertEqual(resolved, project_a.resolve())

    # --- P1: session-bound receipts ----------------------------------------

    def test_receipts_are_session_bound_and_invalidate_on_failure(self):
        project_a = self.td / "A"
        project_b = self.td / "B"
        project_a.mkdir()
        project_b.mkdir()

        scan_a = {
            "project": str(project_a),
            "files_scanned": 3,
            "counts": {"P0": 0, "P1": 1, "P2": 0, "P3": 0},
            "findings": [],
        }
        scan_b = {
            "project": str(project_b),
            "files_scanned": 9,
            "counts": {"P0": 0, "P1": 0, "P2": 2, "P3": 1},
            "findings": [],
        }

        def fake_run(args):
            # args look like ["scan", path, ...]
            root = Path(args[1])
            data = scan_a if root == project_a.resolve() else scan_b
            return {"ok": True, "exit": 0, "data": data}

        with mock.patch.object(cy, "run_checkyourself", side_effect=fake_run):
            cy._call_session_id = "session-A"
            res_a = cy.scan(str(project_a))
            self.assertTrue(res_a["ok"])
            self.assertTrue(res_a.get("receipt_id"))
            rid_a = res_a["receipt_id"]

            cy._call_session_id = "session-B"
            res_b = cy.scan(str(project_b))
            self.assertTrue(res_b["ok"])
            rid_b = res_b["receipt_id"]
            self.assertNotEqual(rid_a, rid_b)

            # Session A still points at A's receipt
            cy._call_session_id = "session-A"
            path_a = cy._findings_path()
            data_a = cy._load_receipt(path_a)
            self.assertEqual(data_a["project"], str(project_a))

            # Failed scan for A invalidates A's implicit pointer
            with mock.patch.object(cy, "run_checkyourself", return_value={"ok": False, "error": "boom"}):
                cy._call_session_id = "session-A"
                failed = cy.scan(str(project_a))
            self.assertFalse(failed["ok"])
            self.assertTrue(failed.get("implicit_receipt_invalidated"))
            with self.assertRaises(ValueError):
                cy._findings_path()

            # Session B still intact
            cy._call_session_id = "session-B"
            data_b = cy._load_receipt(cy._findings_path())
            self.assertEqual(data_b["project"], str(project_b))

    # --- P2: bounded envelope ----------------------------------------------

    def test_bounded_tool_json_never_cuts_mid_string(self):
        huge = {
            "ok": True,
            "receipt_id": "abc123",
            "receipt_path": str(self.data / "receipts" / "abc123.json"),
            "provenance": {"project": "/tmp/x", "session_id": "s1", "ts": 1},
            "data": {
                "project": "/tmp/x",
                "files_scanned": 1,
                "counts": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
                "findings": [],
                "scripts": {f"script-{i}": "x" * 200 for i in range(300)},
            },
        }
        encoded = cy._bounded_tool_json(huge, max_out=500)
        parsed = json.loads(encoded)  # must be valid JSON
        self.assertTrue(parsed.get("truncated"))
        self.assertTrue(parsed.get("ok"))
        self.assertEqual(parsed.get("artifact_ref"), huge["receipt_path"])
        self.assertIn("summary", parsed)

    def test_slash_fmt_summarizes_not_slices(self):
        res = {
            "ok": True,
            "receipt_id": "r1",
            "receipt_path": "/tmp/r1.json",
            "provenance": {"project": "/tmp/p", "session_id": "s"},
            "data": {
                "project": "/tmp/p",
                "files_scanned": 12,
                "counts": {"P0": 0, "P1": 1, "P2": 2, "P3": 3},
                "findings": [{"id": "F1"}] * 50,
                "blob": "Z" * 10000,
            },
        }
        text = cy._fmt(res)
        self.assertIn("receipt_id: r1", text)
        self.assertIn("P1=1", text)
        self.assertNotIn("ZZZZ", text)  # raw blob not dumped mid-cut

    # --- P2: ledger concurrency --------------------------------------------

    def test_concurrent_ledger_keeps_all_entries(self):
        barrier = threading.Barrier(2)
        errors = []

        def writer(n):
            try:
                # Force both threads to load before either writes by patching load.
                original_load = cy._load_json

                def gated_load(path, default):
                    data = original_load(path, default)
                    try:
                        barrier.wait(timeout=5)
                    except Exception:
                        pass
                    return data

                # Only gate the first read collision once; subsequent appends use lock.
                with mock.patch.object(cy, "_load_json", side_effect=gated_load):
                    cy._append_ledger({"ts": n, "tool": "checkyourself_score", "ok": True, "score": n})
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=writer, args=(1,))
        t2 = threading.Thread(target=writer, args=(2,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)
        self.assertFalse(errors, errors)
        ledger = cy._load_json(cy._ledger_path(), [])
        self.assertEqual(len(ledger), 2, ledger)
        scores = sorted(e.get("score") for e in ledger)
        self.assertEqual(scores, [1, 2])

    # --- P2: process-group timeout kill ------------------------------------

    def test_timeout_kills_process_group_descendants(self):
        marker = self.td / "child_marker"
        # Child script: ignore SIGTERM at the Python level? We rely on SIGKILL of the group.
        # Parent is a shell that spawns a long-running python grandchild.
        child_py = self.td / "sleepy.py"
        child_py.write_text(
            "import time, pathlib, sys\n"
            f"p = pathlib.Path({str(marker)!r})\n"
            "time.sleep(2.0)\n"
            "p.write_text('survived')\n",
            encoding="utf-8",
        )
        trampoline = self.td / "trampoline.sh"
        trampoline.write_text(
            "#!/bin/sh\n"
            f"python3 {child_py} &\n"
            "wait\n",
            encoding="utf-8",
        )
        trampoline.chmod(0o755)

        with mock.patch.object(cy, "_cfg", side_effect=lambda k: {
            "checkyourself_command": str(trampoline),
            "timeout_seconds": 1,
        }.get(k, cy.DEFAULTS.get(k))):
            res = cy.run_checkyourself([])
        self.assertFalse(res["ok"])
        self.assertIn("timed out", res.get("error", ""))
        # Give a moment; grandchild must not finish and write the marker.
        time.sleep(2.5)
        self.assertFalse(marker.exists(), "descendant survived timeout")

    # --- P2: data.counts ---------------------------------------------------

    def test_post_tool_reads_data_counts_including_p3(self):
        payload = {
            "ok": True,
            "data": {
                "project": "/tmp/p",
                "files_scanned": 4,
                "findings": [{"id": "a"}, {"id": "b"}],  # array, not dict
                "counts": {"P0": 0, "P1": 1, "P2": 1, "P3": 2},
            },
            "receipt_id": "r",
        }
        cy._on_post_tool("checkyourself_scan", {}, json.dumps(payload))
        ledger = cy._load_json(cy._ledger_path(), [])
        self.assertEqual(len(ledger), 1)
        self.assertEqual(
            ledger[0]["finding_counts"],
            {"P0": 0, "P1": 1, "P2": 1, "P3": 2},
        )
        self.assertTrue(ledger[0]["ok"])

    def test_post_tool_ok_true_on_truncated_envelope(self):
        payload = {
            "ok": True,
            "truncated": True,
            "summary": {
                "project": "/tmp/p",
                "files_scanned": 1,
                "counts": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
            },
            "artifact_ref": "/tmp/r.json",
            "receipt_id": "r",
        }
        cy._on_post_tool("checkyourself_scan", {}, json.dumps(payload))
        ledger = cy._load_json(cy._ledger_path(), [])
        self.assertEqual(len(ledger), 1)
        self.assertTrue(ledger[0]["ok"])
        self.assertTrue(ledger[0].get("truncated"))

    # --- P2: multimodal text extract ---------------------------------------

    def test_pre_llm_extracts_text_from_multimodal_blocks(self):
        msg = [
            {"type": "text", "text": "Tests pass, ready to ship"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}},
        ]
        out = cy._on_pre_llm(msg)
        self.assertIsInstance(out, dict)
        self.assertIn("Evidence Gate", out.get("context", ""))

    def test_pre_llm_ignores_image_only(self):
        msg = [{"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}}]
        self.assertIsNone(cy._on_pre_llm(msg))

    # --- P3: shlex inside try ----------------------------------------------

    def test_unmatched_slash_quote_returns_syntax_error(self):
        text = cy._slash('scan "')
        self.assertIn("No closing quotation", text)
        self.assertIn("Usage:", text)


if __name__ == "__main__":
    unittest.main()
