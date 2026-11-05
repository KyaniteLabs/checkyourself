"""Regression tests for plugins/checkyourself-hermes (Reviewer review on PR #50)."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import shlex
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "checkyourself-hermes"
CLI = ROOT / "tools" / "checkyourself.py"

# Import the plugin module directly by path so we do not require Hermes installed.
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


@contextlib.contextmanager
def _session(sid):
    token = cy._CALL_SESSION.set(sid)
    try:
        yield
    finally:
        cy._CALL_SESSION.reset(token)


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

        with mock.patch.dict(
            sys.modules,
            {
                "gateway": mock.MagicMock(),
                "gateway.session_context": mock.MagicMock(get_session_env=fake.get_session_env),
            },
        ):
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
            with _session("session-A"):
                res_a = cy.scan(str(project_a))
            self.assertTrue(res_a["ok"])
            self.assertTrue(res_a.get("receipt_id"))
            rid_a = res_a["receipt_id"]

            with _session("session-B"):
                res_b = cy.scan(str(project_b))
            self.assertTrue(res_b["ok"])
            rid_b = res_b["receipt_id"]
            self.assertNotEqual(rid_a, rid_b)

            # Session A still points at A's receipt
            with _session("session-A"):
                data_a = cy._load_receipt(cy._findings_path())
            self.assertEqual(data_a["project"], str(project_a))

            # Failed scan for A invalidates A's implicit pointer
            with mock.patch.object(cy, "run_checkyourself", return_value={"ok": False, "error": "boom"}):
                with _session("session-A"):
                    failed = cy.scan(str(project_a))
            self.assertFalse(failed["ok"])
            self.assertTrue(failed.get("implicit_receipt_invalidated"))
            with _session("session-A"), self.assertRaises(ValueError):
                cy._findings_path()

            # Session B still intact
            with _session("session-B"):
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

    def test_timeout_kills_sigterm_resistant_descendant(self):
        marker = self.td / "child_marker"
        ready = self.td / "child_ready"
        child_py = self.td / "stubborn.py"
        child_py.write_text(
            "import os, pathlib, signal, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            f"pathlib.Path({str(ready)!r}).write_text(str(os.getpid()))\n"
            "time.sleep(3.0)\n"
            f"pathlib.Path({str(marker)!r}).write_text('survived')\n",
            encoding="utf-8",
        )
        trampoline = self.td / "trampoline.sh"
        # The shell leader exits promptly on SIGTERM; its Python child ignores SIGTERM.
        trampoline.write_text(
            f"#!/bin/sh\ntrap 'exit 0' TERM\n{shlex.quote(sys.executable)} {shlex.quote(str(child_py))} &\nwait\n",
            encoding="utf-8",
        )
        trampoline.chmod(0o755)

        cfg = {"checkyourself_command": str(trampoline), "timeout_seconds": 1}
        with (
            mock.patch.object(cy, "_cfg", side_effect=lambda k: cfg.get(k, cy.DEFAULTS.get(k))),
            mock.patch.object(cy, "_KILL_GRACE", 0.5),
        ):
            res = cy.run_checkyourself([])
        self.assertFalse(res["ok"])
        self.assertIn("timed out", res.get("error", ""))
        self.assertTrue(ready.exists(), "child never installed its SIGTERM-ignoring handler")
        child_pid = int(ready.read_text())
        time.sleep(3.5)
        self.assertFalse(marker.exists(), "SIGTERM-resistant descendant survived timeout")
        status = Path(f"/proc/{child_pid}/status")
        if status.exists():  # reparented zombie awaiting reaping is dead, anything else is not
            self.assertIn("State:\tZ", status.read_text())

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

    # --- Reviewer pass 2: real-contract / concurrent regressions -----------------

    def _real_cli_cfg(self, **over):
        cfg = {
            "checkyourself_command": f"{shlex.quote(sys.executable)} {shlex.quote(str(CLI))}",
            "timeout_seconds": 120,
            "max_files": 500,
        }
        cfg.update(over)
        return mock.patch.object(cy, "_cfg", side_effect=lambda k: cfg.get(k, cy.DEFAULTS.get(k)))

    def _fixture_project(self, name="proj"):
        proj = self.td / name
        proj.mkdir()
        (proj / "package.json").write_text('{"name": "fixture", "scripts": {"test": "node t.js"}}\n')
        (proj / "index.js").write_text("console.log('hi')\n")
        return proj

    def test_overlapping_handlers_do_not_mix_session_ids(self):
        project_a = self.td / "A"
        project_b = self.td / "B"
        project_a.mkdir()
        project_b.mkdir()
        a_in, a_go, b_in, b_go = (threading.Event() for _ in range(4))

        def fake_run(args):
            root = Path(args[1])
            if root == project_a.resolve():
                a_in.set()
                a_go.wait(5)
            else:
                b_in.set()
                b_go.wait(5)
            return {"ok": True, "exit": 0, "data": {"project": str(root), "files_scanned": 1, "counts": {}}}

        results = {}

        def call(label, project):
            results[label] = json.loads(cy._tool_scan({"project": str(project)}, session_id=label))

        with mock.patch.object(cy, "run_checkyourself", side_effect=fake_run):
            ta = threading.Thread(target=call, args=("A", project_a))
            tb = threading.Thread(target=call, args=("B", project_b))
            ta.start()
            self.assertTrue(a_in.wait(5))  # A is paused inside the CLI call
            tb.start()
            self.assertTrue(b_in.wait(5))  # B entered while A is still running
            a_go.set()  # A resumes first and finishes while B is still running
            ta.join(5)
            b_go.set()
            tb.join(5)

        for label, project in (("A", project_a), ("B", project_b)):
            res = results[label]
            self.assertTrue(res["ok"], res)
            self.assertEqual(res["provenance"]["session_id"], label)
            envelope = json.loads(Path(res["receipt_path"]).read_text())
            self.assertEqual(envelope["session_id"], label)
            self.assertEqual(envelope["project"], str(project.resolve()))
            pointer = json.loads(cy._implicit_pointer_path(label).read_text())
            self.assertEqual(pointer["receipt_id"], res["receipt_id"])
        # Nothing leaks into later calls without a session kwarg.
        self.assertEqual(cy._session_id_from_host(), "")
        self.assertFalse(cy._implicit_pointer_path("").exists())

    def test_score_provenance_is_the_snapshot_actually_scored(self):
        project_a = self.td / "A"
        project_a.mkdir()
        scans = iter(["first", "second"])

        def fake_run(args):
            if args[0] == "scan":
                return {"ok": True, "exit": 0, "data": {"project": next(scans), "files_scanned": 1, "counts": {}}}
            scored = json.loads(Path(args[args.index("--findings") + 1]).read_text())
            # A concurrent scan in the same session replaces the pointer mid-score.
            second = cy.scan(str(project_a))
            holder["second"] = second["receipt_id"]
            return {"ok": True, "exit": 0, "data": {"schema": "checkyourself-score/1", "score": 50, "seen": scored}}

        holder = {}
        with mock.patch.object(cy, "run_checkyourself", side_effect=fake_run):
            first = json.loads(cy._tool_scan({"project": str(project_a)}, session_id="S"))
            res = json.loads(cy._tool_score({}, session_id="S"))
        self.assertEqual(res["data"]["seen"]["project"], "first")
        self.assertEqual(res["receipt_id"], first["receipt_id"])
        self.assertNotEqual(res["receipt_id"], holder["second"])

    def test_failed_scan_before_cli_invalidates_prior_receipt(self):
        project_a = self.td / "A"
        project_a.mkdir()
        ok = {"ok": True, "exit": 0, "data": {"project": str(project_a), "files_scanned": 1, "counts": {}}}
        failures = [
            ({"project": str(self.td / "does-not-exist")}, None),  # path validation
            ({"project": str(project_a), "max_files": "lots"}, None),  # argument validation
            ({"project": str(project_a)}, OSError("exec format error")),  # raised subprocess error
        ]
        for args, raised in failures:
            with self.subTest(args=args, raised=raised):
                with mock.patch.object(cy, "run_checkyourself", return_value=ok):
                    good = json.loads(cy._tool_scan({"project": str(project_a)}, session_id="A"))
                    self.assertTrue(good["ok"])
                    self.assertTrue(json.loads(cy._tool_score({}, session_id="A")).get("receipt_id"))
                side = {"side_effect": raised} if raised else {"return_value": ok}
                with mock.patch.object(cy, "run_checkyourself", **side):
                    bad = json.loads(cy._tool_scan(args, session_id="A"))
                    self.assertFalse(bad["ok"])
                    self.assertTrue(bad.get("implicit_receipt_invalidated"))
                    after = json.loads(cy._tool_score({}, session_id="A"))
                self.assertFalse(after["ok"])
                self.assertIn("no valid session receipt", after["error"])
                # Slash path behaves the same.
                self.assertIn("no valid session receipt", cy._slash("score"))

    def test_missing_executable_invalidates_prior_receipt(self):
        project_a = self.td / "A"
        project_a.mkdir()
        ok = {"ok": True, "exit": 0, "data": {"project": str(project_a), "files_scanned": 1, "counts": {}}}
        with mock.patch.object(cy, "run_checkyourself", return_value=ok):
            self.assertTrue(json.loads(cy._tool_scan({"project": str(project_a)}, session_id="A"))["ok"])
        with self._real_cli_cfg(checkyourself_command=str(self.td / "no-such-binary")):
            bad = json.loads(cy._tool_scan({"project": str(project_a)}, session_id="A"))
            self.assertFalse(bad["ok"])
            after = json.loads(cy._tool_score({}, session_id="A"))
        self.assertIn("no valid session receipt", after["error"])

    def test_real_cli_score_output_displays_score_mode_and_caps(self):
        proj = self._fixture_project()
        with self._real_cli_cfg():
            scanned = cy.scan(str(proj))
            self.assertTrue(scanned["ok"], scanned)
            res = cy.score()
            slash_text = cy._slash("score")
        self.assertTrue(res["ok"], res)
        data = res["data"]
        self.assertEqual(data["schema"], "checkyourself-score/1")
        self.assertIn("counts", data)  # real score JSON shares `counts` with scans
        text = cy._fmt(res)
        self.assertIn(f"score: {data['score']}", text)
        self.assertIn(f"score_mode: {data['score_mode']}", text)
        self.assertNotIn("files_scanned", text)
        for cap in data.get("caps_applied") or []:
            self.assertIn(f"cap: {cap['cap']}", text)
        self.assertIn(f"score: {data['score']}", slash_text)
        # Oversized score responses stay score-shaped.
        bounded = json.loads(cy._bounded_tool_json(res, max_out=1500))
        self.assertEqual(bounded["kind"], "score")
        self.assertEqual(bounded["summary"]["score"], data["score"])
        self.assertEqual(bounded["summary"]["score_mode"], data["score_mode"])
        self.assertEqual(cy._payload_kind(scanned["data"]), "scan")

    def test_explicit_receipt_in_project_dir_is_never_modified(self):
        proj = self._fixture_project()
        with self._real_cli_cfg():
            scanned = cy.scan(str(proj))
        self.assertTrue(scanned["ok"], scanned)
        caller_receipt = proj / "receipt.json"
        caller_receipt.write_bytes(Path(scanned["receipt_path"]).read_bytes())
        sibling = proj / "receipt.json.payload.json"
        sibling.write_text("caller-owned sentinel\n")
        before = {p.name: p.read_bytes() for p in proj.iterdir()}
        with self._real_cli_cfg():
            res = cy.score(str(caller_receipt))
            backlog_res = cy.backlog(str(caller_receipt))
        self.assertTrue(res["ok"], res)
        self.assertTrue(backlog_res["ok"], backlog_res)
        self.assertIn("score", res["data"])
        after = {p.name: p.read_bytes() for p in proj.iterdir()}
        self.assertEqual(before, after)
        tmp = self.data / "tmp"
        self.assertEqual(list(tmp.iterdir()) if tmp.exists() else [], [])

    def test_raw_findings_arrays_pass_through_to_cli(self):
        empty = self.td / "empty.json"
        empty.write_text("[]\n")
        one = self.td / "one.json"
        one.write_text(json.dumps([{"id": "F1", "severity": "P1", "title": "x", "category": "tests"}]))
        before = {p: p.read_bytes() for p in (empty, one)}
        with self._real_cli_cfg():
            for path in (empty, one):
                for fn in (cy.score, cy.backlog, cy.next_batch):
                    with self.subTest(path=path.name, fn=fn.__name__):
                        res = fn(str(path))
                        self.assertTrue(res["ok"], res)
                        self.assertIn("schema", res["data"])
            self.assertEqual(json.loads(cy._tool_score({"findings_path": str(empty)}))["data"]["counts"]["P0"], 0)
        self.assertEqual(before, {p: p.read_bytes() for p in (empty, one)})


if __name__ == "__main__":
    unittest.main()
