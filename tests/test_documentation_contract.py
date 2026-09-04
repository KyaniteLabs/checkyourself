from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_detector_rule_authority_is_unambiguous(self) -> None:
        llms = self.read("llms.txt").lower()
        cli = self.read("docs/cli.md").lower()

        self.assertIn("rules.md", llms)
        self.assertIn("review, safety, evidence, and workflow rules", llms)
        self.assertIn("canonical detector-rule registry", llms)
        self.assertIn("canonical detector-rule registry", cli)
        self.assertNotIn("all detection rules with stable ids", llms)

    def test_lifecycle_and_not_applicable_contract_is_current(self) -> None:
        plan = self.read("docs/agent-access-cli-plan.md")
        plan_lower = plan.lower()

        self.assertNotIn("deterministic scoring algorithm (proposed)", plan_lower)
        self.assertNotIn("`blocked`", plan_lower)
        for status in ("fixed", "accepted-risk", "deferred", "not-applicable", "suppressed"):
            self.assertIn(f"`{status}`", plan)
        self.assertIn("NotApplicable` surfaces", plan)
        self.assertIn("retain their category weight", plan)

    def test_report_backlog_and_dashboard_contracts_are_complete(self) -> None:
        report = self.read("05_OUTPUT_TEMPLATES/production-reality-report.md")
        self.assertIn("Impact / blast radius", report)
        self.assertIn("Files/systems touched", report)
        self.assertIn("Status: Pass / Finding / Unknown / Not applicable", report)

        for relative in ("05_OUTPUT_TEMPLATES/README.md", "10_DASHBOARD/README.md", "10_DASHBOARD/CONTEXT.md"):
            body = self.read(relative).lower()
            self.assertIn("dashboard yes", body)
            self.assertIn("dashboard inline", body)

    def test_manual_fallback_and_score_contracts_are_explicit(self) -> None:
        skill = self.read("skills/checkyourself/SKILL.md")
        scoring = self.read("02_RUN_DIAGNOSTIC/scoring-method.md")

        self.assertIn("Manual fallback contract", skill)
        self.assertIn("CY-MANUAL-AUTH-001", skill)
        self.assertIn("evidence rubric", skill)
        self.assertIn("../../docs/cli.md#canonical-detector-rule-registry", skill)
        self.assertIn("final_score = min(base_score, minimum_cap)", skill)
        self.assertIn("base_score = round(sum(category_award))", scoring)
        self.assertIn("final_score = min(base_score, minimum_cap)", scoring)
        self.assertIn("../docs/cli.md#scoring", scoring)

    def test_native_adapter_covers_discovery_and_write_boundaries(self) -> None:
        readme = self.read("06_ADAPTERS/README.md")
        adapter = self.read("06_ADAPTERS/native-cli-mcp.md")
        cli = self.read("docs/cli.md")
        mcp = self.read("docs/mcp.md")

        self.assertIn("native-cli-mcp.md", readme)
        for phrase in ("describe --format json", "CHECKYOURSELF_SCAN_ROOT", "--no-write", "user-approved"):
            self.assertIn(phrase, adapter)
        self.assertIn("native CLI/MCP adapter", cli)
        self.assertIn("native CLI/MCP adapter", mcp)

    def test_security_policy_tracks_manifest_release_and_main(self) -> None:
        manifest = json.loads(self.read("checkyourself.manifest.json"))
        version = manifest["version"]
        release_line = ".".join(version.split(".")[:2]) + ".x"
        security = self.read("SECURITY.md").lower()

        self.assertIn(f"latest tagged release is `{version}`", security)
        self.assertIn(release_line.lower(), security)
        self.assertIn("public `main` branch", security)
