from __future__ import annotations

import json
from copy import deepcopy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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
            coverage_path = project / "CHECKYOURSELF_COVERAGE.generated.json"
            self.assertTrue(coverage_path.exists())
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            self.assertEqual(coverage["schema"], "checkyourself-coverage/1")

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

    def test_missing_lockfile_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "package.json").write_text('{"name": "x"}\n', encoding="utf-8")
            result = self.run_cli("scan", str(project), "--format", "json", "--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        ids = {f["id"] for f in json.loads(result.stdout)["findings"]}
        self.assertIn("CY-SUPPLY-002", ids)

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
                self.assertEqual(cli_result.stdout, "")
                self.assertIn("invalid coverage artifact", cli_result.stderr)

                mcp_response = self._run_mcp_score(coverage)
                mcp_result = mcp_response["result"]
                self.assertTrue(mcp_result["isError"])
                self.assertNotIn("score", mcp_result["structuredContent"])
                self.assertNotIn("confidence", mcp_result["structuredContent"])

    def test_coverage_backed_full_evidence_reaches_high_confidence(self) -> None:
        from importlib import util as _util
        spec = _util.spec_from_file_location("cy", CLI)
        cy = _util.module_from_spec(spec)
        spec.loader.exec_module(cy)
        surfaces = []
        for sid, surface, category in cy.COVERAGE_SURFACES:
            surfaces.append({
                "id": sid, "surface": surface, "category": category,
                "status": "Pass", "evidence_reviewed": [f"{surface}: verified in src/app.py:10"],
            })
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
        self.assertTrue(score["coverage_complete"])
        self.assertEqual(score["confidence"], "high")
        self.assertEqual(score["score"], 100)

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
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            findings_path = project / "findings.json"
            findings_path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            history_path = project / "history.json"
            history_path.write_text("{ this is not valid json", encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
