from __future__ import annotations

import json
import hashlib
import os
from copy import deepcopy
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Symbol-to-test map for verifier paths that CodeGraph cannot infer through
# subprocess/CLI indirection: challenge_from_root/_run_challenge are covered by
# the challenge tests below; _executed_receipt_hmac by the HMAC tests;
# semantic_challenge_errors and score_from_inputs by the vacuity/scoring tests.

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "checkyourself.py"


GOLDEN_REPORT = {
    "project": "Example App",
    "executive_summary": "Demo-ready, with launch work still required.",
    "app_purpose": "A small app for authenticated users to manage records.",
    "detected_stack": [
        {
            "area": "Backend",
            "technology": "Python",
            "evidence": "app.py",
            "confidence": "high",
        }
    ],
    "unknowns_and_assumptions": [
        {
            "unknown": "Production deployment target",
            "why_it_matters": "Rollback evidence depends on the target.",
            "how_to_resolve": "Confirm the deployment owner and platform.",
            "blocks_score": True,
        }
    ],
    "score": 72,
    "confidence": "medium",
    "score_breakdown": [
        {
            "category": "Testing and quality gates",
            "weight": 10,
            "awarded": 7,
            "evidence": "tests/test_app.py",
            "what_would_improve_it": "Add integration coverage.",
        }
    ],
    "score_caps": ["P1 cap at 74"],
    "coverage": [
        {
            "category": "Testing and quality gates",
            "checked": True,
            "evidence_reviewed": ["tests/test_app.py:1"],
            "missing_evidence": [],
            "follow_up_needed": False,
        }
    ],
    "findings": [
        {
            "id": "F-001",
            "severity": "P1",
            "finding": "Rollback is not proven",
            "plain_english_risk": "A bad deploy may take longer to recover from.",
            "evidence": ["deploy.md:1"],
            "recommended_fix": "Document and rehearse rollback.",
            "status": "open",
        }
    ],
    "evidence_table": [
        {
            "evidence": "Rollback documentation",
            "file_location": "deploy.md:1",
            "supports_finding": "F-001",
            "confidence": "medium",
        }
    ],
    "remediation_backlog": [
        {
            "finding_id": "F-001",
            "severity": "P1",
            "fix_summary": "Document and rehearse rollback.",
            "why_this_order": "Recovery is a launch gate.",
            "verification": "Follow the runbook in a staging drill.",
            "rollback": "Revert the documentation change.",
            "learning_value": "Release safety",
            "status": "open",
        }
    ],
    "first_approval_batch": ["F-001"],
    "full_remediation_path": [
        {
            "wave": "Wave 1",
            "included_findings": ["F-001"],
            "goal": "Remove the launch blocker.",
            "exit_criteria": "Rollback drill passes.",
        }
    ],
    "deferred_items": [],
    "questions": ["Which platform owns production rollback?"],
    "approval_prompts": ["Approve the rollback runbook fix?"],
    "learning_plan_seeds": ["Release safety and rollback rehearsals"],
    "dashboard_handoff": {
        "generated": False,
        "reason": "The optional dashboard was not requested.",
    },
}

REPORT_REQUIRED_SECTIONS = (
    "project",
    "executive_summary",
    "app_purpose",
    "detected_stack",
    "unknowns_and_assumptions",
    "score",
    "confidence",
    "score_breakdown",
    "score_caps",
    "coverage",
    "findings",
    "evidence_table",
    "remediation_backlog",
    "first_approval_batch",
    "full_remediation_path",
    "deferred_items",
    "questions",
    "approval_prompts",
    "learning_plan_seeds",
    "dashboard_handoff",
)


