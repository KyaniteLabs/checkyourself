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
        self.assertIn("value omitted", data["findings"][0]["evidence"][0])

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
        tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
        self.assertIn("score", tool_names)
        structured = responses[2]["result"]["structuredContent"]
        self.assertEqual(structured["schema"], "checkyourself-capabilities/1")


if __name__ == "__main__":
    unittest.main()
