from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "checkyourself.py"


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
                    "  - id: CY-001",
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
        self.assertEqual([finding["id"] for finding in suppressed], ["CY-001"])
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

    def test_score_without_coverage_uses_scan_estimate_and_writes_history(self) -> None:
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

            score_result = self.run_cli("score", "--findings", str(scan_path), "--format", "json")

            self.assertEqual(score_result.returncode, 0, score_result.stderr)
            score = json.loads(score_result.stdout)
            self.assertEqual(score["score_mode"], "scan-derived-estimate")
            self.assertGreaterEqual(score["score"], 90)
            self.assertFalse(score["coverage_complete"])
            self.assertEqual(score["confidence"], "low")
            self.assertTrue(score["manual_evidence_needed"])
            history = json.loads((project / ".checkyourself-score-history.json").read_text(encoding="utf-8"))
            self.assertEqual(history[-1]["score"], score["score"])

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


if __name__ == "__main__":
    unittest.main()