class CheckYourselfCliTests(unittest.TestCase):
    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=str(cwd or ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_format_json_no_write_emits_parseable_scan(self) -> None:
        result = self.run_cli(".", "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["tool"], "checkyourself-cli")
        self.assertEqual(data["schema"], "checkyourself-scan/1")
        self.assertIn("counts", data)
        guardrails = " ".join(data["public_repo_scope_guardrails"]).lower()
        self.assertIn("owner namespace", guardrails)
        self.assertIn("repository count", guardrails)
        self.assertIn("fork", guardrails)
        self.assertIn("verification timestamp", guardrails)
        self.assertIn("default-branch alert state", guardrails)
        self.assertIn("100% status", guardrails)

    def test_scan_subcommand_matches_machine_contract(self) -> None:
        result = self.run_cli("scan", ".", "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["schema"], "checkyourself-scan/1")
        self.assertIn("finding", data["findings"][0] if data["findings"] else {"finding": ""})
        self.assertIn("plain_english_risk", data["findings"][0] if data["findings"] else {"plain_english_risk": ""})

    def test_json_dash_stdout_has_no_console_noise(self) -> None:
        result = self.run_cli(".", "--json", "-", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["schema"], "checkyourself-scan/1")
        self.assertNotIn("Wrote context", result.stdout)
        self.assertNotIn("Findings", result.stdout)

    def test_describe_schema_and_coverage_are_agent_discoverable(self) -> None:
        describe = self.run_cli("describe", "--format", "json")
        self.assertEqual(describe.returncode, 0, describe.stderr)
        capabilities = json.loads(describe.stdout)
        self.assertEqual(capabilities["schema"], "checkyourself-capabilities/1")
        self.assertIn("mcp", capabilities)
        self.assertIn("score", {cmd["name"] for cmd in capabilities["commands"]})
        guardrails = " ".join(capabilities["public_repo_scope_guardrails"]).lower()
        self.assertIn("owner namespace", guardrails)
        self.assertIn("repository count", guardrails)
        self.assertIn("fork", guardrails)
        self.assertIn("dependency or security closure", guardrails)

        schema = self.run_cli("schema", "scan")
        self.assertEqual(schema.returncode, 0, schema.stderr)
        self.assertEqual(json.loads(schema.stdout)["title"], "CheckYourself Scan Result")

        coverage = self.run_cli("coverage", "--emit", "--format", "json")
        self.assertEqual(coverage.returncode, 0, coverage.stderr)
        coverage_data = json.loads(coverage.stdout)
        self.assertEqual(coverage_data["schema"], "checkyourself-coverage/1")
        self.assertEqual(len(coverage_data["surfaces"]), 20)

    def test_validate_accepts_scan_and_score_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text("print('hello')\n", encoding="utf-8")
            scan_result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
            self.assertEqual(scan_result.returncode, 0, scan_result.stderr)
            scan_path = project / "scan.json"
            scan_path.write_text(scan_result.stdout, encoding="utf-8")

            validate_scan = self.run_cli("validate", "--kind", "scan", str(scan_path))
            self.assertEqual(validate_scan.returncode, 0, validate_scan.stderr)

            score_result = self.run_cli("score", "--findings", str(scan_path), "--format", "json")
            self.assertEqual(score_result.returncode, 0, score_result.stderr)
            score_path = project / "score.json"
            score_path.write_text(score_result.stdout, encoding="utf-8")

            validate_score = self.run_cli("validate", "--kind", "score", str(score_path))
            self.assertEqual(validate_score.returncode, 0, validate_score.stderr)

    def test_scoring_caps_unresolved_p0(self) -> None:
        findings = {
            "findings": [
                {
                    "id": "F-001",
                    "severity": "P0",
                    "category": "C3",
                    "finding": "Hardcoded secret",
                    "plain_english_risk": "A credential is in source.",
                    "evidence": ["app.py (value omitted)"],
                    "status": "open",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "findings.json"
            path.write_text(json.dumps(findings), encoding="utf-8")
            result = self.run_cli("score", "--findings", str(path), "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertLessEqual(score["score"], 49)
        self.assertEqual(score["counts"]["P0"], 1)

    def test_scoring_contract_covers_all_documented_caps(self) -> None:
        cases = {
            "unresolved P0": (
                {"findings": [{"id": "F-P0", "severity": "P0", "category": "C4", "finding": "P0 risk", "status": "open"}]},
                None,
                49,
                49,
            ),
            "unresolved P1": (
                {"findings": [{"id": "F-P1", "severity": "P1", "category": "C4", "finding": "P1 risk", "status": "open"}]},
                None,
                74,
                74,
            ),
            "critical evidence gap": (
                {"findings": []},
                "critical",
                84,
                84,
            ),
            "high-score evidence gate": (
                {"findings": []},
                "high-score",
                90,
                90,
            ),
        }

        for label, (findings, coverage_kind, expected_cap, max_score) in cases.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    project = Path(tmp)
                    findings_path = project / "findings.json"
                    findings_path.write_text(json.dumps(findings), encoding="utf-8")
                    args = ["score", "--findings", str(findings_path), "--no-history", "--format", "json"]
                    if coverage_kind:
                        coverage = self._full_coverage()
                        if coverage_kind == "critical":
                            row = next(item for item in coverage["surfaces"] if item["id"] == "S06")
                            row.update(status="Unknown", missing_evidence=["restore receipt"])
                        else:
                            row = next(item for item in coverage["surfaces"] if item["id"] == "S11")
                            row.update(status="Unknown", missing_evidence=["test receipt"])
                        coverage_path = project / "coverage.json"
                        coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
                        args.extend(["--coverage", str(coverage_path)])
                    result = self.run_cli(*args)

                self.assertEqual(result.returncode, 0, result.stderr)
                score = json.loads(result.stdout)
                self.assertLessEqual(score["score"], max_score)
                self.assertIn(expected_cap, [cap["cap"] for cap in score["caps_applied"]])

    def test_nonfinite_numbers_are_rejected_across_schema_and_scoring_paths(self) -> None:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)

        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(kind="schema", value=repr(bad)):
                self.assertTrue(cy.validate_json_schema(bad, {"type": "number"}))
            with self.subTest(kind="weight", value=repr(bad)):
                with mock.patch.dict(cy.SCORE_CATEGORIES, {"C1": ("Data", bad)}):
                    with self.assertRaisesRegex(cy.CliError, "invalid scoring weight"):
                        cy.score_from_inputs({"findings": []})
            with self.subTest(kind="penalty", value=repr(bad)):
                with mock.patch.dict(cy.SEVERITY_PENALTIES, {"P1": bad}):
                    with self.assertRaisesRegex(cy.CliError, "invalid severity penalty"):
                        cy.score_from_inputs({
                            "findings": [{
                                "id": "F-NONFINITE",
                                "severity": "P1",
                                "category": "C1",
                                "finding": "finite input",
                            }]
                        })

        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "nonfinite.json"
            artifact.write_text('{"score": NaN}', encoding="utf-8")
            result = self.run_cli("validate", "--kind", "score", str(artifact), "--format", "json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["code"], 2)
        self.assertIn("non-finite", result.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            overflow = Path(tmp) / "overflow.json"
            overflow.write_text('{"score": 1e309}', encoding="utf-8")
            result = self.run_cli("validate", "--kind", "score", str(overflow), "--format", "json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["code"], 2)
        self.assertIn("non-finite", result.stderr)

    def test_malformed_json_fails_closed_for_cli_artifact_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            broken = project / "broken.json"
            broken.write_text("{ not valid JSON", encoding="utf-8")
            valid = project / "valid.json"
            valid.write_text('{"findings": []}', encoding="utf-8")
            cases = {
                "coverage": ["coverage", "--check", str(broken), "--format", "json"],
                "score": ["score", "--findings", str(broken), "--no-history", "--format", "json"],
                "backlog": ["backlog", "--findings", str(broken), "--format", "json"],
                "next": ["next", "--findings", str(broken), "--format", "json"],
                "diff": ["diff", "--old", str(broken), "--new", str(valid), "--format", "json"],
                "validate": ["validate", "--kind", "scan", str(broken), "--format", "json"],
            }
            for label, args in cases.items():
                with self.subTest(command=label):
                    result = self.run_cli(*args)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    error = json.loads(result.stdout)
                    self.assertEqual(error["code"], 2)
                    self.assertIn("invalid JSON", error["error"])
                    self.assertNotIn("Traceback", result.stderr)

            (project / "package.json").write_text("{ not valid JSON", encoding="utf-8")
            for command in ("scan", "diagnostic"):
                with self.subTest(command=command):
                    result = self.run_cli(command, str(project), "--format", "json", "--no-write")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = json.loads(result.stdout)
                    self.assertIn("could not be parsed", " ".join(data["stack_signals"]))

            init_result = self.run_cli("init", str(project), "--format", "json")
            self.assertEqual(init_result.returncode, 0, init_result.stderr)
            self.assertTrue((project / "CHECKYOURSELF_COVERAGE.generated.json").exists())

    def test_mcp_malformed_json_is_a_parse_error_not_a_crash(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "mcp"],
            text=True,
            input="{ not valid JSON\n",
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response["error"]["code"], -32700)
        self.assertNotIn("Traceback", result.stderr)

    def test_corrupt_receipts_do_not_become_false_empty_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            null_receipt = project / "null.json"
            null_receipt.write_text("null", encoding="utf-8")
            valid = project / "valid.json"
            valid.write_text('{"findings": []}', encoding="utf-8")

            cases = {
                "score": ["score", "--findings", str(null_receipt), "--no-history", "--format", "json"],
                "backlog": ["backlog", "--findings", str(null_receipt), "--format", "json"],
                "next": ["next", "--findings", str(null_receipt), "--format", "json"],
                "diff": ["diff", "--old", str(null_receipt), "--new", str(valid), "--format", "json"],
            }
            for label, args in cases.items():
                with self.subTest(command=label):
                    result = self.run_cli(*args)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    error = json.loads(result.stdout)
                    self.assertEqual(error["code"], 2)
                    self.assertIn("invalid findings artifact", error["error"])

            coverage = project / "coverage-mid-write.json"
            coverage.write_text('{"schema":"checkyourself-coverage/1","surfaces":[', encoding="utf-8")
            findings = project / "findings.json"
            findings.write_text('{"findings": []}', encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings), "--coverage", str(coverage),
                "--no-history", "--format", "json",
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)["code"], 2)
            self.assertNotIn("score", json.loads(result.stdout))

    def test_atomic_generated_writes_preserve_previous_contents_on_interruption(self) -> None:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            target = project / "generated.json"
            target.write_text("old receipt\n", encoding="utf-8")
            for failure in ("fsync", "replace"):
                with self.subTest(failure=failure):
                    target.write_text("old receipt\n", encoding="utf-8")
                    with mock.patch.object(cy.os, failure, side_effect=OSError("simulated interruption")):
                        with self.assertRaises(OSError):
                            cy.safe_write_text(target, "new receipt\n")
                    self.assertEqual(target.read_text(encoding="utf-8"), "old receipt\n")
                    self.assertEqual(list(project.glob(f".{target.name}.*.tmp")), [])

    def test_atomic_generated_write_survives_process_termination(self) -> None:
        child = """
import importlib.util
import os
import signal
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("cy", sys.argv[1])
cy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cy)

def terminate_before_replace(*_args):
    os.kill(os.getpid(), signal.SIGKILL)

cy.os.replace = terminate_before_replace
cy.safe_write_text(Path(sys.argv[2]), "new receipt\\n")
"""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            target = project / "generated.json"
            target.write_text("old receipt\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-c", child, str(CLI), str(target)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "old receipt\n")
            self.assertEqual(len(list(project.glob(f".{target.name}.*.tmp"))), 1)

    def test_atomic_generated_write_reports_permission_denial_without_touching_destination(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root can bypass directory permission denial")
        child = """
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("cy", sys.argv[1])
cy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cy)
cy.safe_write_text(Path(sys.argv[2]), "new receipt\\n")
"""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            target = project / "generated.json"
            target.write_text("old receipt\n", encoding="utf-8")
            original_mode = project.stat().st_mode & 0o777
            project.chmod(0o500)
            try:
                result = subprocess.run(
                    [sys.executable, "-c", child, str(CLI), str(target)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
            finally:
                project.chmod(original_mode)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PermissionError", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "old receipt\n")

    def test_interrupted_score_history_recovery_preserves_corrupt_backup(self) -> None:
        child = """
import importlib.util
import os
import signal
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("cy", sys.argv[1])
cy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cy)

original_replace = os.replace
replace_calls = 0

def terminate_during_recovery_replace(*args):
    global replace_calls
    replace_calls += 1
    if replace_calls == 2:
        os.kill(os.getpid(), signal.SIGKILL)
    return original_replace(*args)

cy.os.replace = terminate_during_recovery_replace
cy.append_score_history(Path(sys.argv[2]), cy.score_from_inputs({"findings": []}))
"""
        corrupted = "{ this is not valid json\n"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            history = project / "history.json"
            history.write_text(corrupted, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-c", child, str(CLI), str(history)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
            self.assertFalse(history.exists())
            self.assertEqual(
                (project / "history.json.corrupt.bak").read_text(encoding="utf-8"),
                corrupted,
            )
            self.assertEqual(len(list(project.glob(".history.json.*.tmp"))), 1)

    def test_report_parser_and_regenerator_are_byte_stable(self) -> None:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)

        generated = cy.regenerate_report(GOLDEN_REPORT)
        parsed = cy.parse_report(generated)
        regenerated = cy.regenerate_report(parsed)

        self.assertEqual(parsed, GOLDEN_REPORT)
        self.assertEqual(regenerated.encode("utf-8"), generated.encode("utf-8"))
        self.assertTrue(generated.endswith("\n"))

    def test_score_to_report_round_trip_and_invalid_mutations_fail_schema(self) -> None:
        findings = {
            "findings": [{
                "id": "F-ROUNDTRIP",
                "severity": "P1",
                "category": "C5",
                "finding": "Generated report test gap",
                "plain_english_risk": "The report must preserve the score contract.",
                "evidence": ["tests/test_checkyourself_cli.py:1"],
                "status": "open",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            findings_path = project / "findings.json"
            findings_path.write_text(json.dumps(findings), encoding="utf-8")
            score_result = self.run_cli(
                "score", "--findings", str(findings_path), "--no-history", "--format", "json",
            )
            self.assertEqual(score_result.returncode, 0, score_result.stderr)
            score = json.loads(score_result.stdout)
            backlog_result = self.run_cli(
                "backlog", "--findings", str(findings_path), "--format", "json",
            )
            self.assertEqual(backlog_result.returncode, 0, backlog_result.stderr)
            backlog = json.loads(backlog_result.stdout)

            report = deepcopy(GOLDEN_REPORT)
            report.update({
                "score": score["score"],
                "confidence": score["confidence"],
                "score_breakdown": score["per_category"],
                "score_caps": score["caps_applied"],
                "findings": findings["findings"],
                "remediation_backlog": backlog["remediation_backlog"],
                "first_approval_batch": backlog["first_approval_batch"],
            })
            report_path = project / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            valid = self.run_cli("validate", "--kind", "report", str(report_path), "--format", "json")
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertTrue(json.loads(valid.stdout)["valid"])

            mutations = {
                "missing score": lambda artifact: artifact.pop("score"),
                "score above maximum": lambda artifact: artifact.__setitem__("score", 101),
                "unknown confidence": lambda artifact: artifact.__setitem__("confidence", "certain"),
                "missing dashboard handoff": lambda artifact: artifact.pop("dashboard_handoff"),
            }
            for label, mutate in mutations.items():
                with self.subTest(mutation=label):
                    invalid = deepcopy(report)
                    mutate(invalid)
                    report_path.write_text(json.dumps(invalid), encoding="utf-8")
                    result = self.run_cli("validate", "--kind", "report", str(report_path), "--format", "json")
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertFalse(json.loads(result.stdout)["valid"])

    def test_diff_ci_treats_line_endings_as_noop_and_reports_real_changes(self) -> None:
        old = {
            "findings": [{
                "id": "CY-LINE-001", "severity": "P2", "category": "C6",
                "finding": "Line ending fixture", "status": "open",
            }]
        }
        added = {
            "findings": old["findings"] + [{
                "id": "CY-REAL-001", "severity": "P1", "category": "C5",
                "finding": "Actual regression", "status": "open",
            }]
        }

        def ending_variant(body: str, mode: str) -> str:
            lines = body.splitlines()
            if mode == "crlf":
                return "\r\n".join(lines) + "\r\n"
            return "".join(line + ("\r\n" if index % 2 == 0 else "\n") for index, line in enumerate(lines))

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            old_path = project / "old.json"
            new_path = project / "new.json"
            old_path.write_text(json.dumps(old, indent=2) + "\n", encoding="utf-8", newline="")
            new_path.write_bytes(ending_variant(json.dumps(old, indent=2), "crlf").encode("utf-8"))
            no_change = self.run_cli(
                "diff", "--old", str(old_path), "--new", str(new_path), "--ci", "--format", "json",
            )
            self.assertEqual(no_change.returncode, 0, no_change.stderr)
            no_change_data = json.loads(no_change.stdout)
            self.assertFalse(no_change_data["regression"])
            self.assertEqual(no_change_data["unchanged"], ["CY-LINE-001"])

            new_path.write_bytes(
                ("\ufeff" + json.dumps(old, indent=2) + "\n \t").encode("utf-8")
            )
            bom_trailing = self.run_cli(
                "diff", "--old", str(old_path), "--new", str(new_path), "--ci", "--format", "json",
            )
            self.assertEqual(bom_trailing.returncode, 0, bom_trailing.stderr)
            bom_trailing_data = json.loads(bom_trailing.stdout)
            self.assertFalse(bom_trailing_data["regression"])
            self.assertEqual(bom_trailing_data["unchanged"], ["CY-LINE-001"])

            new_path.write_bytes(ending_variant(json.dumps(added, indent=2), "mixed").encode("utf-8"))
            changed = self.run_cli(
                "diff", "--old", str(old_path), "--new", str(new_path), "--ci", "--format", "json",
            )
            self.assertEqual(changed.returncode, 1)
            changed_data = json.loads(changed.stdout)
            self.assertEqual([item["id"] for item in changed_data["added"]], ["CY-REAL-001"])
            self.assertEqual(changed_data["regressions"], [{
                "id": "CY-REAL-001", "type": "newly_open", "severity": "P1",
            }])

    def test_unicode_empty_and_huge_strings_survive_scan_and_receipt_commands(self) -> None:
        huge = "x" * 200_001
        finding = {
            "id": "F-✨",
            "severity": "P3",
            "category": "C4",
            "finding": "",
            "plain_english_risk": "",
            "evidence": [huge],
            "status": "open",
        }
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            unicode_dir = project / "空"
            unicode_dir.mkdir()
            (unicode_dir / "空.py").write_text("", encoding="utf-8")
            (project / "huge.txt").write_text("x" * 2_000_001, encoding="utf-8")
            scan_result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
            self.assertEqual(scan_result.returncode, 0, scan_result.stderr)
            scan = json.loads(scan_result.stdout)
            self.assertEqual(scan["scan_limits"]["files_oversized"], 1)
            self.assertTrue(any("空.py" in item for item in scan["tree"]))

            findings_path = project / "edge-findings.json"
            findings_path.write_text(json.dumps({"findings": [finding]}), encoding="utf-8")
            for label, args in {
                "score": ["score", "--findings", str(findings_path), "--no-history", "--format", "json"],
                "backlog": ["backlog", "--findings", str(findings_path), "--format", "json"],
                "next": ["next", "--findings", str(findings_path), "--format", "json"],
            }.items():
                with self.subTest(command=label):
                    result = self.run_cli(*args)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = json.loads(result.stdout)
                    if label == "score":
                        self.assertEqual(data["findings_scored"], ["F-✨"])
                    elif label == "backlog":
                        self.assertEqual(data["first_approval_batch"], ["F-✨"])
                    else:
                        self.assertEqual(data["finding_ids"], ["F-✨"])

            same_path = project / "same-edge-findings.json"
            same_path.write_text(json.dumps({"findings": [finding]}), encoding="utf-8")
            diff_result = self.run_cli(
                "diff", "--old", str(findings_path), "--new", str(same_path), "--format", "json",
            )
            self.assertEqual(diff_result.returncode, 0, diff_result.stderr)
            diff = json.loads(diff_result.stdout)
            self.assertEqual(diff["unchanged"], ["F-✨"])

    def test_caller_issued_not_applicable_receipts_are_unverified(self) -> None:
        coverage = self._full_coverage()
        row = next(item for item in coverage["surfaces"] if item["id"] == "S19")
        row.update(
            status="NotApplicable",
            evidence_reviewed=[],
            not_applicable_reason="Project has no AI or agent behavior.",
            # A reason alone is not delegated-responsibility evidence. This
            # legacy expectation is intentionally covered by the regression
            # test below; this test proves the accepted path retains weight.
            delegation_receipts=[],
        )
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            delegation = self._verification_artifact(project, "S19", suffix="delegation")
            row["delegation_receipts"] = [self._receipt(delegation, project, "provider contract", "temporary test tree", "delegated responsibility documented", surface_id="S19")]
            for item in coverage["surfaces"]:
                if item["id"] == "S19":
                    continue
                evidence = self._verification_artifact(project, item["id"])
                item["evidence_reviewed"] = [evidence.relative_to(project).as_posix()]
                item["evidence_receipts"] = [self._receipt(evidence, project, "fixture verifier", "temporary test tree", "non-empty artifact observed", surface_id=item["id"])]
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        c10 = next(category for category in score["per_category"] if category["id"] == "C10")
        self.assertEqual(c10["coverage_status"], "Unknown")
        self.assertEqual(score["confidence"], "low")
        self.assertLess(score["score"], 100)

    def test_not_applicable_without_delegation_evidence_is_unknown(self) -> None:
        coverage = self._full_coverage()
        for row in coverage["surfaces"]:
            row.update(status="NotApplicable", evidence_reviewed=[], not_applicable_reason="Handled elsewhere.")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )
            coverage_check = self.run_cli("coverage", "--check", str(coverage_path), "--format", "json")
            self.assertEqual(coverage_check.returncode, 1, coverage_check.stderr)
            checked = json.loads(coverage_check.stdout)
            self.assertFalse(checked["complete"])
            self.assertTrue(any("verifier-captured" in warning for warning in checked["warnings"]))
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertEqual(score["confidence"], "low")
        self.assertIn(84, [cap["cap"] for cap in score["caps_applied"]])
        self.assertLess(score["score"], 100)

    def test_backlog_and_next_return_first_batch(self) -> None:
        findings = {
            "findings": [
                {"id": "F-002", "severity": "P2", "category": "C6", "finding": "No CI", "status": "open"},
                {"id": "F-001", "severity": "P1", "category": "C5", "finding": "No tests", "status": "open"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "findings.json"
            path.write_text(json.dumps(findings), encoding="utf-8")
            backlog_result = self.run_cli("backlog", "--findings", str(path), "--format", "json")
            next_result = self.run_cli("next", "--findings", str(path), "--format", "json")

        self.assertEqual(backlog_result.returncode, 0, backlog_result.stderr)
        self.assertEqual(next_result.returncode, 0, next_result.stderr)
        self.assertEqual(json.loads(backlog_result.stdout)["first_approval_batch"], ["F-001"])
        self.assertEqual(json.loads(next_result.stdout)["finding_ids"], ["F-001"])

        with tempfile.TemporaryDirectory() as tmp:
            backlog_path = Path(tmp) / "backlog.json"
            next_path = Path(tmp) / "next.json"
            backlog_path.write_text(backlog_result.stdout, encoding="utf-8")
            next_path.write_text(next_result.stdout, encoding="utf-8")
            self.assertEqual(self.run_cli("validate", "--kind", "backlog", str(backlog_path)).returncode, 0)
            self.assertEqual(self.run_cli("validate", "--kind", "next", str(next_path)).returncode, 0)

    def test_secret_values_are_redacted_from_json_output(self) -> None:
        token = "sk-" + ("x" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text(f'API_KEY = "{token}"\n', encoding="utf-8")
            result = self.run_cli(str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(token, result.stdout)
        data = json.loads(result.stdout)
        self.assertEqual(data["counts"]["P0"], 1)
        self.assertIn("confidence: high", data["findings"][0]["evidence"][0])
        self.assertIn("app.py:1", data["findings"][0]["evidence"][0])

    def test_schema_token_field_does_not_create_p0_without_credential_shape(self) -> None:
        feedback_token = "feedback" + "Token"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            src = project / "src" / "dispatcher"
            src.mkdir(parents=True)
            (src / "tool-registry.ts").write_text(
                "\n".join([
                    f'const {feedback_token}Field = {{ type: "string", description: "Token for recording actual hours" }};',
                    f'const schema = {{ {feedback_token}: "aaaaaaaaaaaaaaaaaaaaaaaa" }};',
                    "",
                ]),
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["counts"]["P0"], 0)
        self.assertTrue(
            any("secret-like field" in finding["finding"].lower() for finding in data["findings"]),
            data["findings"],
        )

    def test_env_example_variants_and_commented_placeholders_do_not_create_secret_noise(self) -> None:
        llm_key = "LLM" + "_API_KEY"
        minimax_key = "MINIMAX" + "_API_KEY"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env.dogfood.example").write_text(
                "\n".join([
                    f"# {llm_key}=your_llm_api_key_here",
                    f"{minimax_key}=replace_me_with_your_key",
                    "",
                ]),
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn(".env.dogfood.example", data["env_files"])
        self.assertEqual(data["counts"]["P0"], 0)
        self.assertEqual(data["counts"]["P2"], 1)  # no CI only
        self.assertFalse(
            any("secret-like field" in finding["finding"].lower() for finding in data["findings"]),
            data["findings"],
        )
        self.assertFalse(
            any("local .env present" in finding["finding"].lower() for finding in data["findings"]),
            data["findings"],
        )

    def test_env_example_classifier_is_shared_across_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env.local").write_text("APP_MODE=local\n", encoding="utf-8")
            (project / ".env.local.example").write_text("APP_MODE=your_app_mode\n", encoding="utf-8")
            (project / ".gitignore").write_text(".env.*\n*.pem\n*.key\n", encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(set(data["env_files"]), {".env.local", ".env.local.example"})
        ids = {finding["id"] for finding in data["findings"]}
        self.assertNotIn("CY-ENV-001", ids)
        self.assertNotIn("CY-ENV-003", ids)

    def test_gitignore_comments_and_patterns_use_gitignore_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env").write_text("APP_MODE=local\n", encoding="utf-8")
            (project / ".gitignore").write_text(
                "# .env is intentionally not an ignore rule\n*.pem\n*.key\n",
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--deep", "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        ids = {finding["id"] for finding in data["findings"]}
        self.assertIn("CY-ENV-001", ids)
        secret_file_finding = next(finding for finding in data["findings"] if finding["id"] == "CY-SECRET-003")
        self.assertIn(".env", " ".join(secret_file_finding["evidence"]))
        self.assertNotIn("*.pem", " ".join(secret_file_finding["evidence"]))
        self.assertNotIn("*.key", " ".join(secret_file_finding["evidence"]))

    def test_gitignore_directory_rules_cover_nested_env_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            secrets_dir = project / "secrets"
            secrets_dir.mkdir()
            (secrets_dir / ".env").write_text("APP_MODE=local\n", encoding="utf-8")
            (project / ".gitignore").write_text("secrets/\n*.pem\n*.key\n", encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        ids = {finding["id"] for finding in json.loads(result.stdout)["findings"]}
        self.assertNotIn("CY-ENV-001", ids)
        self.assertIn("CY-ENV-002", ids)

    def test_invalid_suppression_config_is_structured_and_fail_closed(self) -> None:
        token = "sk-" + ("c" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text(f'API_KEY = "{token}"\n', encoding="utf-8")
            (project / ".checkyourself.json").write_text(
                json.dumps({"suppress": [None]}), encoding="utf-8"
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("suppression 0 must be an object", data["config_error"])
        ids = {finding["id"] for finding in data["findings"]}
        self.assertIn("CY-CONFIG-003", ids)
        self.assertIn("CY-SECRET-001", ids)
        self.assertEqual(data["suppression_count"], 0)

    def test_checkyourself_yml_can_suppress_reviewed_finding_without_counting_it(self) -> None:
        token = "sk-" + ("s" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text(f'API_KEY = "{token}"\n', encoding="utf-8")
            (project / ".checkyourself.yml").write_text(
                "\n".join([
                    "version: 1",
                    "suppress:",
                    "  - id: CY-SECRET-001",
                    "    reason: test fixture uses a fake credential shape",
                    '    files: ["app.py"]',
                    "    reviewed_by: unit-test",
                    '    reviewed_at: "2026-05-29"',
                    "",
                ]),
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(token, result.stdout)
        data = json.loads(result.stdout)
        self.assertEqual(data["counts"]["P0"], 0)
        suppressed = [finding for finding in data["findings"] if finding["status"] == "suppressed"]
        self.assertEqual([finding["id"] for finding in suppressed], ["CY-SECRET-001"])
        self.assertEqual(data["suppression_count"], 1)

    def test_multiline_yaml_suppression_paths_are_parsed(self) -> None:
        token = "sk-" + ("m" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text(f'API_KEY = "{token}"\n', encoding="utf-8")
            (project / ".checkyourself.yml").write_text(
                "\n".join([
                    "version: 1",
                    "suppress:",
                    "  - id: CY-SECRET-001",
                    "    reason: reviewed multiline path fixture",
                    "    files:",
                    "      - app.py",
                    "    reviewed_by: unit-test",
                    '    reviewed_at: "2026-09-04"',
                    "",
                ]),
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIsNone(data["config_error"])
        self.assertEqual(data["suppression_count"], 1)
        suppressed = next(finding for finding in data["findings"] if finding["id"] == "CY-SECRET-001")
        self.assertEqual(suppressed["suppression"]["reason"], "reviewed multiline path fixture")

    def test_path_scoped_suppression_does_not_hide_other_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src").mkdir()
            (project / "src" / "reviewed.py").write_text(
                'API_KEY = "abcdefghijklmnop"\n', encoding="utf-8"
            )
            (project / "src" / "runtime.py").write_text(
                'API_KEY = "qrstuvwxyzabcdef"\n', encoding="utf-8"
            )
            (project / ".checkyourself.yml").write_text(
                "\n".join([
                    "version: 1",
                    "suppress:",
                    "  - id: CY-SECRET-002",
                    "    reason: reviewed non-secret config field",
                    '    files: ["src/reviewed.py"]',
                    "",
                ]),
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        finding = next(item for item in data["findings"] if item["id"] == "CY-SECRET-002")
        self.assertEqual(finding["status"], "open")
        self.assertTrue(any("src/runtime.py" in evidence for evidence in finding["evidence"]))
        self.assertEqual(len(finding["suppressed_evidence"]), 1)
        self.assertIn("reviewed non-secret config field", finding["suppressed_evidence"][0]["reason"])

    def test_package_scripts_are_redacted_from_json_and_markdown(self) -> None:
        token = "sk-" + ("y" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "package.json").write_text(
                json.dumps({
                    "scripts": {
                        "deploy": f"API_KEY={token} node deploy.js",
                        "safe": "node safe.js",
                    }
                }),
                encoding="utf-8",
            )
            json_result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
            self.assertEqual(json_result.returncode, 0, json_result.stderr)
            self.assertNotIn(token, json_result.stdout)
            data = json.loads(json_result.stdout)
            self.assertIn("[REDACTED]", data["scripts"]["deploy"])

            markdown_path = project / "context.md"
            md_result = self.run_cli("scan", str(project), "--out", str(markdown_path), "--quiet")
            self.assertEqual(md_result.returncode, 0, md_result.stderr)
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertNotIn(token, markdown)
            self.assertIn("[REDACTED]", markdown)

    def test_mcp_stdio_exposes_thin_tools(self) -> None:
        messages = "\n".join([
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "unit-test", "version": "0"},
                },
            }),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "describe", "arguments": {}},
            }),
            "",
        ])
        result = subprocess.run(
            [sys.executable, str(CLI), "mcp"],
            text=True,
            input=messages,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([r["id"] for r in responses], [1, 2, 3])
        instructions = responses[0]["result"]["instructions"].lower()
        self.assertIn("owner namespaces", instructions)
        self.assertIn("fork exclusions", instructions)
        tools = responses[1]["result"]["tools"]
        tool_names = {tool["name"] for tool in tools}
        self.assertIn("score", tool_names)
        for tool in tools:
            description = tool["description"].lower()
            self.assertIn("requires no authentication", description, tool["name"])
            self.assertIn("does not make network calls", description, tool["name"])
            self.assertIn("does not modify local files", description, tool["name"])
            self.assertIn("no external rate limits", description, tool["name"])
            self.assertTrue(tool["annotations"]["readOnlyHint"], tool["name"])
            self.assertFalse(tool["annotations"]["destructiveHint"], tool["name"])

        by_name = {tool["name"]: tool for tool in tools}
        for tool_name in ("score", "backlog", "next"):
            findings_schema = by_name[tool_name]["inputSchema"]["properties"]["findings"]
            self.assertEqual(findings_schema["type"], ["object", "array"], tool_name)
            self.assertIn("list", findings_schema["description"].lower(), tool_name)

        structured = responses[2]["result"]["structuredContent"]
        self.assertEqual(structured["schema"], "checkyourself-capabilities/1")

    def test_score_without_coverage_uses_scan_estimate_and_writes_explicit_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (project / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            workflow = project / ".github" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "ci.yml").write_text("name: ci\non: [push]\njobs: {}\n", encoding="utf-8")
            scan_result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
            self.assertEqual(scan_result.returncode, 0, scan_result.stderr)
            scan_path = project / "scan.json"
            scan_path.write_text(scan_result.stdout, encoding="utf-8")

            score_result = self.run_cli(
                "score", "--findings", str(scan_path), "--history", "--format", "json",
            )

            self.assertEqual(score_result.returncode, 0, score_result.stderr)
            score = json.loads(score_result.stdout)
            self.assertEqual(score["score_mode"], "scan-derived-estimate")
            # Estimates must never report a launch-ready number: missing
            # coverage evidence caps every estimate at 84.
            self.assertLessEqual(score["score"], 84)
            self.assertIn(84, [cap["cap"] for cap in score["caps_applied"]])
            self.assertFalse(score["coverage_complete"])
            self.assertEqual(score["confidence"], "low")
            self.assertTrue(score["manual_evidence_needed"])
            history = json.loads((project / ".checkyourself-score-history.json").read_text(encoding="utf-8"))
        self.assertEqual(history[-1]["score"], score["score"])

    def test_scan_derived_presence_is_not_proof_of_tests_or_ci(self) -> None:
        cases = {
            "empty test file": "tests",
            "invalid CI file": "ci",
        }
        for label, surface in cases.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    project = Path(tmp)
                    if surface == "tests":
                        (project / "test_empty.py").write_text("", encoding="utf-8")
                    else:
                        workflow = project / ".github" / "workflows"
                        workflow.mkdir(parents=True)
                        (workflow / "ci.yml").write_text("jobs: [not valid", encoding="utf-8")

                    scan_result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
                    self.assertEqual(scan_result.returncode, 0, scan_result.stderr)
                    scan_path = project / "scan.json"
                    scan_path.write_text(scan_result.stdout, encoding="utf-8")
                    score_result = self.run_cli(
                        "score", "--findings", str(scan_path), "--no-history", "--format", "json",
                    )

                self.assertEqual(score_result.returncode, 0, score_result.stderr)
                score = json.loads(score_result.stdout)
                categories = {item["id"]: item for item in score["per_category"]}
                category_id = "C5" if surface == "tests" else "C6"
                if surface == "tests":
                    self.assertEqual(categories["C5"]["coverage_status"], "Unknown")
                    self.assertIn("file presence does not prove", " ".join(categories["C5"]["missing_evidence"]))
                else:
                    self.assertEqual(categories["C6"]["coverage_status"], "Unknown")
                    self.assertIn("file presence does not prove", " ".join(categories["C6"]["missing_evidence"]))
                self.assertNotEqual(categories[category_id]["coverage_status"], "Pass")

    def test_audit_defaults_leave_fixture_tree_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text("print('hello')\n", encoding="utf-8")
            findings_path = project / "findings.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            before = sorted(
                (path.relative_to(project).as_posix(), path.read_bytes())
                for path in project.rglob("*") if path.is_file()
            )

            scan_result = self.run_cli("scan", str(project), "--format", "json")
            self.assertEqual(scan_result.returncode, 0, scan_result.stderr)
            score_result = self.run_cli(
                "score", "--findings", str(findings_path), "--format", "json",
            )
            self.assertEqual(score_result.returncode, 0, score_result.stderr)

            after = sorted(
                (path.relative_to(project).as_posix(), path.read_bytes())
                for path in project.rglob("*") if path.is_file()
            )
            self.assertEqual(after, before)
            self.assertFalse((project / "CHECKYOURSELF_PROJECT_CONTEXT.generated.md").exists())
            self.assertFalse((project / ".checkyourself-score-history.json").exists())

    def test_coverage_emit_writes_default_file_in_text_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_cli("coverage", "--emit", cwd=project)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Wrote coverage skeleton", result.stdout)
            self.assertIn("fill coverage.json with evidence, then re-run score", result.stdout.lower())
            coverage_path = project / "CHECKYOURSELF_COVERAGE.generated.json"
            self.assertTrue(coverage_path.exists())
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            self.assertEqual(coverage["schema"], "checkyourself-coverage/1")

    def test_failed_json_score_redirect_emits_parseable_error_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            findings_path = project / "findings.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            emit = self.run_cli("coverage", "--emit", cwd=project)
            self.assertEqual(emit.returncode, 0, emit.stderr)
            coverage_path = project / "CHECKYOURSELF_COVERAGE.generated.json"
            output_path = project / "score.json"
            with output_path.open("w", encoding="utf-8") as output:
                result = subprocess.run(
                    [
                        sys.executable, str(CLI), "score", "--findings", str(findings_path),
                        "--coverage", str(coverage_path), "--no-history", "--format", "json",
                    ],
                    cwd=str(project), text=True, stdout=output, stderr=subprocess.PIPE, check=False,
                )

            self.assertEqual(result.returncode, 2)
            error = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(error["code"], 2)
            self.assertIn("fill coverage.json with evidence, then re-run score", error["error"].lower())
            self.assertIn("error:", result.stderr)

    def test_diagnostic_alias_emits_scan_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text("print('hello')\n", encoding="utf-8")
            result = self.run_cli("diagnostic", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["schema"], "checkyourself-scan/1")

    def test_deep_scan_flags_mutable_github_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            workflow = project / ".github" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "ci.yml").write_text(
                "name: ci\non: [push]\njobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--deep", "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(
            any("mutable github action" in finding["finding"].lower() for finding in data["findings"]),
            data["findings"],
        )

    def test_repository_includes_composite_github_action(self) -> None:
        action = ROOT / ".github" / "actions" / "checkyourself" / "action.yml"
        self.assertTrue(action.exists())
        text = action.read_text(encoding="utf-8")
        self.assertIn("runs:", text)
        self.assertIn("fail-on-p0", text)

    def test_composite_action_passes_inputs_through_env_not_interpolation(self) -> None:
        action = ROOT / ".github" / "actions" / "checkyourself" / "action.yml"
        text = action.read_text(encoding="utf-8")
        # Untrusted inputs must reach the shell via env vars, never via ${{ }}
        # expansion inside a run: body (script-injection sink).
        self.assertNotIn('"${{ inputs.project }}"', text)
        self.assertIn("CY_PROJECT: ${{ inputs.project }}", text)
        self.assertIn('os.environ["CY_OUTPUT"]', text)

    def test_scan_reports_truncation_when_file_cap_is_hit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for i in range(5):
                (project / f"f{i}.py").write_text("x = 1\n", encoding="utf-8")
            result = self.run_cli("scan", str(project), "--max-files", "2", "--format", "json", "--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["scan_limits"]["truncated"])
        self.assertEqual(data["files_scanned"], 2)
        self.assertGreater(data["scan_limits"]["files_beyond_limit"], 0)
        self.assertTrue(data["scan_limits"]["incomplete"])
        self.assertTrue(data["scan_limits"]["truncated_files"])

    def test_scan_reports_oversized_files_as_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "large.py").write_bytes(b"x" * 2_000_001)
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        limits = data["scan_limits"]
        self.assertEqual(data["files_scanned"], 0)
        self.assertEqual(limits["files_oversized"], 1)
        self.assertEqual(limits["oversized_files"], ["large.py"])
        self.assertTrue(limits["incomplete"])

    def test_scan_reads_eligible_content_past_previous_read_cap(self) -> None:
        token = "sk-" + ("e" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text(
                ("# padding\n" * 7_000) + f'API_KEY = "{token}"\n',
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        secret = next(f for f in data["findings"] if f["id"] == "CY-SECRET-001")
        self.assertGreater(int(secret["evidence"][0].split(":", 2)[1].split(" ", 1)[0]), 60_000 // 10)
        self.assertFalse(data["scan_limits"]["incomplete"])

    def test_extensionless_config_files_are_scanned_for_secrets(self) -> None:
        token = "sk-" + ("d" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "Dockerfile").write_text(f"FROM python:3.14\nENV API_KEY={token}\n", encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        secret = next(f for f in data["findings"] if f["id"] == "CY-SECRET-001")
        self.assertIn("Dockerfile:2", " ".join(secret["evidence"]))

    def test_filename_substrings_do_not_create_test_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "latest.py").write_text("print('not a test')\n", encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["tests"], [])
        self.assertIn("CY-TEST-001", {finding["id"] for finding in data["findings"]})

    def test_scan_does_not_read_symlinked_files_out_of_tree(self) -> None:
        # Built by concatenation so the committed source never contains a
        # credential-shaped literal (keeps gitleaks clean).
        aws_shape = "AKIA" + "IOSFODNN7EXAMPLEXX"
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as tmp:
            secret = Path(outside) / "real_secret.env"
            secret.write_text(f"AWS_SECRET_ACCESS_KEY={aws_shape}\n", encoding="utf-8")
            project = Path(tmp)
            (project / "config.env").symlink_to(secret)
            (project / "app.py").write_text("print('ok')\n", encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertGreaterEqual(data["scan_limits"]["symlinks_skipped"], 1)
        self.assertNotIn("config.env", json.dumps(data["findings"]))

    def test_secret_scan_reports_multiple_credentials_in_one_file(self) -> None:
        # Built by concatenation so the committed source never contains a
        # credential-shaped literal (keeps gitleaks clean).
        key_one = "AKIA" + "1234567890ABCDEF"
        key_two = "AKIA" + "ZZZZZZZZZZZZZZZZ"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "creds.env").write_text(
                f"{key_one}\nfiller=1\n{key_two}\n",
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        secret = next(f for f in data["findings"] if f["id"] == "CY-SECRET-001")
        located = " ".join(secret["evidence"])
        self.assertIn(":1", located)
        self.assertIn(":3", located)

    def test_findings_use_stable_semantic_rule_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text("print('hi')\n", encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        ids = {f["id"] for f in json.loads(result.stdout)["findings"]}
        self.assertIn("CY-TEST-001", ids)
        self.assertNotIn("CY-001", ids)

    def test_debug_flag_and_default_credentials_are_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "settings.py").write_text("DEBUG = True\n", encoding="utf-8")
            (project / "docker-compose.yml").write_text(
                "services:\n  db:\n    environment:\n      POSTGRES_PASSWORD: postgres\n",
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        ids = {f["id"] for f in json.loads(result.stdout)["findings"]}
        self.assertIn("CY-CONFIG-001", ids)
        self.assertIn("CY-CONFIG-002", ids)

    def test_cors_wildcard_and_dangerous_sink_are_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "server.js").write_text(
                'app.use(cors({ origin: "*" }));\nconst r = eval(userInput);\n',
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        ids = {f["id"] for f in json.loads(result.stdout)["findings"]}
        self.assertIn("CY-API-001", ids)
        self.assertIn("CY-CODE-001", ids)

    def test_context_suppressions_keep_real_secret_and_sink_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "docs").mkdir()
            (project / "tests").mkdir()
            (project / "docs" / "audit.md").write_text(
                'API_KEY = "abcdefghijklmnop"\neval(userInput)\n', encoding="utf-8"
            )
            (project / "tests" / "test_example.py").write_text(
                'API_KEY = "qrstuvwxyzabcdef"\neval(userInput)\n', encoding="utf-8"
            )
            (project / "detector.py").write_text(
                "patterns = [{pattern: /eval\\s*\\(/, label: 'eval()'}]\n", encoding="utf-8"
            )
            (project / "guarded.js").write_text(
                "const blockedPatterns = findDangerous(code);\n"
                "if (blockedPatterns.length > 0) { warn(); } else { eval(wrappedCode); }\n",
                encoding="utf-8",
            )
            (project / "app.py").write_text(
                'API_KEY = "1234567890abcdef"\neval(userInput)\n', encoding="utf-8"
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        ids = {finding["id"] for finding in data["findings"]}
        self.assertIn("CY-SECRET-002", ids)
        self.assertIn("CY-CODE-001", ids)
        secret = next(finding for finding in data["findings"] if finding["id"] == "CY-SECRET-002")
        sink = next(finding for finding in data["findings"] if finding["id"] == "CY-CODE-001")
        self.assertTrue(any("app.py" in evidence for evidence in secret["evidence"]))
        self.assertTrue(any("app.py" in evidence for evidence in sink["evidence"]))
        suppressed = data["context_suppressions"]
        self.assertGreaterEqual(len(suppressed), 4)
        reasons = {item["reason"] for item in suppressed}
        self.assertTrue(any("documentation" in reason for reason in reasons))
        self.assertTrue(any("detector source" in reason for reason in reasons))
        self.assertTrue(any("guarded eval" in reason for reason in reasons))

    def test_missing_lockfile_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "package.json").write_text('{"name": "x"}\n', encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        ids = {f["id"] for f in json.loads(result.stdout)["findings"]}
        self.assertIn("CY-SUPPLY-002", ids)

    def test_non_object_package_json_is_reported_without_traceback(self) -> None:
        for label, package_json in {
            "null": "null\n",
            "array": "[]\n",
            "boolean": "true\n",
        }.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    project = Path(tmp)
                    (project / "package.json").write_text(package_json, encoding="utf-8")
                    result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                data = json.loads(result.stdout)
                self.assertIn("package.json exists but must contain a JSON object", data["stack_signals"])

    def test_test_path_secrets_still_detected_but_heuristics_skip_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            tests_dir = project / "tests"
            tests_dir.mkdir()
            # A real credential shape in a test file must still surface.
            # Built by concatenation so the committed test source never
            # contains a credential-shaped literal (keeps gitleaks clean).
            aws_shape = "AKIA" + "1234567890ABCDEF"
            (tests_dir / "test_thing.py").write_text(f"KEY = '{aws_shape}'\nDEBUG = True\n", encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        ids = {f["id"] for f in json.loads(result.stdout)["findings"]}
        self.assertIn("CY-SECRET-001", ids)  # secret still found
        self.assertNotIn("CY-CONFIG-001", ids)  # debug flag heuristic skips test paths

    def test_coverage_backed_score_blocks_thin_pass_gaming(self) -> None:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)
        surfaces = [
            {"id": sid, "surface": surface, "category": category,
             "status": "Pass", "evidence_reviewed": ["x"]}
            for sid, surface, category in cy.COVERAGE_SURFACES[:10]
        ]
        coverage = {"schema": "checkyourself-coverage/1", "surfaces": surfaces}
        with tempfile.TemporaryDirectory() as tmp:
            findings_path = Path(tmp) / "findings.json"
            coverage_path = Path(tmp) / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path),
                "--coverage", str(coverage_path), "--no-history", "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertFalse(score["coverage_complete"])
        self.assertNotEqual(score["confidence"], "high")
        self.assertLess(score["score"], 100)

    def _run_mcp_validate(self, kind: str, artifact: object) -> dict:
        messages = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                "name": "validate", "arguments": {"kind": kind, "artifact": artifact},
            }}),
            "",
        ])
        result = subprocess.run(
            [sys.executable, str(CLI), "mcp"],
            text=True,
            input=messages,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = {json.loads(line)["id"]: json.loads(line) for line in result.stdout.splitlines()}
        return responses[2]

    def test_dashboard_one_of_rejects_empty_and_garbage_artifacts(self) -> None:
        for label, artifact in {
            "empty": {},
            "garbage": {"garbage": True},
        }.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    artifact_path = Path(tmp) / "dashboard.json"
                    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
                    cli_result = self.run_cli("validate", "--kind", "dashboard", str(artifact_path))
                self.assertEqual(cli_result.returncode, 1, cli_result.stderr)
                self.assertIn("oneOf", cli_result.stdout)

                mcp_response = self._run_mcp_validate("dashboard", artifact)
                result = mcp_response["result"]
                self.assertFalse(result["structuredContent"]["valid"])
                self.assertTrue(result["isError"] is False)

    def _run_mcp_requests(self, requests, cwd: Path | None = None) -> dict:
        workdir = cwd or ROOT
        messages = "\n".join([*(json.dumps(request) for request in requests), ""])
        result = subprocess.run(
            [sys.executable, str(CLI), "mcp"],
            text=True,
            input=messages,
            capture_output=True,
            check=False,
            cwd=workdir,
            env={**__import__("os").environ, "CHECKYOURSELF_SCAN_ROOT": str(workdir)},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return {json.loads(line)["id"]: json.loads(line) for line in result.stdout.splitlines()}

    def test_validate_rejects_empty_machine_artifacts_in_cli_and_mcp(self) -> None:
        kinds = (
            "scan", "coverage", "score", "backlog", "next", "diff",
            "learning-plan", "capabilities", "dashboard-data",
        )
        for kind in kinds:
            with self.subTest(kind=kind):
                with tempfile.TemporaryDirectory() as tmp:
                    artifact_path = Path(tmp) / f"{kind}.json"
                    artifact_path.write_text("{}", encoding="utf-8")
                    cli_result = self.run_cli("validate", "--kind", kind, str(artifact_path), "--format", "json")
                self.assertEqual(cli_result.returncode, 1, cli_result.stderr)
                validation = json.loads(cli_result.stdout)
                self.assertFalse(validation["valid"])
                self.assertTrue(validation["errors"])

                mcp_response = self._run_mcp_validate(kind, {})
                mcp_result = mcp_response["result"]
                self.assertFalse(mcp_result["structuredContent"]["valid"])
                self.assertFalse(mcp_result["isError"])

    def test_golden_dashboard_and_report_fixtures_validate_in_cli_and_mcp(self) -> None:
        dashboard_paths = (
            ROOT / "samples" / "sample-dashboard-data.json",
            ROOT / "05_OUTPUT_TEMPLATES" / "dashboard-data.example.json",
        )
        dashboard_artifacts = [json.loads(path.read_text(encoding="utf-8")) for path in dashboard_paths]
        golden_artifacts = [("dashboard", artifact) for artifact in dashboard_artifacts]
        golden_artifacts.append(("report", GOLDEN_REPORT))

        for kind, artifact in golden_artifacts:
            with self.subTest(kind=kind):
                with tempfile.TemporaryDirectory() as tmp:
                    artifact_path = Path(tmp) / f"{kind}.json"
                    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
                    cli_result = self.run_cli("validate", "--kind", kind, str(artifact_path))
                self.assertEqual(cli_result.returncode, 0, cli_result.stderr)
                self.assertIn("Valid", cli_result.stdout)

                mcp_response = self._run_mcp_validate(kind, artifact)
                result = mcp_response["result"]
                self.assertTrue(result["structuredContent"]["valid"])
                self.assertFalse(result["isError"])

    def test_cli_outputs_are_deterministic_goldens_after_timestamp_normalization(self) -> None:
        def without_timestamps(value):
            if isinstance(value, dict):
                return {
                    key: without_timestamps(item)
                    for key, item in value.items()
                    if key != "generated_at"
                }
            if isinstance(value, list):
                return [without_timestamps(item) for item in value]
            return value

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (project / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            workflow = project / ".github" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "ci.yml").write_text("name: ci\non: [push]\njobs: {}\n", encoding="utf-8")

            first_scan_result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
            second_scan_result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
            self.assertEqual(first_scan_result.returncode, 0, first_scan_result.stderr)
            self.assertEqual(second_scan_result.returncode, 0, second_scan_result.stderr)
            first_scan = json.loads(first_scan_result.stdout)
            second_scan = json.loads(second_scan_result.stdout)
            self.assertEqual(without_timestamps(first_scan), without_timestamps(second_scan))

            findings_path = project / "scan.json"
            findings_path.write_text(first_scan_result.stdout, encoding="utf-8")
            score_one = self.run_cli(
                "score", "--findings", str(findings_path), "--no-history", "--format", "json",
            )
            score_two = self.run_cli(
                "score", "--findings", str(findings_path), "--no-history", "--format", "json",
            )
            self.assertEqual(score_one.returncode, 0, score_one.stderr)
            self.assertEqual(score_two.returncode, 0, score_two.stderr)
            self.assertEqual(
                without_timestamps(json.loads(score_one.stdout)),
                without_timestamps(json.loads(score_two.stdout)),
            )

            backlog_one = self.run_cli("backlog", "--findings", str(findings_path), "--format", "json")
            backlog_two = self.run_cli("backlog", "--findings", str(findings_path), "--format", "json")
            self.assertEqual(backlog_one.returncode, 0, backlog_one.stderr)
            self.assertEqual(backlog_two.returncode, 0, backlog_two.stderr)
            self.assertEqual(
                without_timestamps(json.loads(backlog_one.stdout)),
                without_timestamps(json.loads(backlog_two.stdout)),
            )

    def test_cli_and_mcp_scan_score_validate_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (project / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            workflow = project / ".github" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "ci.yml").write_text("name: ci\non: [push]\njobs: {}\n", encoding="utf-8")

            scan_result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
            self.assertEqual(scan_result.returncode, 0, scan_result.stderr)
            scan = json.loads(scan_result.stdout)
            scan_path = project / "scan.json"
            scan_path.write_text(scan_result.stdout, encoding="utf-8")
            self.assertEqual(self.run_cli("validate", "--kind", "scan", str(scan_path)).returncode, 0)

            score_result = self.run_cli(
                "score", "--findings", str(scan_path), "--no-history", "--format", "json",
            )
            self.assertEqual(score_result.returncode, 0, score_result.stderr)
            score_path = project / "score.json"
            score_path.write_text(score_result.stdout, encoding="utf-8")
            self.assertEqual(self.run_cli("validate", "--kind", "score", str(score_path)).returncode, 0)

            emitted = {
                "capabilities": self.run_cli("describe", "--format", "json"),
                "coverage": self.run_cli("coverage", "--emit", "--format", "json"),
                "backlog": self.run_cli("backlog", "--findings", str(scan_path), "--format", "json"),
                "next": self.run_cli("next", "--findings", str(scan_path), "--format", "json"),
                "diff": self.run_cli("diff", "--old", str(scan_path), "--new", str(scan_path), "--format", "json"),
            }
            for kind, emitted_result in emitted.items():
                self.assertEqual(emitted_result.returncode, 0, emitted_result.stderr)
                artifact_path = project / f"{kind}.json"
                artifact_path.write_text(emitted_result.stdout, encoding="utf-8")
                validation = self.run_cli("validate", "--kind", kind, str(artifact_path), "--format", "json")
                self.assertEqual(validation.returncode, 0, validation.stderr)

            mcp_scan = self._run_mcp_requests([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "scan", "arguments": {"project": "."}}},
            ], cwd=project)
            mcp_scan_result = mcp_scan[2]["result"]
            self.assertFalse(mcp_scan_result["isError"])
            self.assertEqual(mcp_scan_result["structuredContent"]["schema"], "checkyourself-scan/1")
            mcp_scan_data = mcp_scan_result["structuredContent"]

            mcp_pipeline = self._run_mcp_requests([
                {"jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
                {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
                    "name": "score", "arguments": {"findings": mcp_scan_data},
                }},
                {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
                    "name": "validate", "arguments": {"kind": "scan", "artifact": mcp_scan_data},
                }},
            ], cwd=project)
            mcp_score = mcp_pipeline[4]["result"]
            self.assertFalse(mcp_score["isError"])
            self.assertEqual(mcp_score["structuredContent"]["schema"], "checkyourself-score/1")
            mcp_validate = mcp_pipeline[5]["result"]
            self.assertTrue(mcp_validate["structuredContent"]["valid"])

    def test_report_requires_every_documented_section(self) -> None:
        for section in REPORT_REQUIRED_SECTIONS:
            with self.subTest(section=section):
                artifact = deepcopy(GOLDEN_REPORT)
                artifact.pop(section)
                with tempfile.TemporaryDirectory() as tmp:
                    artifact_path = Path(tmp) / "report.json"
                    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
                    cli_result = self.run_cli("validate", "--kind", "report", str(artifact_path), "--format", "json")
                self.assertEqual(cli_result.returncode, 1, cli_result.stderr)
                validation = json.loads(cli_result.stdout)
                self.assertFalse(validation["valid"])
                self.assertTrue(any(section in error for error in validation["errors"]))

    def test_semantic_report_validation_rejects_tampered_verdict(self) -> None:
        artifact = deepcopy(GOLDEN_REPORT)
        artifact.update({
            "score": 100,
            "confidence": "high",
            "score_caps": [],
            "findings": [{
                "id": "F-OPEN-P0", "severity": "P0", "category": "C1",
                "finding": "Cross-user access remains possible",
                "plain_english_risk": "A user may read another user's records.",
                "evidence": ["auth.md:1"], "status": "open",
            }],
        })
        artifact["remediation_backlog"] = [{
            "finding_id": "F-OPEN-P0", "severity": "P0",
            "fix_summary": "Prove tenant isolation.", "status": "open",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered-report.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            result = self.run_cli("validate", "--kind", "report", str(path), "--format", "json")
        self.assertEqual(result.returncode, 1, result.stderr)
        validation = json.loads(result.stdout)
        self.assertTrue(validation["schema_valid"])
        self.assertFalse(validation["semantic_valid"])
        self.assertFalse(validation["valid"])
        self.assertTrue(any("P0 cap" in error for error in validation["semantic_errors"]))

    def test_score_claim_records_explicit_and_unbound_evidence(self) -> None:
        coverage = self._full_coverage()
        coverage["surfaces"][5]["claim_bound_evidence"] = ["src/app.py:6"]
        with tempfile.TemporaryDirectory() as tmp:
            findings_path = Path(tmp) / "findings.json"
            coverage_path = Path(tmp) / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--claim", "The export returns only the requester's records",
                "--no-history", "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertEqual(score["claim"], "The export returns only the requester's records")
        c1 = next(category for category in score["per_category"] if category["id"] == "C1")
        bindings = {item["evidence"]: item["claim_bound"] for item in c1["claim_binding"]}
        self.assertTrue(bindings["src/app.py:6"])
        self.assertTrue(any(not bound for bound in bindings.values()))

    def _full_coverage(self) -> dict:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)
        return {
            "schema": cy.COVERAGE_SCHEMA_ID,
            "surfaces": [
                {
                    "id": sid,
                    "surface": surface,
                    "category": category,
                    "status": "Pass",
                    "evidence_reviewed": [f"src/app.py:{index}"],
                }
                for index, (sid, surface, category) in enumerate(cy.COVERAGE_SURFACES, start=1)
            ],
        }

    def _verification_artifact(self, root: Path, surface_id: str, *, suffix: str = "proof") -> Path:
        path = root / "coverage" / "verification" / surface_id / f"{suffix}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "kind": "surface-verification-record",
            "surface_id": surface_id,
            "source_revision": "fixture-revision",
            "command": f"verify {surface_id}",
            "result": "verified",
        }) + "\n", encoding="utf-8")
        return path

    def _receipt(self, path: Path, root: Path, origin: str, source_state: str, result: str, *, surface_id: str, claim: str = "fixture claim") -> dict:
        receipt = {
            "reference": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "subject_digest": hashlib.sha256(path.read_bytes()).hexdigest(),
            "surface_id": surface_id,
            "source_revision": "fixture-revision",
            "command": "fixture verifier command",
            "claim": claim,
            "origin": "checkyourself verifier receipt command",
            "source_state": source_state,
            "result": result,
            "issuer": "checkyourself-verifier/1",
            "issued_at": "2026-09-05T00:00:00Z",
        }
        binding = {field: receipt.get(field) for field in (
            "reference", "sha256", "subject_digest", "surface_id", "source_revision", "command", "claim",
            "origin", "source_state", "result", "issuer", "issued_at",
        )}
        receipt["receipt_sha256"] = hashlib.sha256(
            json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return receipt

    def _run_mcp_score(self, coverage: object) -> dict:
        messages = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                "name": "score", "arguments": {"findings": {"findings": []}, "coverage": coverage},
            }}),
            "",
        ])
        result = subprocess.run(
            [sys.executable, str(CLI), "mcp"],
            text=True,
            input=messages,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = {json.loads(line)["id"]: json.loads(line) for line in result.stdout.splitlines()}
        return responses[2]

    def test_score_rejects_invalid_coverage_in_cli_and_mcp(self) -> None:
        base = self._full_coverage()
        cases = {}

        invalid = deepcopy(base)
        invalid["surfaces"][2]["status"] = "Bogus"
        cases["invalid status"] = invalid

        null_status = deepcopy(base)
        null_status["surfaces"][2]["status"] = None
        cases["null status"] = null_status
        cases["null artifact"] = None

        duplicate = deepcopy(base)
        duplicate["surfaces"].append(deepcopy(duplicate["surfaces"][0]))
        cases["duplicate id"] = duplicate

        unknown_id = deepcopy(base)
        unknown_id["surfaces"][2]["id"] = "S99"
        cases["unknown id"] = unknown_id

        mismatched_category = deepcopy(base)
        mismatched_category["surfaces"][2]["category"] = "C2"
        cases["mismatched category"] = mismatched_category

        missing_surface = deepcopy(base)
        del missing_surface["surfaces"][2]["surface"]
        cases["missing canonical surface"] = missing_surface

        structural_drift = deepcopy(base)
        structural_drift["surfaces"].append({
            "id": "S99",
            "surface": "Untracked surface",
            "category": "C1",
            "status": "Pass",
            "evidence_reviewed": ["src/app.py:99"],
        })
        cases["unknown structural row"] = structural_drift

        for label, coverage in cases.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    findings_path = Path(tmp) / "findings.json"
                    coverage_path = Path(tmp) / "coverage.json"
                    findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
                    coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
                    cli_result = self.run_cli(
                        "score", "--findings", str(findings_path),
                        "--coverage", str(coverage_path), "--no-history", "--format", "json",
                    )
                self.assertEqual(cli_result.returncode, 2, cli_result.stderr)
                error = json.loads(cli_result.stdout)
                self.assertEqual(error["code"], 2)
                self.assertIn("fill coverage.json with evidence, then re-run score", error["error"])
                self.assertIn("invalid coverage artifact", cli_result.stderr)

                mcp_response = self._run_mcp_score(coverage)
                mcp_result = mcp_response["result"]
                self.assertTrue(mcp_result["isError"])
                self.assertNotIn("score", mcp_result["structuredContent"])
                self.assertNotIn("confidence", mcp_result["structuredContent"])

    def test_caller_issued_full_evidence_cannot_reach_high_confidence(self) -> None:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)
        surfaces = []
        with tempfile.TemporaryDirectory() as tmp:
            findings_path = Path(tmp) / "findings.json"
            coverage_path = Path(tmp) / "coverage.json"
            for index, (sid, surface, category) in enumerate(cy.COVERAGE_SURFACES, start=1):
                evidence = self._verification_artifact(Path(tmp), sid, suffix=f"receipt-{index}")
                surfaces.append({
                    "id": sid, "surface": surface, "category": category,
                    "status": "Pass", "evidence_reviewed": [evidence.relative_to(Path(tmp)).as_posix()],
                    "evidence_receipts": [self._receipt(evidence, Path(tmp), "fixture verifier", "temporary test tree", "non-empty artifact observed", surface_id=sid)],
                })
            coverage = {"schema": "checkyourself-coverage/1", "surfaces": surfaces}
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path),
                "--coverage", str(coverage_path), "--no-history", "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertFalse(score["coverage_complete"])
        self.assertEqual(score["confidence"], "low")
        self.assertLess(score["score"], 100)

    def test_verifier_receipt_command_emits_surface_bound_binding_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            evidence = self._verification_artifact(project, "S11", suffix="pytest")
            receipt_path = project / "receipt.json"
            result = self.run_cli(
                "receipt",
                "--root", str(project),
                "--reference", evidence.relative_to(project).as_posix(),
                "--surface-id", "S11",
                "--source-revision", "abc123",
                "--source-state", "temporary test tree",
                "--command", "pytest tests/test_app.py -q",
                "--claim", "The focused quality gate passes",
                "--result", "1 passed",
                "--out", str(receipt_path),
                "--format", "json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["issuer"], "checkyourself-verifier/1")
            self.assertEqual(receipt["surface_id"], "S11")
            self.assertEqual(receipt["reference"], "coverage/verification/S11/pytest.json")
            self.assertEqual(self.run_cli("validate", "--kind", "receipt", str(receipt_path)).returncode, 0)
            tampered_path = project / "tampered-receipt.json"
            tampered = deepcopy(receipt)
            tampered["result"] = "2 passed"
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            tampered_result = self.run_cli("validate", "--kind", "receipt", str(tampered_path), "--format", "json")
            self.assertEqual(tampered_result.returncode, 1)
            self.assertIn("does not cover", json.loads(tampered_result.stdout)["semantic_errors"][0])

    def test_receipt_subject_digest_must_match_registered_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            evidence = self._verification_artifact(project, "S11", suffix="pytest")
            result = self.run_cli(
                "receipt",
                "--root", str(project),
                "--reference", evidence.relative_to(project).as_posix(),
                "--surface-id", "S11",
                "--source-revision", "abc123",
                "--source-state", "temporary test tree",
                "--command", "pytest tests/test_app.py -q",
                "--claim", "The focused quality gate passes",
                "--result", "1 passed",
                "--subject-digest", "0" * 64,
                "--format", "json",
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("subject_digest must match", result.stderr)

    def test_explicit_registry_override_changes_path_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            evidence = project / "custom" / "S11" / "pytest-proof.json"
            evidence.parent.mkdir(parents=True)
            evidence.write_text(json.dumps({
                "kind": "surface-verification-record",
                "surface_id": "S11",
                "source_revision": "abc123",
                "command": "pytest tests/test_app.py -q",
                "result": "1 passed",
            }) + "\n", encoding="utf-8")
            (project / ".checkyourself.json").write_text(json.dumps({
                "verification_artifact_registry": {
                    "S11": {
                        "path_roots": ["custom/S11"],
                        "path_patterns": ["pytest-*.json"],
                    }
                }
            }), encoding="utf-8")
            result = self.run_cli(
                "receipt", "--root", str(project),
                "--reference", evidence.relative_to(project).as_posix(),
                "--surface-id", "S11", "--source-revision", "abc123",
                "--source-state", "temporary test tree",
                "--command", "pytest tests/test_app.py -q",
                "--claim", "The focused quality gate passes", "--result", "1 passed",
                "--format", "json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            wrong_shape = project / "custom" / "S11" / "pytest-wrong.json"
            wrong_shape.write_text(json.dumps({"surface_id": "S11"}), encoding="utf-8")
            rejected = self.run_cli(
                "receipt", "--root", str(project),
                "--reference", wrong_shape.relative_to(project).as_posix(),
                "--surface-id", "S11", "--source-revision", "abc123",
                "--source-state", "temporary test tree",
                "--command", "pytest tests/test_app.py -q",
                "--claim", "The focused quality gate passes", "--result", "1 passed",
                "--format", "json",
            )
        self.assertEqual(rejected.returncode, 2, rejected.stderr)
        self.assertIn("expected", rejected.stderr)

    def test_distinct_unregistered_artifacts_fail_closed_for_issuance_and_score(self) -> None:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)
        coverage = self._full_coverage()
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for row in coverage["surfaces"]:
                evidence = project / f"irrelevant-{row['id']}.md"
                evidence.write_text(f"Existing but unregistered artifact for {row['id']}.\n", encoding="utf-8")
                reference = evidence.relative_to(project).as_posix()
                row["evidence_reviewed"] = [reference]
                row["evidence_receipts"] = [self._receipt(
                    evidence,
                    project,
                    "fixture verifier",
                    "temporary test tree",
                    "verified",
                    surface_id=row["id"],
                )]
                with self.assertRaisesRegex(cy.CliError, "not a registered verification artifact"):
                    cy.issue_receipt(
                        reference,
                        project,
                        surface_id=row["id"],
                        source_revision="fixture-revision",
                        source_state="temporary test tree",
                        command=f"verify {row['id']}",
                        claim=f"The {row['id']} verification passes",
                        result="verified",
                    )
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertLessEqual(score["score"], 84)
        self.assertNotEqual(score["confidence"], "high")
        self.assertIn(84, [cap["cap"] for cap in score["caps_applied"]])

    def test_distinct_unregistered_delegation_artifacts_fail_closed(self) -> None:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)
        coverage = self._full_coverage()
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for row in coverage["surfaces"]:
                evidence = project / f"delegation-{row['id']}.md"
                evidence.write_text(f"Existing but unregistered delegation artifact for {row['id']}.\n", encoding="utf-8")
                reference = evidence.relative_to(project).as_posix()
                row.update(
                    status="NotApplicable",
                    evidence_reviewed=[],
                    not_applicable_reason="Responsibility is delegated.",
                    delegation_receipts=[self._receipt(
                        evidence, project, "fixture delegation", "temporary test tree",
                        "delegated", surface_id=row["id"], claim="Delegation is documented",
                    )],
                )
                with self.assertRaisesRegex(cy.CliError, "not a registered verification artifact"):
                    cy.issue_receipt(
                        reference,
                        project,
                        surface_id=row["id"],
                        source_revision="fixture-revision",
                        source_state="temporary test tree",
                        command=f"delegate {row['id']}",
                        claim="Delegation is documented",
                        result="delegated",
                    )
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertLessEqual(score["score"], 84)
        self.assertNotEqual(score["confidence"], "high")
        self.assertIn(84, [cap["cap"] for cap in score["caps_applied"]])

    def test_rebound_receipt_with_rehashed_binding_fails_closed(self) -> None:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)
        coverage = self._full_coverage()
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            receipts = {}
            for row in coverage["surfaces"]:
                evidence = self._verification_artifact(project, row["id"])
                row["evidence_reviewed"] = [evidence.relative_to(project).as_posix()]
                receipts[row["id"]] = cy.issue_receipt(
                    evidence.relative_to(project).as_posix(),
                    project,
                    surface_id=row["id"],
                    source_revision="fixture-revision",
                    source_state="temporary test tree",
                    command=f"verify {row['id']}",
                    claim=f"The {row['id']} verification passes",
                    result="verified",
                )
                row["evidence_receipts"] = [receipts[row["id"]]]

            rebound = deepcopy(receipts["S01"])
            rebound["surface_id"] = "S02"
            rebound["receipt_sha256"] = cy._receipt_binding_digest(rebound)
            s02 = next(row for row in coverage["surfaces"] if row["id"] == "S02")
            s02["evidence_reviewed"] = ["coverage/verification/S01/proof.json"]
            s02["evidence_receipts"] = [rebound]
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertLessEqual(score["score"], 84)
        self.assertNotEqual(score["confidence"], "high")
        self.assertIn(84, [cap["cap"] for cap in score["caps_applied"]])

    def test_irrelevant_caller_receipt_reuse_cannot_earn_high_score(self) -> None:
        for status in ("Pass", "NotApplicable"):
            with self.subTest(status=status):
                coverage = self._full_coverage()
                with tempfile.TemporaryDirectory() as tmp:
                    project = Path(tmp)
                    evidence = project / "README.md"
                    evidence.write_text("This file is authentic but irrelevant to every surface.\n", encoding="utf-8")
                    caller_receipt = {
                        "reference": evidence.name,
                        "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                        "origin": "caller-authored",
                        "source_state": "caller claim",
                        "result": "pass",
                    }
                    for row in coverage["surfaces"]:
                        row["status"] = status
                        row["evidence_reviewed"] = [] if status == "NotApplicable" else [evidence.name]
                        row["evidence_receipts"] = []
                        row["delegation_receipts"] = [caller_receipt] if status == "NotApplicable" else []
                        if status == "NotApplicable":
                            row["not_applicable_reason"] = "Delegated to the caller."
                        else:
                            row["evidence_receipts"] = [caller_receipt]
                    findings_path = project / "findings.json"
                    coverage_path = project / "coverage.json"
                    findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
                    coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
                    result = self.run_cli(
                        "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                        "--no-history", "--format", "json",
                    )
                self.assertEqual(result.returncode, 0, result.stderr)
                score = json.loads(result.stdout)
                self.assertEqual(score["score"], 29)
                self.assertNotEqual(score["confidence"], "high")
                self.assertLessEqual(score["score"], 84)
                self.assertIn(84, [cap["cap"] for cap in score["caps_applied"]])
                self.assertTrue(score["manual_evidence_needed"])

    def test_finding_linked_only_to_fixed_finding_is_independently_blocked(self) -> None:
        coverage = self._full_coverage()
        findings = {
            "findings": [{
                "id": "F-FIXED-ISOLATION", "severity": "P0", "category": "C1",
                "finding": "Prior isolation issue is fixed", "status": "fixed",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for row in coverage["surfaces"]:
                evidence = self._verification_artifact(project, row["id"])
                row["evidence_reviewed"] = [evidence.relative_to(project).as_posix()]
                row["evidence_receipts"] = [self._receipt(
                    evidence, project, "fixture verifier", "temporary test tree",
                    "non-empty artifact observed", surface_id=row["id"],
                )]
            s07 = next(row for row in coverage["surfaces"] if row["id"] == "S07")
            s07.update(status="Finding", finding_ids=["F-FIXED-ISOLATION"])
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps(findings), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertLess(score["score"], 84)
        self.assertIn("CY-COVERAGE-S07", score["findings_scored"])
        self.assertNotEqual(score["confidence"], "high")
        self.assertLessEqual(score["score"], 84)
        self.assertIn(84, [cap["cap"] for cap in score["caps_applied"]])
        self.assertIn("CY-COVERAGE-S07", score["findings_scored"])
        c1 = next(category for category in score["per_category"] if category["id"] == "C1")
        self.assertTrue(any("no linked unresolved finding" in item for item in c1["missing_evidence"]))

    def test_fabricated_evidence_references_cannot_earn_pass_credit(self) -> None:
        coverage = self._full_coverage()
        with tempfile.TemporaryDirectory() as tmp:
            findings_path = Path(tmp) / "findings.json"
            coverage_path = Path(tmp) / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertEqual(score["confidence"], "low")
        self.assertLess(score["score"], 100)
        c1 = next(category for category in score["per_category"] if category["id"] == "C1")
        self.assertTrue(c1["missing_evidence"])

    def test_accepted_p0_retains_residual_risk_penalty_and_cap(self) -> None:
        findings = {
            "findings": [{
                "id": "F-ACCEPTED-P0", "severity": "P0", "category": "C1",
                "finding": "Cross-user access remains possible", "status": "accepted-risk",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "findings.json"
            path.write_text(json.dumps(findings), encoding="utf-8")
            result = self.run_cli("score", "--findings", str(path), "--no-history", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertEqual(score["counts"]["P0"], 1)
        self.assertIn(49, [cap["cap"] for cap in score["caps_applied"]])
        self.assertLessEqual(score["score"], 49)
        self.assertEqual(score["workflow_dispositions"], [{
            "finding_id": "F-ACCEPTED-P0", "status": "accepted-risk", "residual_risk": "open",
        }])

    def test_unknown_evidence_survives_finding_category_override(self) -> None:
        coverage = self._full_coverage()
        s06 = next(item for item in coverage["surfaces"] if item["id"] == "S06")
        s06.update(status="Unknown", evidence_reviewed=[], missing_evidence=["restore receipt"])
        s07 = next(item for item in coverage["surfaces"] if item["id"] == "S07")
        s07.update(status="Finding", evidence_reviewed=["fixture.md:1"], finding_ids=["F-ISOLATION"])
        findings = {"findings": [{
            "id": "F-ISOLATION", "severity": "P3", "category": "C1",
            "finding": "Isolation evidence is incomplete", "status": "open",
        }]}
        with tempfile.TemporaryDirectory() as tmp:
            findings_path = Path(tmp) / "findings.json"
            coverage_path = Path(tmp) / "coverage.json"
            findings_path.write_text(json.dumps(findings), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            result = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertEqual(score["confidence"], "low")
        self.assertIn(84, [cap["cap"] for cap in score["caps_applied"]])
        self.assertLess(score["score"], 100)

    def test_diff_detects_regression_and_gates_in_ci(self) -> None:
        old = {"findings": [{"id": "CY-TEST-001", "severity": "P1", "category": "C5", "finding": "No tests", "status": "open"}]}
        new = {"findings": [
            {"id": "CY-TEST-001", "severity": "P1", "category": "C5", "finding": "No tests", "status": "open"},
            {"id": "CY-SECRET-001", "severity": "P0", "category": "C3", "finding": "Secret", "status": "open"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            old_path = Path(tmp) / "old.json"
            new_path = Path(tmp) / "new.json"
            old_path.write_text(json.dumps(old), encoding="utf-8")
            new_path.write_text(json.dumps(new), encoding="utf-8")
            json_result = self.run_cli("diff", "--old", str(old_path), "--new", str(new_path), "--format", "json")
            ci_result = self.run_cli("diff", "--old", str(old_path), "--new", str(new_path), "--ci")
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        diff = json.loads(json_result.stdout)
        self.assertEqual([f["id"] for f in diff["added"]], ["CY-SECRET-001"])
        self.assertTrue(diff["regression"])
        self.assertEqual(ci_result.returncode, 1)

    def test_diff_gates_equal_count_p1_replacement(self) -> None:
        old = {"findings": [{"id": "CY-OLD-001", "severity": "P1", "category": "C5", "finding": "Old risk", "status": "open"}]}
        new = {"findings": [{"id": "CY-NEW-001", "severity": "P1", "category": "C5", "finding": "New risk", "status": "open"}]}
        with tempfile.TemporaryDirectory() as tmp:
            old_path = Path(tmp) / "old.json"
            new_path = Path(tmp) / "new.json"
            old_path.write_text(json.dumps(old), encoding="utf-8")
            new_path.write_text(json.dumps(new), encoding="utf-8")
            result = self.run_cli("diff", "--old", str(old_path), "--new", str(new_path), "--format", "json")
            ci_result = self.run_cli("diff", "--old", str(old_path), "--new", str(new_path), "--ci")

        self.assertEqual(result.returncode, 0, result.stderr)
        diff = json.loads(result.stdout)
        self.assertEqual(diff["old_counts"], diff["new_counts"])
        self.assertTrue(diff["regression"])
        self.assertEqual(diff["regressions"], [{"id": "CY-NEW-001", "type": "newly_open", "severity": "P1"}])
        self.assertEqual(ci_result.returncode, 1)

    def test_diff_reports_status_only_resolution(self) -> None:
        old = {"findings": [{"id": "CY-TEST-001", "severity": "P1", "category": "C5", "finding": "No tests", "status": "open"}]}
        new = {"findings": [{"id": "CY-TEST-001", "severity": "P1", "category": "C5", "finding": "No tests", "status": "fixed"}]}
        with tempfile.TemporaryDirectory() as tmp:
            old_path = Path(tmp) / "old.json"
            new_path = Path(tmp) / "new.json"
            old_path.write_text(json.dumps(old), encoding="utf-8")
            new_path.write_text(json.dumps(new), encoding="utf-8")
            result = self.run_cli("diff", "--old", str(old_path), "--new", str(new_path), "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        diff = json.loads(result.stdout)
        self.assertEqual([finding["id"] for finding in diff["resolved"]], ["CY-TEST-001"])
        self.assertEqual(diff["resolved"][0]["status"], "fixed")
        self.assertEqual(diff["status_changes"], [{"id": "CY-TEST-001", "old_status": "open", "new_status": "fixed"}])
        self.assertEqual(diff["unchanged"], [])
        self.assertFalse(diff["regression"])

    def test_diff_gates_reopened_and_escalated_high_risk(self) -> None:
        old = {"findings": [{"id": "CY-RISK-001", "severity": "P2", "category": "C5", "finding": "Risk", "status": "fixed"}]}
        new = {"findings": [{"id": "CY-RISK-001", "severity": "P1", "category": "C5", "finding": "Risk", "status": "open"}]}
        with tempfile.TemporaryDirectory() as tmp:
            old_path = Path(tmp) / "old.json"
            new_path = Path(tmp) / "new.json"
            old_path.write_text(json.dumps(old), encoding="utf-8")
            new_path.write_text(json.dumps(new), encoding="utf-8")
            result = self.run_cli("diff", "--old", str(old_path), "--new", str(new_path), "--ci")

        self.assertEqual(result.returncode, 1)
        self.assertIn("[reopened] CY-RISK-001", result.stdout)
        self.assertIn("[severity_escalated] CY-RISK-001", result.stdout)

    def test_batch_output_names_highest_severity_slice(self) -> None:
        findings = {
            "findings": [
                {"id": "F-002", "severity": "P2", "category": "C6", "finding": "No CI", "status": "open"},
                {"id": "F-001", "severity": "P1", "category": "C5", "finding": "No tests", "status": "open"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "findings.json"
            path.write_text(json.dumps(findings), encoding="utf-8")
            result = self.run_cli("backlog", "--findings", str(path), "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        backlog = json.loads(result.stdout)
        self.assertEqual(backlog["highest_severity_batch"], ["F-001"])
        self.assertEqual(backlog["first_approval_batch"], backlog["highest_severity_batch"])
        self.assertEqual(backlog["batch_basis"]["name"], "highest_severity_batch")
        self.assertEqual(backlog["batch_basis"]["safety_analysis"], "not performed")

    def test_mcp_rejects_unknown_arguments_and_unknown_tools(self) -> None:
        messages = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "scan", "arguments": {"path": "/etc"}}}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "does_not_exist", "arguments": {}}}),
            "",
        ])
        result = subprocess.run(
            [sys.executable, str(CLI), "mcp"],
            text=True, input=messages, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = {json.loads(line)["id"]: json.loads(line) for line in result.stdout.splitlines()}
        self.assertIn("error", responses[2])
        self.assertEqual(responses[2]["error"]["code"], -32602)
        self.assertIn("error", responses[3])
        self.assertIn("unknown tool", responses[3]["error"]["message"])

    def test_mcp_rejects_wrong_argument_types_and_bounds(self) -> None:
        messages = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "scan", "arguments": {"deep": "false"}}}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "scan", "arguments": {"max_files": 0}}}),
            "",
        ])
        result = subprocess.run(
            [sys.executable, str(CLI), "mcp"],
            text=True, input=messages, capture_output=True, check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        responses = {json.loads(line)["id"]: json.loads(line) for line in result.stdout.splitlines()}
        self.assertEqual(responses[2]["error"]["code"], -32602)
        self.assertIn("expected", responses[2]["error"]["message"])
        self.assertEqual(responses[3]["error"]["code"], -32602)
        self.assertIn("minimum", responses[3]["error"]["message"])

    def test_top_level_help_lists_every_shipped_subcommand(self) -> None:
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        for command in (
            "describe", "scan", "diagnostic", "schema", "coverage", "score",
            "backlog", "next", "diff", "validate", "init", "mcp",
        ):
            self.assertIn(command, result.stdout)
        self.assertNotIn("Project root to scan", result.stdout)

    def test_mcp_scan_is_confined_to_scan_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            messages = "\n".join([
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "scan", "arguments": {"project": "/etc"}}}),
                "",
            ])
            result = subprocess.run(
                [sys.executable, str(CLI), "mcp"],
                text=True, input=messages, capture_output=True, check=False,
                cwd=tmp, env={**__import__("os").environ, "CHECKYOURSELF_SCAN_ROOT": tmp},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = {json.loads(line)["id"]: json.loads(line) for line in result.stdout.splitlines()}
        call = responses[2]["result"]
        self.assertTrue(call["isError"])
        self.assertIn("outside the allowed scan root", call["structuredContent"]["error"])

    def test_unknown_command_suggests_closest_match(self) -> None:
        result = self.run_cli("scna", ".")
        self.assertEqual(result.returncode, 2)
        self.assertIn("scan", result.stderr)

    def test_stdin_score_does_not_write_history_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(CLI), "score", "--findings", "-", "--format", "json"],
                text=True, input=json.dumps({"findings": []}), capture_output=True, check=False, cwd=tmp,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((Path(tmp) / ".checkyourself-score-history.json").exists())

    def test_corrupt_score_history_is_preserved_not_destroyed(self) -> None:
        for corrupted in ("{ this is not valid json", "null", '{"wrong": "shape"}'):
            with self.subTest(corrupted=corrupted):
                with tempfile.TemporaryDirectory() as tmp:
                    project = Path(tmp)
                    findings_path = project / "findings.json"
                    findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
                    history_path = project / "history.json"
                    history_path.write_text(corrupted, encoding="utf-8")
                    result = self.run_cli("score", "--findings", str(findings_path), "--history", str(history_path), "--format", "json")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue((project / "history.json.corrupt.bak").exists())
                    history = json.loads(history_path.read_text(encoding="utf-8"))
                    self.assertEqual(len(history), 1)

    def test_validate_public_handles_non_dict_dashboard_sample(self) -> None:
        validator = ROOT / "tools" / "validate_public.py"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "samples").mkdir()
            (project / "samples" / "sample-dashboard-data.json").write_text("[]", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(validator), str(project)],
                text=True, capture_output=True, check=False,
            )
        # Must not crash with a traceback; a clean failure message is fine.
        self.assertNotIn("Traceback", result.stderr)

    def test_diff_artifact_validates_against_schema(self) -> None:
        old = {"findings": []}
        new = {"findings": [{"id": "CY-CI-001", "severity": "P2", "category": "C6", "finding": "No CI", "status": "open"}]}
        with tempfile.TemporaryDirectory() as tmp:
            old_path = Path(tmp) / "old.json"
            new_path = Path(tmp) / "new.json"
            diff_path = Path(tmp) / "diff.json"
            old_path.write_text(json.dumps(old), encoding="utf-8")
            new_path.write_text(json.dumps(new), encoding="utf-8")
            diff_result = self.run_cli("diff", "--old", str(old_path), "--new", str(new_path), "--format", "json")
            self.assertEqual(diff_result.returncode, 0, diff_result.stderr)
            diff_path.write_text(diff_result.stdout, encoding="utf-8")
            validate = self.run_cli("validate", "--kind", "diff", str(diff_path))
            self.assertEqual(validate.returncode, 0, validate.stderr)

    def test_stable_rule_id_triple_for_secret_tests_and_ci(self) -> None:
        # The exact ID-and-severity contract: a credential shape is always
        # CY-SECRET-001 (P0), missing tests CY-TEST-001 (P1), missing CI
        # CY-CI-001 (P2), and findings sort deterministically by severity.
        token = "sk-" + ("z" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text(f'API_KEY = "{token}"\n', encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(
            [(f["id"], f["severity"]) for f in data["findings"]],
            [("CY-SECRET-001", "P0"), ("CY-TEST-001", "P1"), ("CY-CI-001", "P2")],
        )

    def test_identifier_continuations_are_not_secret_names(self) -> None:
        # `tokenizer` and `passwordResetUrlPath` continue past the credential
        # token, so neither may produce a secret finding of any confidence.
        # Built by concatenation so the committed test source never pairs a
        # credential keyword with an assignment (keeps gitleaks clean).
        continuation_field = "password" + "ResetUrlPath"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text(
                "\n".join([
                    'tokenizer = "abcdefghijklmnopqrstuvwxyz123456"',
                    f'{continuation_field} = "reset/abcdefghijklmnop"',
                    "",
                ]),
                encoding="utf-8",
            )
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        ids = {f["id"] for f in json.loads(result.stdout)["findings"]}
        self.assertNotIn("CY-SECRET-001", ids)
        self.assertNotIn("CY-SECRET-002", ids)

    def test_scan_ci_flag_exits_nonzero_only_on_p0(self) -> None:
        token = "sk-" + ("w" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text(f'API_KEY = "{token}"\n', encoding="utf-8")
            gated = self.run_cli("scan", str(project), "--ci", "--no-write", "--quiet")
            (project / "app.py").write_text("print('ok')\n", encoding="utf-8")
            clean = self.run_cli("scan", str(project), "--ci", "--no-write", "--quiet")

        self.assertEqual(gated.returncode, 1, gated.stderr)
        self.assertEqual(clean.returncode, 0, clean.stderr)

    def test_scan_refuses_to_write_context_through_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text("print('ok')\n", encoding="utf-8")
            target = Path(outside) / "target.md"
            target.write_text("", encoding="utf-8")
            out_link = project / "context.md"
            out_link.symlink_to(target)
            result = self.run_cli("scan", str(project), "--out", str(out_link), "--quiet")

        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to write through symlink", result.stderr)

    def test_scan_refuses_to_write_through_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text("print('ok')\n", encoding="utf-8")
            target_dir = Path(outside) / "output"
            target_dir.mkdir()
            parent_link = project / "generated"
            parent_link.symlink_to(target_dir, target_is_directory=True)
            result = self.run_cli("scan", str(project), "--out", str(parent_link / "context.md"), "--quiet")

        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to write through symlink", result.stderr)

    def test_risk_path_hints_match_segments_not_substrings(self) -> None:
        # `rapid/` must not register as an API surface and `user-agent.ts`
        # must not register as an AI-agent surface.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for folder, name in (("rapid", "notes.ts"), ("src", "user-agent.ts"), ("api", "route.ts")):
                (project / folder).mkdir()
                (project / folder / name).write_text("export const x = 1;\n", encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")

        self.assertEqual(result.returncode, 0, result.stderr)
        surfaces = json.loads(result.stdout)["risk_surfaces"]
        self.assertEqual(surfaces.get("API routes or handlers"), ["api/route.ts"])
        self.assertNotIn("AI agents", surfaces)

    def test_unknown_category_labels_are_normalized_for_scoring(self) -> None:
        # A label like "security" is not a scoring category; it must be
        # re-inferred (here to C3) instead of silently escaping penalties.
        findings = {
            "findings": [{
                "id": "F-001",
                "severity": "P1",
                "category": "security",
                "finding": "Hardcoded secret in source",
                "status": "open",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "findings.json"
            path.write_text(json.dumps(findings), encoding="utf-8")
            result = self.run_cli("score", "--findings", str(path), "--no-history", "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        c3 = next(cat for cat in score["per_category"] if cat["id"] == "C3")
        self.assertIn("F-001", [p.get("finding_id") for p in c3["penalties"]])

    def _write_challenges(self, project: Path, definitions: dict) -> None:
        path = project / ".checkyourself" / "challenges.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema": "checkyourself-challenges/1",
            "challenges": definitions,
        }), encoding="utf-8")

    def _score_challenge_receipt(self, project: Path, receipt: dict) -> dict:
        coverage = {
            "schema": "checkyourself-coverage/1",
            "surfaces": [{
                "id": "S11",
                "surface": "Tests, quality gates, and regression coverage",
                "category": "C5",
                "status": "Pass",
                "evidence_reviewed": [receipt["captured_output"]],
                "evidence_receipts": [receipt],
            }],
        }
        findings_path = project / "findings.json"
        coverage_path = project / "coverage.json"
        findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
        coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
        score = self.run_cli(
            "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
            "--no-history", "--format", "json",
        )
        self.assertEqual(score.returncode, 0, score.stderr)
        return json.loads(score.stdout)

    def test_true_command_challenge_is_rejected_before_credit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S11": {
                    "command": ["true"],
                    "timeout_s": 10,
                    "success": {"exit_zero": True},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 1)
            result = json.loads(challenge.stdout)
            self.assertEqual(result["surfaces"][0]["status"], "FAIL")
            self.assertTrue(any("vacuous" in reason for reason in result["surfaces"][0]["reasons"]))
            score = self._score_challenge_receipt(project, result["receipts"][0])
            self.assertNotEqual(score["confidence"], "high")
            self.assertLess(score["score"], 100)

    def test_echo_only_output_is_rejected_even_with_a_positive_assertion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S11": {
                    "command": ["echo", "one two three"],
                    "timeout_s": 10,
                    "success": {"exit_zero": True, "regex_match": "one"},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 1)
            result = json.loads(challenge.stdout)
            self.assertTrue(any("vacuous" in reason for reason in result["surfaces"][0]["reasons"]))

    def test_trivially_matching_regex_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S11": {
                    "command": [sys.executable, "-c", "import pytest; print('1 passed in 0.01s')"],
                    "timeout_s": 10,
                    "success": {"exit_zero": True, "regex_match": ".*"},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 1)
            result = json.loads(challenge.stdout)
            self.assertTrue(any("vacuous" in reason for reason in result["surfaces"][0]["reasons"]))

    def test_build_surface_requires_a_non_empty_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S13": {
                    "command": [sys.executable, "-c", "import sys; sys.stdout.write('release status ready checks 1\\n')"],
                    "timeout_s": 10,
                    "success": {"exit_zero": True, "regex_match": "release\\s+status\\s+ready", "artifact": "build/release.json"},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S13", "--format", "json")
            self.assertEqual(challenge.returncode, 1)
            result = json.loads(challenge.stdout)
            self.assertTrue(any("required artifact" in reason for reason in result["surfaces"][0]["reasons"]))

    def test_build_surface_accepts_a_non_empty_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S13": {
                    "command": [sys.executable, "-c", "from pathlib import Path; Path('build').mkdir(); Path('build/release.json').write_text('release'); import sys; sys.stdout.write('release status ready checks 1\\n')"],
                    "timeout_s": 10,
                    "success": {"exit_zero": True, "regex_match": "release\\s+status\\s+ready", "artifact": "build/release.json"},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S13", "--format", "json")
            self.assertEqual(challenge.returncode, 0, challenge.stderr)
            self.assertEqual(json.loads(challenge.stdout)["surfaces"][0]["status"], "PASS")

    def test_analysis_surface_requires_structured_findings_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S19": {
                    "command": [sys.executable, "-c", "import json; print(json.dumps({'status': 'pass'}))"],
                    "timeout_s": 10,
                    "success": {"json_field": {"status": "pass"}},
                    "output_kind": "json",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S19", "--format", "json")
            self.assertEqual(challenge.returncode, 1)
            result = json.loads(challenge.stdout)
            self.assertTrue(any("structured fields" in reason for reason in result["surfaces"][0]["reasons"]))

    def test_executed_challenge_receipt_is_the_only_full_credit_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "test_challenge.py").write_text("def test_challenge():\n    assert True\n", encoding="utf-8")
            self._write_challenges(project, {
                "S11": {
                    "command": [sys.executable, "-m", "pytest", "-q"],
                    "timeout_s": 10,
                    "success": {"exit_zero": True, "regex_match": r"\b\d+\s+passed\b"},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 0, challenge.stderr)
            result = json.loads(challenge.stdout)
            receipt = result["receipts"][0]
            self.assertEqual(receipt["receipt_type"], "EXECUTED")
            self.assertEqual(receipt["exit_code"], 0)
            self.assertNotIn("claim", receipt)
            self.assertNotIn("origin", receipt)
            self.assertTrue((project / receipt["captured_output"]).exists())

            coverage = {
                "schema": "checkyourself-coverage/1",
                "surfaces": [{
                    "id": "S11",
                    "surface": "Tests, quality gates, and regression coverage",
                    "category": "C5",
                    "status": "Pass",
                    "evidence_reviewed": [receipt["captured_output"]],
                    "evidence_receipts": [receipt],
                }],
            }
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            score = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )
            self.assertEqual(score.returncode, 0, score.stderr)
            c5 = next(item for item in json.loads(score.stdout)["per_category"] if item["id"] == "C5")
            self.assertEqual(c5["coverage_status"], "Pass")
            self.assertEqual(c5["verified_evidence"], [receipt["captured_output"]])

    def test_probe_e1_forged_merged_definition_receipt_is_unknown_without_hmac(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S11": {
                    "command": [sys.executable, "-c", "import pytest; print('1 passed in 0.01s')"],
                    "timeout_s": 10,
                    "success": {"exit_zero": True, "regex_match": r"\b\d+\s+passed\b"},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 0, challenge.stderr)
            forged = json.loads(challenge.stdout)["receipts"][0]
            forged.pop("local_integrity_hmac")
            score = self._score_challenge_receipt(project, forged)
            c5 = next(item for item in score["per_category"] if item["id"] == "C5")
            self.assertEqual(c5["coverage_status"], "Unknown")
            self.assertIn(90, [cap["cap"] for cap in score["caps_applied"]])
            self.assertTrue(any("local integrity binding HMAC" in needed for item in score["manual_evidence_needed"] for needed in item["needed"]))

    def test_executed_receipt_with_invalid_hmac_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S11": {
                    "command": [sys.executable, "-c", "import pytest; print('1 passed in 0.01s')"],
                    "timeout_s": 10,
                    "success": {"exit_zero": True, "regex_match": r"\b\d+\s+passed\b"},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 0, challenge.stderr)
            invalid = json.loads(challenge.stdout)["receipts"][0]
            invalid["local_integrity_hmac"] = "0" * 64
            score = self._score_challenge_receipt(project, invalid)
            c5 = next(item for item in score["per_category"] if item["id"] == "C5")
            self.assertEqual(c5["coverage_status"], "Unknown")
            self.assertIn(90, [cap["cap"] for cap in score["caps_applied"]])

    def test_executed_receipt_is_unknown_when_capture_is_edited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S11": {
                    "command": [sys.executable, "-c", "import pytest; print('1 passed in 0.01s')"],
                    "timeout_s": 10,
                    "success": {"exit_zero": True, "regex_match": r"\b\d+\s+passed\b"},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 0, challenge.stderr)
            receipt = json.loads(challenge.stdout)["receipts"][0]
            capture_path = project / receipt["captured_output"]
            capture_path.write_text('{"stdout":"forged\\n","stderr":""}\n', encoding="utf-8")
            score = self._score_challenge_receipt(project, receipt)
            c5 = next(item for item in score["per_category"] if item["id"] == "C5")
            self.assertEqual(c5["coverage_status"], "Unknown")

    def test_score_reexecutes_and_rejects_changed_excluded_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            state_path = project / ".checkyourself" / "challenge-runs" / "input.txt"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text("before\n", encoding="utf-8")
            self._write_challenges(project, {
                "S11": {
                    "command": [
                        sys.executable,
                        "-c",
                        "import pytest; from pathlib import Path; print(Path('.checkyourself/challenge-runs/input.txt').read_text().strip() + ' 1 passed')",
                    ],
                    "timeout_s": 10,
                    "success": {"exit_zero": True, "regex_match": r"\b\d+\s+passed\b"},
                    "output_kind": "text",
                },
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 0, challenge.stderr)
            receipt = json.loads(challenge.stdout)["receipts"][0]
            state_path.write_text("after\n", encoding="utf-8")
            score = self._score_challenge_receipt(project, receipt)
            c5 = next(item for item in score["per_category"] if item["id"] == "C5")
            self.assertEqual(c5["coverage_status"], "Unknown")
            self.assertTrue(any("re-executed output digest" in needed for item in score["manual_evidence_needed"] for needed in item["needed"]))

    def test_caller_issued_receipt_is_explicitly_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            artifact = self._verification_artifact(project, "S11")
            receipt = self._receipt(
                artifact, project, "caller", "caller state", "perfect", surface_id="S11",
            )
            coverage = {
                "schema": "checkyourself-coverage/1",
                "surfaces": [{
                    "id": "S11", "surface": "Tests, quality gates, and regression coverage", "category": "C5",
                    "status": "Pass", "evidence_reviewed": [artifact.relative_to(project).as_posix()],
                    "evidence_receipts": [receipt],
                }],
            }
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            score = self.run_cli(
                "score", "--findings", str(findings_path), "--coverage", str(coverage_path),
                "--no-history", "--format", "json",
            )
            self.assertEqual(score.returncode, 0, score.stderr)
            data = json.loads(score.stdout)
            self.assertEqual(data["confidence"], "low")
            self.assertIn(
                "UNVERIFIED",
                " ".join(
                    str(item)
                    for needed in data["manual_evidence_needed"]
                    for item in needed["needed"]
                ),
            )
            self.assertLess(data["score"], 100)

    def test_challenge_output_assertions_and_surface_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S02": {"command": [sys.executable, "-c", "import json; print(json.dumps({'status': 'ok', 'dependencies': 1}))"], "timeout_s": 10, "success": {"json_field": {"status": "ok", "dependencies": 1}, "regex_not_match": ["failure"]}, "output_kind": "json"},
                "S05": {"command": [sys.executable, "-c", "import sys; sys.stdout.write('auth status ok checks 1\\n')"], "timeout_s": 10, "success": {"exit_zero": True, "regex_match": r"auth\s+status\s+ok"}, "output_kind": "text"},
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S02", "--format", "json")
            self.assertEqual(challenge.returncode, 0, challenge.stderr)
            receipt = json.loads(challenge.stdout)["receipts"][0]
            self.assertEqual(receipt["surface_id"], "S02")
            self.assertEqual(receipt["status"], "PASS")
            coverage = {
                "schema": "checkyourself-coverage/1",
                "surfaces": [{
                    "id": "S05", "surface": "Auth, permissions, sessions, roles, and admin paths", "category": "C2",
                    "status": "Pass", "evidence_reviewed": [receipt["captured_output"]],
                    "evidence_receipts": [receipt],
                }],
            }
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            score = self.run_cli("score", "--findings", str(findings_path), "--coverage", str(coverage_path), "--no-history", "--format", "json")
            self.assertEqual(score.returncode, 0, score.stderr)
            c2 = next(item for item in json.loads(score.stdout)["per_category"] if item["id"] == "C2")
            self.assertEqual(c2["coverage_status"], "Unknown")

    def test_invalid_override_fails_closed_without_shell_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {"S05": {"command": "echo injected"}})
            result = self.run_cli("challenge", str(project), "--surface", "S05", "--format", "json")
            self.assertEqual(result.returncode, 1)
            data = json.loads(result.stdout)
            self.assertEqual(data["surfaces"][0]["status"], "FAIL")
            self.assertEqual(data["receipts"][0]["command"], [])
            self.assertTrue(data["findings"])

    def test_failing_challenge_is_scored_as_a_finding_and_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S11": {"command": [sys.executable, "-c", "import pytest; print('0 passed in 0.01s'); raise SystemExit(3)"], "timeout_s": 10, "success": {"exit_zero": True, "regex_match": r"\b\d+\s+passed\b"}, "output_kind": "text"},
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 1)
            receipt = json.loads(challenge.stdout)["receipts"][0]
            coverage = {"schema": "checkyourself-coverage/1", "surfaces": [{
                "id": "S11", "surface": "Tests, quality gates, and regression coverage", "category": "C5",
                "status": "Pass", "evidence_reviewed": [receipt["captured_output"]], "evidence_receipts": [receipt],
            }]}
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            score = self.run_cli("score", "--findings", str(findings_path), "--coverage", str(coverage_path), "--no-history", "--format", "json")
            self.assertEqual(score.returncode, 0, score.stderr)
            data = json.loads(score.stdout)
            self.assertIn("CY-CHALLENGE-S11", data["findings_scored"])
            self.assertIn(74, [cap["cap"] for cap in data["caps_applied"]])

    def test_timeout_is_bounded_and_receipted_as_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S11": {"command": [sys.executable, "-c", "import pytest; import time; time.sleep(2)"], "timeout_s": 0.1, "success": {"exit_zero": True, "regex_match": r"\b\d+\s+passed\b"}, "output_kind": "text"},
            })
            result = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(result.returncode, 1)
            data = json.loads(result.stdout)
            self.assertTrue(data["receipts"][0]["timed_out"])
            self.assertEqual(data["receipts"][0]["status"], "FAIL")

    def test_executed_receipt_is_invalid_after_source_tree_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._write_challenges(project, {
                "S11": {"command": [sys.executable, "-c", "import pytest; print('1 passed in 0.01s')"], "timeout_s": 10, "success": {"exit_zero": True, "regex_match": r"\b\d+\s+passed\b"}, "output_kind": "text"},
            })
            challenge = self.run_cli("challenge", str(project), "--surface", "S11", "--format", "json")
            self.assertEqual(challenge.returncode, 0, challenge.stderr)
            receipt = json.loads(challenge.stdout)["receipts"][0]
            (project / "app.py").write_text("print('changed')\n", encoding="utf-8")
            coverage = {"schema": "checkyourself-coverage/1", "surfaces": [{
                "id": "S11", "surface": "Tests, quality gates, and regression coverage", "category": "C5",
                "status": "Pass", "evidence_reviewed": [receipt["captured_output"]], "evidence_receipts": [receipt],
            }]}
            findings_path = project / "findings.json"
            coverage_path = project / "coverage.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
            score = self.run_cli("score", "--findings", str(findings_path), "--coverage", str(coverage_path), "--no-history", "--format", "json")
            self.assertEqual(score.returncode, 0, score.stderr)
            c5 = next(item for item in json.loads(score.stdout)["per_category"] if item["id"] == "C5")
            self.assertEqual(c5["coverage_status"], "Unknown")


if __name__ == "__main__":
    unittest.main()
