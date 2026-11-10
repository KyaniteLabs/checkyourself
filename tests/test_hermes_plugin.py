"""Evidence-gate guards, one isolating test per guard. Fixtures are synthetic and local."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("evidence_gate", ROOT / "hermes-plugin/evidence_gate.py")
gate_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate_mod)
State = gate_mod.State

PASSING_TEST = "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1, 1)\n"
FAILING_TEST = "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1, 2)\n"
UNITTEST_S11 = {"command": [sys.executable, "-m", "unittest", "-q"], "timeout_s": 60,
                "success": {"exit_zero": True, "regex_match": r"\bOK\b"}}


class Fixture:
    """A task workspace, an operator data dir and a worker environment."""

    def __init__(self, tmp, s11=None, test=PASSING_TEST, task="t_a", board="b"):
        self.base = Path(tmp).resolve()
        self.ws = self.base / "ws"
        self.ws.mkdir()
        (self.ws / ".git").mkdir()
        (self.ws / "test_fixture.py").write_text(test)
        self.write_s11(s11 or UNITTEST_S11)
        self.data = self.base / "data"
        self.gate = gate_mod.Gate(lambda: self.data)
        self.store = gate_mod.Store(self.data)
        self.env = {"HERMES_KANBAN_TASK": task, "HERMES_KANBAN_WORKSPACE": str(self.ws), "HERMES_KANBAN_BOARD": board}

    def write_s11(self, s11):
        cfg = self.ws / ".checkyourself"
        cfg.mkdir(exist_ok=True)
        (cfg / "challenges.json").write_text(json.dumps({"challenges": {"S11": s11}}))

    def approve(self, environ=None, **kw):
        approval = gate_mod.build_approval(self.ws, self.ws, environ or dict(os.environ), **kw)
        approvals = self.store.approvals() if self.store.configured() else {}
        approvals[approval["prefix"]] = approval
        self.store.save_approvals(approvals)
        return approval

    def worker(self, **extra):
        env = dict(self.env, **extra)
        return patch.dict(os.environ, env)

    def complete(self, args=None):
        return self.gate.pre_tool_call(tool_name="kanban_complete", args=args or {})

    def check(self, **args):
        return json.loads(self.gate.tool(dict({"claim": "fixture tests pass"}, **args)))

    def verdict_file(self, task="t_a", board="b"):
        return self.store.verdict_path("%s:%s" % (board, task))


def blocked_state(directive):
    assert directive and directive["action"] == "block", directive
    return directive["message"].split("[", 1)[1].split("]", 1)[0]


class InertAndEnrollment(unittest.TestCase):
    def test_unconfigured_gate_is_inert_and_warns_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            with fx.worker(), self.assertLogs(gate_mod.logger, "WARNING") as logs:
                self.assertIsNone(fx.complete())
                self.assertIsNone(fx.complete())
            self.assertEqual(len(logs.records), 1)
            self.assertFalse(fx.data.exists(), "an inert gate must not write state")

    def test_unenrolled_workspace_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            other = fx.base / "other"
            other.mkdir()
            (other / ".checkyourself").mkdir()
            (other / ".checkyourself/challenges.json").write_text(json.dumps({"challenges": {"S11": UNITTEST_S11}}))
            approval = gate_mod.build_approval(other, other, dict(os.environ))
            fx.store.save_approvals({approval["prefix"]: approval})
            with fx.worker():
                self.assertIsNone(fx.complete())
                self.assertEqual(fx.check()["state"], "NOT_ENROLLED")

    def test_unrelated_tools_pass_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with fx.worker():
                self.assertIsNone(fx.gate.pre_tool_call(tool_name="read_file", args={}))

    def test_missing_task_blocks_once_enrolled(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(blocked_state(fx.complete()), "NO_TASK")

    def test_prefix_covers_task_worktrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            approval = gate_mod.build_approval(fx.ws, fx.base, dict(os.environ))
            fx.store.save_approvals({approval["prefix"]: approval})
            with fx.worker():
                self.assertEqual(blocked_state(fx.complete()), "NO_VERDICT")


class PassAndBinding(unittest.TestCase):
    def test_check_then_complete_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with fx.worker():
                self.assertEqual(blocked_state(fx.complete()), "NO_VERDICT")
                result = fx.check()
                self.assertEqual(result["state"], "ALLOWED", result)
                self.assertTrue(result["executed"])
                self.assertIsNone(fx.complete())
                again = fx.check()
                self.assertEqual((again["state"], again["executed"]), ("ALLOWED", False))
                self.assertEqual(oct(fx.store.key_path.stat().st_mode & 0o777), "0o600")

    def test_completion_executes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with fx.worker():
                fx.check()
                with patch.object(gate_mod.subprocess, "Popen", side_effect=AssertionError("executed")):
                    self.assertIsNone(fx.complete())

    def test_new_file_anywhere_makes_verdict_stale(self):  # R4: unhashed dir conftest
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with fx.worker():
                fx.check()
                (fx.ws / "coverage").mkdir()
                (fx.ws / "coverage/conftest.py").write_text("raise SystemExit(0)\n")
                self.assertEqual(blocked_state(fx.complete()), "STALE_TREE")

    def test_edit_in_place_makes_verdict_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with fx.worker():
                fx.check()
                path = fx.ws / "test_fixture.py"
                stat = path.stat()
                path.write_text(PASSING_TEST.replace("1, 1", "2, 2"))
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                self.assertEqual(blocked_state(fx.complete()), "STALE_TREE")

    def test_out_of_tree_symlink_target_is_bound(self):  # R4: symlinked conftest
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            outside = fx.base / "outside_conftest.py"
            outside.write_text("x = 1\n")
            (fx.ws / "conftest.py").symlink_to(outside)
            fx.approve()
            with fx.worker():
                self.assertEqual(fx.check()["state"], "ALLOWED")
                outside.write_text("x = 2\n")
                self.assertEqual(blocked_state(fx.complete()), "STALE_TREE")

    def test_directory_symlink_leaving_workspace_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            (fx.base / "elsewhere").mkdir()
            (fx.ws / "pkg").symlink_to(fx.base / "elsewhere")
            fx.approve()
            with fx.worker():
                self.assertEqual(fx.check()["state"], "CONFIG_INVALID")

    def test_ignored_paths_do_not_invalidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve(ignore=["build"])
            (fx.ws / "build").mkdir()
            with fx.worker():
                fx.check()
                (fx.ws / ".git/HEAD").write_text("ref: x\n")
                (fx.ws / "build/out.txt").write_text("x")
                self.assertIsNone(fx.complete())

    def test_verdict_is_bound_to_task(self):  # R1: card-A evidence reused for card-B
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with fx.worker():
                fx.check()
            with fx.worker(HERMES_KANBAN_TASK="t_b"):
                self.assertEqual(blocked_state(fx.complete()), "NO_VERDICT")
                fx.verdict_file("t_b").parent.mkdir(parents=True, exist_ok=True)
                fx.verdict_file("t_b").write_bytes(fx.verdict_file("t_a").read_bytes())
                self.assertEqual(blocked_state(fx.complete()), "VERDICT_TAMPERED")

    def test_forged_verdict_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, test=FAILING_TEST)
            fx.approve()
            with fx.worker():
                self.assertEqual(fx.check()["state"], "TESTS_FAILED")
                record = json.loads(fx.verdict_file().read_text())
                record["status"] = "ALLOWED"
                fx.verdict_file().write_text(json.dumps(record))
                self.assertEqual(blocked_state(fx.complete()), "VERDICT_TAMPERED")
                record.pop("mac")
                fx.verdict_file().write_text(json.dumps(record))
                self.assertEqual(blocked_state(fx.complete()), "VERDICT_TAMPERED")

    def test_reapproval_invalidates_old_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with fx.worker():
                fx.check()
                fx.approve(max_run_s=30)
                self.assertEqual(blocked_state(fx.complete()), "APPROVAL_CHANGED")


class ForgeryAndExecution(unittest.TestCase):
    def test_agent_rewritten_s11_is_not_trusted(self):  # R1: forged S11 printing "passed"
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, test=FAILING_TEST)
            fx.approve()
            fx.write_s11({"command": [sys.executable, "-c", "print('OK')"], "success": {"regex_match": "OK"}})
            with fx.worker():
                result = fx.check()
                self.assertEqual((result["state"], result["executed"]), ("APPROVAL_CHANGED", False))
                self.assertEqual(blocked_state(fx.complete()), "APPROVAL_CHANGED")
                self.assertIsNone(fx.gate.pre_tool_call(tool_name=gate_mod.TOOL_NAME, args={"claim": "x"}))

    def test_failing_tests_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, test=FAILING_TEST)
            fx.approve()
            with fx.worker():
                self.assertEqual(fx.check()["state"], "TESTS_FAILED")
                self.assertEqual(blocked_state(fx.complete()), "TESTS_FAILED")

    def test_regex_is_required_even_on_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, s11={"command": [sys.executable, "-c", "print('nothing ran')"],
                                   "success": {"exit_zero": True, "regex_match": r"\d+ passed"}})
            fx.approve()
            with fx.worker():
                self.assertEqual(fx.check()["state"], "TESTS_FAILED")

    def test_exit_code_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, s11={"command": [sys.executable, "-c", "print('1 passed'); raise SystemExit(3)"],
                                   "success": {"exit_zero": True, "regex_match": "passed"}})
            fx.approve()
            with fx.worker():
                result = fx.check()
                self.assertEqual((result["state"], result["exit_code"]), ("TESTS_FAILED", 3))

    def test_swapped_executable_is_refused(self):  # R3: PATH wrapper
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / "bin"
            bindir.mkdir()
            runner = bindir / "runtests"
            runner.write_text("#!/bin/sh\necho OK\n")
            runner.chmod(0o755)
            fx = Fixture(tmp, s11={"command": ["runtests"], "success": {"regex_match": "OK"}})
            fx.approve(environ={"PATH": "%s:/usr/bin:/bin" % bindir, "HOME": tmp})
            with fx.worker(PATH="/usr/bin:/bin"):
                self.assertEqual(fx.check()["state"], "ALLOWED", "pinned PATH must be used, not the caller's")
                (fx.ws / "new_code.py").write_text("")
                runner.write_text("#!/bin/sh\necho OK # forged\n")
                self.assertEqual(fx.check()["state"], "APPROVAL_CHANGED")

    def test_child_env_is_pinned_not_inherited(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = "import os,sys; sys.exit(1 if 'LEAK_ME' in os.environ or os.environ.get('PYTHONNOUSERSITE') != '1' else 0)"
            fx = Fixture(tmp, s11={"command": [sys.executable, "-c", probe], "success": {"exit_zero": True}})
            fx.approve()
            with fx.worker(LEAK_ME="secret"):
                self.assertEqual(fx.check()["state"], "ALLOWED")

    def test_timeout_kills_whole_process_group(self):  # R5: orphaned challenge
        script = ("import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']);"
                  " print('child', p.pid, flush=True); time.sleep(60)")
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, s11={"command": [sys.executable, "-c", script], "timeout_s": 60,
                                   "success": {"exit_zero": True}})
            fx.approve(max_run_s=1)
            with fx.worker():
                start = time.monotonic()
                result = fx.check()
                self.assertLess(time.monotonic() - start, 1 + gate_mod.KILL_GRACE_S + 5)
            self.assertEqual(result["state"], "TIMEOUT")
            pid = int(result["output_tail"].split("child", 1)[1].split()[0])
            for _ in range(60):
                try:
                    stat = Path("/proc/%d/stat" % pid).read_text()
                except FileNotFoundError:
                    break
                if stat.rsplit(")", 1)[1].split()[0] == "Z":
                    break
                time.sleep(0.05)
            else:
                self.fail("grandchild %d survived the timeout" % pid)

    def test_tree_written_during_run_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, s11={"command": [sys.executable, "-c", "open('made.txt','w').write('x')"],
                                   "success": {"exit_zero": True}})
            fx.approve()
            with fx.worker():
                self.assertEqual(fx.check()["state"], "TREE_CHANGED_DURING_RUN")
                self.assertEqual(blocked_state(fx.complete()), "TREE_CHANGED_DURING_RUN")

    def test_retry_cap_and_operator_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, test=FAILING_TEST)
            fx.approve(max_attempts=2)
            with fx.worker():
                self.assertEqual([fx.check()["state"] for _ in range(2)], ["TESTS_FAILED"] * 2)
                capped = fx.check()
                self.assertEqual((capped["state"], capped["executed"]), ("RETRY_CAP_REACHED", False))
            args = argparse.Namespace(evidence_gate_cmd="reset", task="t_a", board="b")
            with patch.dict(os.environ, {}, clear=True), patch("builtins.print"):
                self.assertEqual(gate_mod.run_cli(fx.store, args, environ={}), 0)
            with fx.worker():
                self.assertTrue(fx.check()["executed"])

    def test_concurrent_check_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with fx.worker():
                held = fx.store.lock("b:t_a")
                try:
                    self.assertEqual(fx.check()["state"], "RUN_ERROR")
                finally:
                    held.close()


class Findings(unittest.TestCase):
    def test_p0_finding_blocks_and_project_suppression_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            (fx.ws / ".env").write_text("TOKEN=1\n")
            (fx.ws / ".checkyourself.json").write_text(json.dumps(
                {"suppress": [{"id": "CY-ENV-001", "reason": "agent says fine"}]}))
            fx.approve()
            with fx.worker():
                result = fx.check()
                self.assertEqual(result["state"], "FINDINGS_BLOCK", result)
                self.assertTrue(any("CY-ENV-001" in b for b in result["blockers"]))

    def test_operator_accepted_finding_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            (fx.ws / ".env").write_text("TOKEN=1\n")
            fx.approve(accept_findings=["CY-ENV-001", "CY-ENV-003"])
            with fx.worker():
                result = fx.check()
                self.assertEqual(result["state"], "ALLOWED", result)

    def test_caller_findings_only_add_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            with fx.worker():
                self.assertEqual(fx.check(known_blockers=["auth bypass open"])["state"], "FINDINGS_BLOCK")
                self.assertEqual(fx.check(known_blockers=[])["state"], "ALLOWED")


class OperatorConfig(unittest.TestCase):
    def test_tampered_or_missing_approvals_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            record = json.loads(fx.store.approvals_path.read_text())
            next(iter(record["approvals"].values()))["max_run_s"] = 99999
            fx.store.approvals_path.write_text(json.dumps(record))
            with fx.worker():
                self.assertEqual(blocked_state(fx.complete()), "CONFIG_INVALID")
                fx.store.approvals_path.unlink()
                self.assertEqual(blocked_state(fx.complete()), "CONFIG_INVALID")

    def test_approval_digest_must_cover_its_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            approval = fx.approve()
            approval["s11"]["timeout_s"] = 1
            fx.store.save_approvals({approval["prefix"]: approval})
            with fx.worker():
                self.assertEqual(blocked_state(fx.complete()), "CONFIG_INVALID")

    def test_s11_cwd_must_stay_in_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, s11=dict(UNITTEST_S11, cwd=".."))
            fx.approve()
            with fx.worker():
                self.assertEqual(fx.check()["state"], "CONFIG_INVALID")

    def test_cli_approve_needs_matching_digest_and_operator_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            ns = argparse.Namespace(evidence_gate_cmd="approve", project=str(fx.ws), prefix=None, max_run_s=None,
                                    max_attempts=None, ignore=None, accept_finding=None, confirm=None)
            env = {"PATH": os.environ["PATH"], "HOME": tmp}
            with patch("builtins.print"):
                self.assertEqual(gate_mod.run_cli(fx.store, ns, env), 0)
                self.assertFalse(fx.store.configured())
                ns.confirm = "0" * 64
                self.assertEqual(gate_mod.run_cli(fx.store, ns, env), 1)
                ns.confirm = gate_mod.build_approval(fx.ws, fx.ws, env)["digest"]
                self.assertEqual(gate_mod.run_cli(fx.store, ns, dict(env, HERMES_KANBAN_TASK="t_a")), 2)
                self.assertFalse(fx.store.configured())
                self.assertEqual(gate_mod.run_cli(fx.store, ns, env), 0)
            self.assertIn(str(fx.ws), fx.store.approvals())
            revoke = argparse.Namespace(evidence_gate_cmd="revoke", prefix=str(fx.ws))
            with patch("builtins.print"):
                self.assertEqual(gate_mod.run_cli(fx.store, revoke, env), 0)
            self.assertEqual(fx.store.approvals(), {})

    def test_approve_directive_names_the_approved_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            with fx.worker():
                self.assertIsNone(fx.gate.pre_tool_call(tool_name=gate_mod.TOOL_NAME, args={"claim": "x"}))
                approval = fx.approve()
                directive = fx.gate.pre_tool_call(tool_name=gate_mod.TOOL_NAME, args={"claim": "x"})
            self.assertEqual(directive["action"], "approve")
            self.assertEqual(directive["rule_key"], "checkyourself-evidence-check:" + approval["digest"][:16])
            self.assertIn("unittest", directive["message"])

    def test_board_lookup_for_non_worker_callers(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.approve()
            db = fx.base / "kanban.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE tasks (id TEXT, workspace_path TEXT)")
            conn.execute("INSERT INTO tasks VALUES ('t_x', ?)", (str(fx.ws),))
            conn.commit()
            conn.close()
            fake = types.ModuleType("hermes_cli.kanban_db")
            fake.kanban_db_path = lambda board=None: db
            pkg = types.ModuleType("hermes_cli")
            pkg.kanban_db = fake
            with patch.dict(sys.modules, {"hermes_cli": pkg, "hermes_cli.kanban_db": fake}), \
                    patch.dict(os.environ, {}, clear=True):
                self.assertEqual(blocked_state(fx.complete({"task_id": "t_x"})), "NO_VERDICT")
                self.assertEqual(blocked_state(fx.complete({"task_id": "t_missing"})), "WORKSPACE_UNRESOLVED")
                self.assertEqual(fx.check(task_id="t_x")["state"], "ALLOWED")
                self.assertIsNone(fx.complete({"task_id": "t_x"}))

    def test_fingerprint_respects_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(300):
                (root / ("f%d" % i)).write_text("")
            with self.assertRaises(gate_mod.GateError) as err:
                gate_mod.fingerprint(root, [], time.monotonic() - 1)
            self.assertEqual(err.exception.state, State.FINGERPRINT_TIMEOUT)
            self.assertEqual(gate_mod.fingerprint(root, [], time.monotonic() + 30),
                             gate_mod.fingerprint(root, [], time.monotonic() + 30))

    def test_internal_errors_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            with patch.object(gate_mod.Gate, "completion", side_effect=RuntimeError("boom")), \
                    self.assertLogs(gate_mod.logger, "ERROR"):
                self.assertEqual(blocked_state(fx.complete()), "RUN_ERROR")

    def test_messages_separate_operator_and_agent_faults(self):
        self.assertTrue(gate_mod.block_message(State.APPROVAL_CHANGED).startswith("Operator action needed"))
        self.assertTrue(gate_mod.block_message(State.TESTS_FAILED).startswith("Completion blocked"))
        self.assertEqual(set(gate_mod.ADVICE) | gate_mod.ALLOWING, set(State))

    def test_registration_is_pure(self):
        calls = []

        class Context:
            @property
            def state(self):
                raise AssertionError("state read during register")

            def __getattr__(self, key):
                return lambda *a, **kw: calls.append((key, a, kw))

        with patch("subprocess.Popen", side_effect=AssertionError("I/O during register")):
            gate_mod.register(Context())
        self.assertEqual([c[0] for c in calls],
                         ["register_tool", "register_hook", "register_command", "register_cli_command"])
        self.assertEqual(calls[0][2]["name"], gate_mod.TOOL_NAME)


if __name__ == "__main__":
    unittest.main()
