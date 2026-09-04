from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_public.py"


class ValidatePublicTests(unittest.TestCase):
    def run_validator(self, root: Path | str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(root)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_real_repository_passes_validation(self) -> None:
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK: public CheckYourself validation passed", result.stdout)

    def test_missing_required_files_fail_with_named_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        self.assertIn("Public validation failed:", result.stdout)
        self.assertIn("missing required public file: README.md", result.stdout)
        self.assertIn("missing required public file: tools/checkyourself.py", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_required_paths_must_be_regular_in_root_files(self) -> None:
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "README.md").mkdir()
            (Path(outside) / "private.md").write_text("private\n", encoding="utf-8")
            (project / "CONTEXT.md").symlink_to(Path(outside) / "private.md")
            result = self.run_validator(project)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "required public path must be a regular in-root file: README.md",
            result.stdout,
        )
        self.assertIn(
            "required public path must be a regular in-root file: CONTEXT.md",
            result.stdout,
        )
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_json_is_reported_with_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "broken.json").write_text("{not json", encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid JSON: broken.json", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_non_dict_dashboard_sample_is_reported_not_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            samples = Path(tmp) / "samples"
            samples.mkdir()
            (samples / "sample-dashboard-data.json").write_text("[]", encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(
            "dashboard data example must be a JSON object: samples/sample-dashboard-data.json",
            result.stdout,
        )

    def test_dashboard_sample_shape_contract(self) -> None:
        message = "dashboard data example does not match an accepted shape"
        accepted = {
            "app_name": "Demo",
            "score": 80,
            "confidence": "low",
            "counts": {},
            "coverage": [],
            "findings": [],
        }
        for payload, should_error in (({"foo": 1}, True), (accepted, False)):
            with self.subTest(payload=sorted(payload)):
                with tempfile.TemporaryDirectory() as tmp:
                    samples = Path(tmp) / "samples"
                    samples.mkdir()
                    (samples / "sample-dashboard-data.json").write_text(
                        json.dumps(payload), encoding="utf-8"
                    )
                    result = self.run_validator(tmp)
                if should_error:
                    self.assertIn(message, result.stdout)
                else:
                    self.assertNotIn(message, result.stdout)

    def test_broken_markdown_link_is_reported_with_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "real.md").write_text("# real\n", encoding="utf-8")
            (project / "doc.md").write_text(
                "\n".join([
                    "# Doc",
                    "",
                    "[good](real.md)",
                    "[external](https://example.com/page)",
                    "[missing](does-not-exist.md)",
                    "",
                ]),
                encoding="utf-8",
            )
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        self.assertIn("broken local markdown link: doc.md:5 -> does-not-exist.md", result.stdout)
        # Resolvable local links and external URLs must not be flagged.
        self.assertNotIn("doc.md:3", result.stdout)
        self.assertNotIn("doc.md:4", result.stdout)

    def test_markdown_link_may_not_escape_validated_root(self) -> None:
        # A relative link that resolves outside the validated root is broken
        # even when the target file actually exists.
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as tmp:
            target = Path(outside) / "outside.md"
            target.write_text("# outside\n", encoding="utf-8")
            link = f"../{Path(outside).name}/outside.md"
            (Path(tmp) / "esc.md").write_text(f"[esc]({link})\n", encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        self.assertIn("broken local markdown link: esc.md:1", result.stdout)

    def test_markdown_link_titles_and_escaped_destinations_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "target.md").write_text("# target\n", encoding="utf-8")
            (project / "a(b).md").write_text("# escaped\n", encoding="utf-8")
            (project / "doc.md").write_text(
                "\n".join([
                    '[quoted](target.md "a title")',
                    "[angle](<target.md> 'another title')",
                    r"[escaped](a\(b\).md \"title\")",
                    "",
                ]),
                encoding="utf-8",
            )
            result = self.run_validator(project)

        self.assertNotIn("broken local markdown link", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_stale_public_phrase_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "notes.md").write_text("status Dashboard=Yes for launch\n", encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        self.assertIn("stale public phrase in notes.md: Dashboard=Yes", result.stdout)

    def test_canonical_dashboard_template_may_not_hardcode_secondary_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard = Path(tmp) / "10_DASHBOARD"
            dashboard.mkdir()
            (dashboard / "dashboard-template.html").write_text("<h1>Puntaje</h1>\n", encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "canonical dashboard template hardcodes a secondary language in "
            "10_DASHBOARD/dashboard-template.html: Puntaje",
            result.stdout,
        )

    def test_auto_bilingual_instructions_must_ask_first_except_output_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            out_dir = project / "04_LEARNING_PLAN" / "output"
            out_dir.mkdir(parents=True)
            (project / "plan.md").write_text("Always make the plan bilingual.\n", encoding="utf-8")
            (out_dir / "result.md").write_text("Always make the plan bilingual.\n", encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "auto-bilingual instruction must ask for confirmation first in plan.md: "
            "make the plan bilingual",
            result.stdout,
        )
        # Generated user outputs are allowed to contain the phrase.
        self.assertNotIn("04_LEARNING_PLAN/output/result.md", result.stdout)

    def test_duplicate_assets_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            assets = Path(tmp) / "assets"
            assets.mkdir()
            (assets / "one.png").write_bytes(b"same-bytes")
            (assets / "two.png").write_bytes(b"same-bytes")
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate asset files: assets/one.png, assets/two.png", result.stdout)

    def test_asset_symlink_is_rejected_without_reading_target(self) -> None:
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            assets = project / "assets"
            assets.mkdir()
            (assets / "one.png").write_bytes(b"same-bytes")
            external = Path(outside) / "two.png"
            external.write_bytes(b"same-bytes")
            (assets / "two.png").symlink_to(external)
            result = self.run_validator(project)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public asset must be a regular in-root file: assets/two.png", result.stdout)
        self.assertNotIn("duplicate asset files", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_manifest_contract_is_enforced(self) -> None:
        manifest = {
            "version": "9.9.9",
            "entrypoints": {"start": "missing-entrypoint.md"},
            "modes": ["scan", "scan", "dashboard-a", "dashboard-b", "dashboard-c"],
            "optional_dashboard": {
                "template": "wrong.html",
                "inline_fallback": "10_DASHBOARD/inline-dashboard.md",
                "advanced_data_template": "extra.js",
            },
            "html_dashboard_template": "legacy.html",
        }
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "checkyourself.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (project / "CHANGELOG.md").write_text("## 1.0.0\n", encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertEqual(result.returncode, 1)
        for expected in (
            "manifest version 9.9.9 is missing from CHANGELOG.md",
            "manifest entrypoint is missing: start -> missing-entrypoint.md",
            "manifest modes contain duplicates",
            "manifest modes contain too many dashboard variants",
            "manifest optional dashboard template must be the canonical HTML/CSS dashboard",
            "manifest optional dashboard must not advertise a second JS/data-template dashboard",
            "manifest must use optional_dashboard.template as the only rich dashboard template",
        ):
            self.assertIn(expected, result.stdout)

    def test_non_dict_manifest_is_reported_not_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "checkyourself.manifest.json").write_text("[]", encoding="utf-8")
            (project / "CHANGELOG.md").write_text("## 1.0.0\n", encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("checkyourself.manifest.json must be a JSON object", result.stdout)

    def test_symlinked_files_are_not_read_through(self) -> None:
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as tmp:
            target = Path(outside) / "private.json"
            target.write_text("{definitely not json", encoding="utf-8")
            (Path(tmp) / "link.json").symlink_to(target)
            result = self.run_validator(tmp)

        self.assertNotIn("link.json", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_oversized_files_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "big.json").write_text("x" * 5_000_001, encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertNotIn("big.json", result.stdout)

    def test_ignored_directories_are_not_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for ignored in ("node_modules", ".worktrees", "__pycache__"):
                sub = Path(tmp) / ignored
                sub.mkdir()
                (sub / "broken.json").write_text("{not json", encoding="utf-8")
            result = self.run_validator(tmp)

        self.assertNotIn("broken.json", result.stdout)

    def test_release_boundary_requires_gitignore_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_without = self.run_validator(tmp)
            (Path(tmp) / ".gitignore").write_text(
                "\n".join([
                    "checkyourself-creator-launch-kit copy/",
                    ".omx/",
                    ".DS_Store",
                    "CHECKYOURSELF_PROJECT_CONTEXT.generated.md",
                    "",
                ]),
                encoding="utf-8",
            )
            result_with = self.run_validator(tmp)

        self.assertIn("public exclude is not listed in .gitignore: .omx", result_without.stdout)
        self.assertIn("scanner-generated project context output is not ignored", result_without.stdout)
        self.assertNotIn("not listed in .gitignore", result_with.stdout)
        self.assertNotIn("scanner-generated project context output is not ignored", result_with.stdout)


if __name__ == "__main__":
    unittest.main()
