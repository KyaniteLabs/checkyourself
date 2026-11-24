"""In-process behaviour tests for tools/validate_public.py.

The existing suite drives the validator through subprocesses, which deadlocks
under mutmut's per-test fork machinery (fork + inherited pipes). These tests
import the validators directly and build minimal fixtures in tmp dirs, so the
mutation lane never forks inside a fork. Expectations are derived by hand
from the validator rules.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tools.validate_public as vp  # noqa: E402


class TestRequired(unittest.TestCase):
    def test_minimal_root_has_no_required_errors(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            for rel in vp.REQUIRED:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x\n")
            errors: list[str] = []
            vp.validate_required(root, errors)
            self.assertEqual(errors, [])

    def test_one_missing_file_is_named(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            for rel in vp.REQUIRED:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x\n")
            (root / "rules.md").unlink()
            errors: list[str] = []
            vp.validate_required(root, errors)
            self.assertEqual(errors, ["missing required public file: rules.md"])

    def test_symlinked_required_path_is_refused(self):
        import os

        with TemporaryDirectory() as td:
            root = Path(td)
            outside = Path(td) / "outside.md"
            outside.write_text("x")
            for rel in vp.REQUIRED:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if rel == "rules.md":
                    os.symlink(outside, p)
                else:
                    p.write_text("x\n")
            errors: list[str] = []
            vp.validate_required(root, errors)
            self.assertEqual(errors, ["required public path must be a regular in-root file: rules.md"])


class TestReleaseBoundary(unittest.TestCase):
    def test_unignored_public_exclude_is_an_error(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".gitignore").write_text("")  # no excludes listed
            errors: list[str] = []
            vp.validate_release_boundary(root, errors)
            self.assertTrue(any(e.startswith("public exclude is not listed in .gitignore:") for e in errors))
            self.assertIn("scanner-generated project context output is not ignored", errors)

    def test_generated_pattern_wildcard_satisfies_the_boundary(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".gitignore").write_text("\n".join(vp.PUBLIC_EXCLUDES) + "\nCHECKYOURSELF_*.generated.md\n")
            errors: list[str] = []
            vp.validate_release_boundary(root, errors)
            self.assertEqual(errors, [])

    def test_existing_private_path_must_be_ignored(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            rel = vp.PUBLIC_EXCLUDES[0]
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("private\n")
            (root / ".gitignore").write_text(
                "\n".join(e for e in vp.PUBLIC_EXCLUDES if e != rel) + "\nCHECKYOURSELF_*.generated.md\n"
            )
            errors: list[str] = []
            vp.validate_release_boundary(root, errors)
            self.assertIn(f"public exclude is not listed in .gitignore: {rel}", errors)


class TestIcmContext(unittest.TestCase):
    def test_root_context_needs_all_three_phrases(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "CONTEXT.md").write_text("## Stage Router\n## Output Handoffs\n")
            errors: list[str] = []
            vp.validate_icm_context(root, errors)
            self.assertEqual(
                errors,
                [
                    "CONTEXT.md missing ## Public Release Boundary",
                ],
            )

    def test_stage_context_needs_three_sections_when_present(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            rel = vp.STAGE_CONTEXTS[0]
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            (root / "CONTEXT.md").write_text("## Stage Router\n## Output Handoffs\n## Public Release Boundary\n")
            p.write_text("## Inputs\n## Process\n")
            errors: list[str] = []
            vp.validate_icm_context(root, errors)
            self.assertEqual(errors, [f"{rel} missing ## Outputs"])

    def test_absent_stage_context_is_skipped(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "CONTEXT.md").write_text("## Stage Router\n## Output Handoffs\n## Public Release Boundary\n")
            errors: list[str] = []
            vp.validate_icm_context(root, errors)
            self.assertEqual(errors, [])


class TestValidateJson(unittest.TestCase):
    def test_invalid_public_json_is_reported_with_the_parser_reason(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "bad.json").write_text("{oops")
            errors: list[str] = []
            vp.validate_json(root, errors)
            self.assertEqual(len(errors), 1)
            self.assertTrue(errors[0].startswith("invalid JSON: bad.json ("))

    def test_dashboard_example_shapes(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            rel = "samples/sample-dashboard-data.json"
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('["not", "an", "object"]')
            errors: list[str] = []
            vp.validate_json(root, errors)
            self.assertEqual(errors, [f"dashboard data example must be a JSON object: {rel}"])

            p.write_text(
                '{"app_name": "a", "score": 1, "confidence": "c", "counts": {}, "coverage": {}, "findings": []}'
            )
            errors2: list[str] = []
            vp.validate_json(root, errors2)
            self.assertEqual(errors2, [])

            p.write_text('{"app_name": "a"}')
            errors3: list[str] = []
            vp.validate_json(root, errors3)
            self.assertEqual(errors3, [f"dashboard data example does not match an accepted shape: {rel}"])


class TestValidateManifest(unittest.TestCase):
    def test_manifest_version_missing_from_changelog_is_an_error(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "checkyourself.manifest.json").write_text('{"version": "9.9.9"}')
            (root / "CHANGELOG.md").write_text("## 1.0.0\n")
            errors: list[str] = []
            vp.validate_manifest(root, errors)
            self.assertIn("manifest version 9.9.9 is missing from CHANGELOG.md", errors)

    def test_entrypoint_missing_and_duplicate_modes(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "checkyourself.manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0.0",
                        "entrypoints": {"cli": "nope.py"},
                        "modes": ["a", "a"],
                    }
                )
            )
            (root / "CHANGELOG.md").write_text("## 1.0.0\n")
            errors: list[str] = []
            vp.validate_manifest(root, errors)
            self.assertIn("manifest entrypoint is missing: cli -> nope.py", errors)
            self.assertIn("manifest modes contain duplicates", errors)

    def test_optional_dashboard_contract(self):
        base = {
            "version": "1.0.0",
            "optional_dashboard": {
                "template": "wrong.html",
                "inline_fallback": "wrong.md",
                "advanced_data_template": "x",
            },
        }
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "checkyourself.manifest.json").write_text(json.dumps(base))
            (root / "CHANGELOG.md").write_text("## 1.0.0\n")
            errors: list[str] = []
            vp.validate_manifest(root, errors)
            self.assertIn("manifest optional dashboard template must be the canonical HTML/CSS dashboard", errors)
            self.assertIn("manifest optional dashboard inline fallback is missing or wrong", errors)
            self.assertIn("manifest optional dashboard must not advertise a second JS/data-template dashboard", errors)

            base2 = dict(base)
            base2["optional_dashboard"] = {
                "template": "10_DASHBOARD/dashboard-template.html",
                "inline_fallback": "10_DASHBOARD/inline-dashboard.md",
            }
            base2["html_dashboard_template"] = "z"
            (root / "checkyourself.manifest.json").write_text(json.dumps(base2))
            errors2: list[str] = []
            vp.validate_manifest(root, errors2)
            self.assertEqual(
                errors2,
                ["manifest must use optional_dashboard.template as the only rich dashboard template"],
            )

    def test_too_many_dashboard_modes(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "checkyourself.manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0.0",
                        "modes": ["dashboard", "dashboard-inline", "dashboard-x"],
                    }
                )
            )
            (root / "CHANGELOG.md").write_text("## 1.0.0\n")
            errors: list[str] = []
            vp.validate_manifest(root, errors)
            self.assertIn("manifest modes contain too many dashboard variants", errors)

    def test_absent_manifest_or_changelog_is_silent(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            errors: list[str] = []
            vp.validate_manifest(root, errors)
            self.assertEqual(errors, [])


class TestMarkdownLinks(unittest.TestCase):
    def md_root(self, body: str) -> Path:
        import tempfile

        root = Path(tempfile.mkdtemp())
        (root / "README.md").write_text(body, encoding="utf-8")
        (root / "exists.md").write_text("target\n", encoding="utf-8")
        sub = root / "docs"
        sub.mkdir()
        (sub / "target.md").write_text("t\n", encoding="utf-8")
        return root

    def run_errors(self, root: Path) -> list[str]:
        errors: list[str] = []
        vp.validate_markdown_links(root, errors)
        return errors

    def test_broken_local_link_is_reported_with_file_and_line(self):
        root = self.md_root("intro\n\n[missing](gone.md)\n")
        self.assertEqual(
            self.run_errors(root),
            ["broken local markdown link: README.md:3 -> gone.md"],
        )

    def test_existing_relative_subdirectory_and_encoded_links_pass(self):
        root = self.md_root("[a](exists.md) [b](docs/target.md) [c](docs/target.md#anchor) [d](docs%2Ftarget.md)\n")
        self.assertEqual(self.run_errors(root), [])

    def test_schemes_mailto_and_pure_anchors_are_skipped(self):
        root = self.md_root("[u](https://example.com/x) [m](mailto:a@b.c) [x](ftp://h/f) [frag](#section) [empty]()\n")
        self.assertEqual(self.run_errors(root), [])

    def test_file_line_citation_suffix_is_stripped_before_resolving(self):
        root = self.md_root("[cite](exists.md:12:34)\n")
        self.assertEqual(self.run_errors(root), [])

    def test_link_outside_root_is_reported(self):
        root = self.md_root("[esc](../outside.md)\n")
        errs = self.run_errors(root)
        self.assertEqual(len(errs), 1)
        self.assertTrue(errs[0].startswith("broken local markdown link: README.md:1"))

    def test_angle_destination_and_escaped_paren_parse(self):
        root = self.md_root("[a](<exists.md>) [b](ex\\(ists\\).md)\n")
        # escaped paren target does not exist under that literal name
        errs = self.run_errors(root)
        self.assertEqual(len(errs), 1)
        self.assertIn("ex\\(ists\\).md", errs[0])

    def test_unterminated_link_body_is_skipped(self):
        root = self.md_root("[dangling](unterminated\n")
        self.assertEqual(self.run_errors(root), [])

    def test_non_markdown_files_are_skipped(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        (root / "notes.txt").write_text("[gone](missing.md)\n", encoding="utf-8")
        self.assertEqual(self.run_errors(root), [])


class TestAssets(unittest.TestCase):
    def errors(self, root: Path) -> list[str]:
        errs: list[str] = []
        vp.validate_assets(root, errs)
        return errs

    def test_absent_assets_directory_passes(self):
        import tempfile

        self.assertEqual(self.errors(Path(tempfile.mkdtemp())), [])

    def test_symlinked_assets_directory_is_rejected(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        real = root / "real"
        real.mkdir()
        (real / "a.png").write_bytes(b"a")
        (root / "assets").symlink_to(real)
        errs = self.errors(root)
        self.assertEqual(errs, ["public asset directory must be a regular in-root directory: assets"])

    def test_duplicate_asset_contents_are_reported(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        assets = root / "assets"
        assets.mkdir()
        (assets / "one.png").write_bytes(b"same")
        (assets / "two.png").write_bytes(b"same")
        (assets / "three.png").write_bytes(b"different")
        self.assertEqual(
            self.errors(root),
            ["duplicate asset files: assets/one.png, assets/two.png"],
        )

    def test_subdirectory_inside_assets_is_skipped(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        assets = root / "assets"
        (assets / "nested").mkdir(parents=True)
        self.assertEqual(self.errors(root), [])


class TestDocDrift(unittest.TestCase):
    def errors(self, root: Path) -> list[str]:
        errs: list[str] = []
        vp.validate_doc_drift(root, errs)
        return errs

    def test_identical_token_efficiency_docs_are_duplicates(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        docs = root / "docs"
        docs.mkdir()
        (docs / "token-efficiency-and-context-control.md").write_text("same\n")
        (docs / "token-efficiency.md").write_text("same\n")
        self.assertEqual(self.errors(root), ["token-efficiency docs are exact duplicates"])

    def test_missing_companion_doc_passes(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        docs = root / "docs"
        docs.mkdir()
        (docs / "token-efficiency.md").write_text("alone\n")
        self.assertEqual(self.errors(root), [])


class TestPublicText(unittest.TestCase):
    def base_root(self) -> Path:
        import tempfile

        root = Path(tempfile.mkdtemp())
        # the required-phrase surfaces, all satisfied
        (root / "10_DASHBOARD" / "CONTEXT.md").parent.mkdir(parents=True)
        (root / "10_DASHBOARD" / "CONTEXT.md").write_text("canonical HTML/CSS dashboard and inline Markdown fallback\n")
        (root / "05_OUTPUT_TEMPLATES").mkdir()
        (root / "05_OUTPUT_TEMPLATES" / "dashboard-prompt.md").write_text(
            "single canonical HTML/CSS dashboard, inline Markdown fallback\n"
        )
        (root / "AGENTS.md").write_text("candidate second language; ask the user first\n")
        (root / "05_OUTPUT_TEMPLATES" / "bespoke-learning-plan.md").write_text(
            "why_this_source_is_trusted authority_level checked_at\n"
        )
        return root

    def errors(self, root: Path) -> list[str]:
        errs: list[str] = []
        vp.validate_public_text(root, errs)
        return errs

    def test_satisfied_root_is_clean(self):
        self.assertEqual(self.errors(self.base_root()), [])

    def test_stale_phrase_in_markdown_is_reported(self):
        root = self.base_root()
        (root / "README.md").write_text("Dashboard=Yes\n")
        errs = self.errors(root)
        self.assertEqual(errs, ["stale public phrase in README.md: Dashboard=Yes"])

    def test_stale_phrase_scanned_in_json_yaml_html_txt(self):
        root = self.base_root()
        (root / "data.json").write_text('{"a": "dashboard:on"}\n')
        (root / "notes.txt").write_text("07_PUBLISHING\n")
        (root / "page.html").write_text("<i>Skool post and YouTube</i>\n")
        (root / "conf.yaml").write_text("x: advanced data-template path\n")
        errs = self.errors(root)
        self.assertEqual(len(errs), 4)
        self.assertIn("stale public phrase in data.json: dashboard:on", errs)
        self.assertIn("stale public phrase in page.html: Skool post and YouTube", errs)

    def test_unscanned_suffix_is_skipped(self):
        root = self.base_root()
        (root / "binary.bin").write_text("Dashboard=Yes\n")
        self.assertEqual(self.errors(root), [])

    def test_missing_dashboard_context_phrases_are_both_reported(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        errs = self.errors(root)
        self.assertIn("10_DASHBOARD/CONTEXT.md must identify the canonical HTML/CSS dashboard path", errs)
        self.assertIn("10_DASHBOARD/CONTEXT.md must identify the inline Markdown fallback", errs)

    def test_missing_dashboard_prompt_phrases_are_both_reported(self):
        root = self.base_root()
        (root / "05_OUTPUT_TEMPLATES" / "dashboard-prompt.md").write_text("thin\n")
        errs = self.errors(root)
        self.assertIn("05_OUTPUT_TEMPLATES/dashboard-prompt.md must identify the single canonical dashboard", errs)
        self.assertIn("05_OUTPUT_TEMPLATES/dashboard-prompt.md must identify the inline Markdown fallback", errs)

    def test_missing_agents_md_requirements_are_reported(self):
        root = self.base_root()
        (root / "AGENTS.md").write_text("neither phrase present\n")
        errs = self.errors(root)
        self.assertIn("AGENTS.md must require runtime candidate second-language detection", errs)
        self.assertIn("AGENTS.md must require asking before using an inferred second language", errs)

    def test_learning_plan_missing_field_is_reported_per_field(self):
        root = self.base_root()
        (root / "05_OUTPUT_TEMPLATES" / "bespoke-learning-plan.md").write_text("why_this_source_is_trusted only\n")
        errs = self.errors(root)
        self.assertEqual(
            errs,
            [
                "bespoke learning plan template missing source reliability field: authority_level",
                "bespoke learning plan template missing source reliability field: checked_at",
            ],
        )

    def test_hardcoded_secondary_language_in_canonical_templates(self):
        root = self.base_root()
        (root / "10_DASHBOARD" / "dashboard-template.html").write_text("<b>Puntaje</b>\n")
        errs = self.errors(root)
        self.assertEqual(
            errs,
            [
                "canonical dashboard template hardcodes a secondary language in "
                "10_DASHBOARD/dashboard-template.html: Puntaje"
            ],
        )

    def test_auto_bilingual_phrase_outside_output_dirs_is_reported(self):
        root = self.base_root()
        (root / "GUIDE.md").write_text("make learning/dashboard outputs bilingual\n")
        errs = self.errors(root)
        self.assertEqual(
            errs,
            [
                "auto-bilingual instruction must ask for confirmation first in GUIDE.md: "
                "make learning/dashboard outputs bilingual"
            ],
        )

    def test_auto_bilingual_phrase_inside_output_dirs_is_skipped(self):
        root = self.base_root()
        out = root / "10_DASHBOARD" / "output"
        out.mkdir()
        (out / "generated.md").write_text("make the plan bilingual\n")
        self.assertEqual(self.errors(root), [])

    def test_non_dogfood_example_neutral_fields(self):
        root = self.base_root()
        (root / "samples").mkdir(exist_ok=True)
        (root / "samples" / "sample-dashboard-data.json").write_text('{"note": "plain_other_language"}\n')
        errs = self.errors(root)
        self.assertEqual(
            errs,
            [
                "non-dogfood example must use runtime-neutral secondary-language fields "
                "in samples/sample-dashboard-data.json: plain_other_language"
            ],
        )


class TestManifestExtraBranches(unittest.TestCase):
    def errors(self, root: Path) -> list[str]:
        errs: list[str] = []
        vp.validate_manifest(root, errs)
        return errs

    VALID_OPTIONAL_DASHBOARD = {
        "template": "10_DASHBOARD/dashboard-template.html",
        "inline_fallback": "10_DASHBOARD/inline-dashboard.md",
    }

    def make(self, manifest: dict) -> Path:
        import tempfile

        base = {"optional_dashboard": dict(self.VALID_OPTIONAL_DASHBOARD)}
        base.update(manifest)
        root = Path(tempfile.mkdtemp())
        (root / "checkyourself.manifest.json").write_text(json.dumps(base))
        (root / "CHANGELOG.md").write_text("## 1.0.0\n")
        return root

    def test_non_object_manifest_is_reported(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        (root / "checkyourself.manifest.json").write_text("[1]")
        (root / "CHANGELOG.md").write_text("x")
        self.assertEqual(self.errors(root), ["checkyourself.manifest.json must be a JSON object"])

    def test_version_missing_from_changelog(self):
        root = self.make({"version": "9.9.9"})
        self.assertEqual(self.errors(root), ["manifest version 9.9.9 is missing from CHANGELOG.md"])

    def test_missing_entrypoint(self):
        root = self.make({"entrypoints": {"cli": "tools/nope.py"}})
        self.assertEqual(self.errors(root), ["manifest entrypoint is missing: cli -> tools/nope.py"])

    def test_duplicate_modes(self):
        root = self.make({"modes": ["cli", "cli"]})
        self.assertEqual(self.errors(root), ["manifest modes contain duplicates"])

    def test_too_many_dashboard_modes(self):
        root = self.make({"modes": ["dashboard-a", "dashboard-b", "dashboard-c"]})
        self.assertEqual(self.errors(root), ["manifest modes contain too many dashboard variants"])

    def test_optional_dashboard_template_must_be_canonical(self):
        root = self.make({"optional_dashboard": {**self.VALID_OPTIONAL_DASHBOARD, "template": "other.html"}})
        errs = self.errors(root)
        self.assertEqual(errs, ["manifest optional dashboard template must be the canonical HTML/CSS dashboard"])

    def test_optional_dashboard_fallback_must_be_inline(self):
        root = self.make({"optional_dashboard": {**self.VALID_OPTIONAL_DASHBOARD, "inline_fallback": "x.md"}})
        errs = self.errors(root)
        self.assertEqual(errs, ["manifest optional dashboard inline fallback is missing or wrong"])

    def test_second_rich_dashboard_advertisement_is_rejected(self):
        root = self.make({"optional_dashboard": {**self.VALID_OPTIONAL_DASHBOARD, "advanced_data_template": "t.html"}})
        self.assertEqual(
            self.errors(root), ["manifest optional dashboard must not advertise a second JS/data-template dashboard"]
        )

    def test_html_dashboard_template_top_level_key_is_rejected(self):
        root = self.make({"html_dashboard_template": "t.html"})
        self.assertEqual(
            self.errors(root), ["manifest must use optional_dashboard.template as the only rich dashboard template"]
        )

    def test_clean_manifest_passes(self):
        root = self.make({"version": "1.0.0", "modes": ["cli", "mcp"]})
        self.assertEqual(self.errors(root), [])


class TestJsonExampleShapes(unittest.TestCase):
    def errors(self, root: Path) -> list[str]:
        errs: list[str] = []
        vp.validate_json(root, errs)
        return errs

    def root_with_example(self, payload: str) -> Path:
        import tempfile

        root = Path(tempfile.mkdtemp())
        example = root / "samples" / "sample-dashboard-data.json"
        example.parent.mkdir()
        example.write_text(payload)
        return root

    def test_invalid_json_in_public_file_is_reported(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        (root / "bad.json").write_text("{nope")
        errs = self.errors(root)
        self.assertEqual(len(errs), 1)
        self.assertTrue(errs[0].startswith("invalid JSON: bad.json"))

    def test_non_object_example_is_reported(self):
        root = self.root_with_example("[1]")
        self.assertEqual(
            self.errors(root), ["dashboard data example must be a JSON object: samples/sample-dashboard-data.json"]
        )

    def test_compact_and_template_shapes_pass(self):
        compact = {"app_name": 1, "score": 1, "confidence": 1, "counts": {}, "coverage": {}, "findings": []}
        self.assertEqual(self.errors(self.root_with_example(json.dumps(compact))), [])
        template = {"project": "p", "score": 1, "counts": {}, "coverage": {}, "backlog": [], "learning_plan": []}
        self.assertEqual(self.errors(self.root_with_example(json.dumps(template))), [])

    def test_wrong_shape_example_is_reported(self):
        root = self.root_with_example(json.dumps({"unrelated": True}))
        self.assertEqual(
            self.errors(root),
            ["dashboard data example does not match an accepted shape: samples/sample-dashboard-data.json"],
        )


class TestStageContextSections(unittest.TestCase):
    def test_missing_stage_sections_are_reported_per_section(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        (root / "CONTEXT.md").write_text("## Stage Router\n## Output Handoffs\n## Public Release Boundary\n")
        ctx = root / "00_START_HERE" / "CONTEXT.md"
        ctx.parent.mkdir(parents=True)
        ctx.write_text("## Inputs only\n")
        errs: list[str] = []
        vp.validate_icm_context(root, errs)
        self.assertEqual(
            errs,
            [
                "00_START_HERE/CONTEXT.md missing ## Process",
                "00_START_HERE/CONTEXT.md missing ## Outputs",
            ],
        )

    def test_root_context_phrases(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        errs: list[str] = []
        vp.validate_icm_context(root, errs)
        self.assertEqual(
            errs,
            [
                "CONTEXT.md missing ## Stage Router",
                "CONTEXT.md missing ## Output Handoffs",
                "CONTEXT.md missing ## Public Release Boundary",
            ],
        )


class TestFileHelpers(unittest.TestCase):
    def test_gitignore_patterns_strip_comments_blanks_and_trailing_slash(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        (root / ".gitignore").write_text("# comment\n\nbuild/\n.omx\nCHECKYOURSELF_*.generated.md\n")
        self.assertEqual(vp.gitignore_patterns(root), {"build", ".omx", "CHECKYOURSELF_*.generated.md"})

    def test_gitignore_missing_returns_empty(self):
        import tempfile

        self.assertEqual(vp.gitignore_patterns(Path(tempfile.mkdtemp())), set())

    def test_is_ignored_matches_path_and_basename(self):
        self.assertTrue(vp.is_ignored({"build"}, "build"))
        self.assertTrue(vp.is_ignored({"build"}, "sub/build"))
        self.assertFalse(vp.is_ignored({"build"}, "buildx"))

    def test_public_files_skips_symlinks_ignored_dirs_and_oversized(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        (root / "keep.txt").write_text("x")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "hidden.txt").write_text("x")
        (root / "link.txt").symlink_to(root / "keep.txt")
        big = root / "big.bin"
        big.write_bytes(b"0" * (vp.MAX_VALIDATED_FILE_BYTES + 1))
        files = vp.public_files(root)
        rels = [str(p.relative_to(root)) for p in files]
        self.assertIn("keep.txt", rels)
        self.assertNotIn("node_modules/hidden.txt", rels)
        self.assertNotIn("link.txt", rels)
        self.assertNotIn("big.bin", rels)

    def test_path_has_symlink_detection_and_outside_root(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        other = Path(tempfile.mkdtemp())
        self.assertTrue(vp._path_has_symlink(root, other / "x"))  # outside root
        inner = root / "dir"
        inner.mkdir()
        target = root / "real"
        target.write_text("x")
        (inner / "link").symlink_to(target)
        self.assertTrue(vp._path_has_symlink(root, inner / "link"))
        self.assertFalse(vp._path_has_symlink(root, target))

    def test_path_is_inside_rejects_outside(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        other = Path(tempfile.mkdtemp())
        self.assertTrue(vp._path_is_inside(root, root / "a"))
        self.assertFalse(vp._path_is_inside(root, other))

    def test_regular_in_root_file_rejects_symlink_and_directory(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        real = root / "real"
        real.write_text("x")
        self.assertTrue(vp._regular_in_root_file(root, real))
        (root / "link").symlink_to(real)
        self.assertFalse(vp._regular_in_root_file(root, root / "link"))
        self.assertFalse(vp._regular_in_root_file(root, root))

    def test_required_symlink_is_rejected(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        target = root / "elsewhere"
        target.write_text("x")
        for req in vp.REQUIRED:
            q = root / req
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_text("x")
        rel = vp.REQUIRED[0]
        (root / rel).unlink()
        (root / rel).symlink_to(target)
        errs: list[str] = []
        vp.validate_required(root, errs)
        self.assertEqual(errs, [f"required public path must be a regular in-root file: {rel}"])


class TestMain(unittest.TestCase):
    def test_main_reports_errors_and_returns_one(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        with mock.patch.object(sys, "argv", ["validate_public", str(root)]):
            import io as _io
            import contextlib

            out = _io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = vp.main()
        self.assertEqual(rc, 1)
        self.assertIn("Public validation failed:", out.getvalue())
        self.assertIn("missing required public file", out.getvalue())

    def test_main_defaults_to_cwd(self):
        import tempfile

        root = Path(tempfile.mkdtemp())
        cwd = os.getcwd()
        os.chdir(root)
        try:
            with mock.patch.object(sys, "argv", ["validate_public"]):
                rc = vp.main()
        finally:
            os.chdir(cwd)
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
