#!/usr/bin/env python3
"""Validate the public CheckYourself repository shape.

This script uses only the Python standard library so it can run locally or in
GitHub Actions without dependency installation.
"""
from __future__ import annotations

import json
import hashlib
import re
import sys
import urllib.parse
from pathlib import Path


REQUIRED = [
    ".github/workflows/validate.yml",
    ".gitignore",
    "CONTEXT.md",
    "README.md",
    "START_HERE.md",
    "PASTE_THIS_INTO_YOUR_AI.md",
    "AGENTS.md",
    "rules.md",
    "LICENSE",
    "NOTICE.md",
    "SECURITY.md",
    "SUPPORT.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    "00_START_HERE/CONTEXT.md",
    "01_PROJECT_CONTEXT/CONTEXT.md",
    "01_PROJECT_CONTEXT/output/.gitkeep",
    "02_RUN_DIAGNOSTIC/CONTEXT.md",
    "02_RUN_DIAGNOSTIC/coverage-matrix.md",
    "02_RUN_DIAGNOSTIC/output/.gitkeep",
    "02_RUN_DIAGNOSTIC/scoring-method.md",
    "03_GUIDED_FIX_MODE/CONTEXT.md",
    "03_GUIDED_FIX_MODE/output/.gitkeep",
    "04_LEARNING_PLAN/CONTEXT.md",
    "04_LEARNING_PLAN/output/.gitkeep",
    "05_OUTPUT_TEMPLATES/production-reality-report.md",
    "05_OUTPUT_TEMPLATES/bespoke-learning-plan.md",
    "10_DASHBOARD/CONTEXT.md",
    "10_DASHBOARD/README.md",
    "10_DASHBOARD/inline-dashboard.md",
    "10_DASHBOARD/dashboard-smoke-check.md",
    "10_DASHBOARD/dashboard-template.html",
    "10_DASHBOARD/output/.gitkeep",
    "90_ADVANCED/CONTEXT.md",
    "90_ADVANCED/README.md",
    "assets/checkyourself-user-workflow.png",
    "assets/checkyourself-user-workflow.svg",
    "checkyourself.manifest.json",
    "docs/cli.md",
    "docs/mcp.md",
    "docs/agent-access-cli-plan.md",
    "tools/checkyourself.py",
    "CHANGELOG.md",
    "samples/dogfood-fixture-broken-app.md",
    "schemas/dashboard-data.schema.json",
    "schemas/scan.schema.json",
    "schemas/coverage.schema.json",
    "schemas/score-result.schema.json",
    "schemas/backlog.schema.json",
    "schemas/next-batch.schema.json",
    "schemas/capabilities.schema.json",
]

PUBLIC_EXCLUDES = [
    "checkyourself-creator-launch-kit copy",
    ".omx",
    ".DS_Store",
]

STALE_PUBLIC_PHRASES = [
    "Dashboard=Yes",
    "dashboard:on",
    "01_PRODUCT_CHECKYOURSELF",
    "02_CREATOR_LAUNCH_KIT",
    "07_PUBLISHING",
    "scripts/validate_pack",
    "Skool post and YouTube",
    "advanced data-template path",
    "05_OUTPUT_TEMPLATES/checkyourself-dashboard.html",
]

HARDCODED_SECONDARY_LANGUAGE_PHRASES = [
    "Saltar al tablero",
    "Puntaje",
    "Confianza",
    "Próxima decisión",
    "No lanzar",
    "No Lanzar",
    "Cobertura completa",
    "Lista completa",
    "Prioridades de aprendizaje",
    "Project / Proyecto",
    "Score / Puntaje",
    "Surface / Superficie",
    "Evidence / Evidencia",
]

CANONICAL_LANGUAGE_TEMPLATES = [
    "10_DASHBOARD/dashboard-template.html",
    "10_DASHBOARD/inline-dashboard.md",
]

AUTO_BILINGUAL_PHRASES = [
    "make learning/dashboard outputs bilingual",
    "make the plan bilingual",
    "bilingual labels/content when the user or codebase is not English-only",
    "bilingual content appears when the user or project language is not English-only",
    "Include the user's language when the prompt or codebase is not English-only",
    "bilingual labels/content when language signals call for it",
]

NON_DOGFOOD_EXAMPLE_DATA = [
    "05_OUTPUT_TEMPLATES/dashboard-data.example.json",
    "samples/sample-dashboard-data.json",
]

STAGE_CONTEXTS = [
    "00_START_HERE/CONTEXT.md",
    "01_PROJECT_CONTEXT/CONTEXT.md",
    "02_RUN_DIAGNOSTIC/CONTEXT.md",
    "03_GUIDED_FIX_MODE/CONTEXT.md",
    "04_LEARNING_PLAN/CONTEXT.md",
    "10_DASHBOARD/CONTEXT.md",
    "90_ADVANCED/CONTEXT.md",
]


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def gitignore_patterns(root: Path) -> set[str]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return set()
    return {
        line.strip().rstrip("/")
        for line in text(gitignore).splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def is_ignored(patterns: set[str], rel: str) -> bool:
    clean = rel.rstrip("/")
    return clean in patterns or Path(clean).name in patterns


def public_files(root: Path) -> list[Path]:
    ignored_roots = {".git", ".omx", "checkyourself-creator-launch-kit copy"}
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if rel_parts and rel_parts[0] in ignored_roots:
            continue
        files.append(path)
    return sorted(files)


def validate_required(root: Path, errors: list[str]) -> None:
    for rel in REQUIRED:
        if not (root / rel).exists():
            errors.append(f"missing required public file: {rel}")


def validate_release_boundary(root: Path, errors: list[str]) -> None:
    patterns = gitignore_patterns(root)
    for rel in PUBLIC_EXCLUDES:
        if not is_ignored(patterns, rel):
            errors.append(f"public exclude is not listed in .gitignore: {rel}")
        if (root / rel).exists() and not is_ignored(patterns, rel):
            errors.append(f"private/local path exists and is not ignored: {rel}")

    generated_patterns = {"CHECKYOURSELF_PROJECT_CONTEXT.generated.md", "CHECKYOURSELF_*.generated.md"}
    if not generated_patterns & patterns:
        errors.append("scanner-generated project context output is not ignored")


def validate_icm_context(root: Path, errors: list[str]) -> None:
    root_context = text(root / "CONTEXT.md") if (root / "CONTEXT.md").exists() else ""
    for phrase in ["## Stage Router", "## Output Handoffs", "## Public Release Boundary"]:
        if phrase not in root_context:
            errors.append(f"CONTEXT.md missing {phrase}")

    for rel in STAGE_CONTEXTS:
        path = root / rel
        if not path.exists():
            continue
        body = text(path)
        for section in ["## Inputs", "## Process", "## Outputs"]:
            if section not in body:
                errors.append(f"{rel} missing {section}")


def validate_json(root: Path, errors: list[str]) -> None:
    for path in public_files(root):
        if path.suffix != ".json":
            continue
        try:
            json.loads(text(path))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON: {path.relative_to(root)} ({exc})")

    for rel in ["samples/sample-dashboard-data.json", "05_OUTPUT_TEMPLATES/dashboard-data.example.json"]:
        path = root / rel
        if not path.exists():
            continue
        data = json.loads(text(path))
        compact_shape = {"app_name", "score", "confidence", "counts", "coverage", "findings"}
        template_shape = {"project", "score", "counts", "coverage", "backlog", "learning_plan"}
        if not (compact_shape <= data.keys() or template_shape <= data.keys()):
            errors.append(f"dashboard data example does not match an accepted shape: {rel}")


def validate_manifest(root: Path, errors: list[str]) -> None:
    manifest_path = root / "checkyourself.manifest.json"
    changelog_path = root / "CHANGELOG.md"
    if not manifest_path.exists() or not changelog_path.exists():
        return

    manifest = json.loads(text(manifest_path))
    version = manifest.get("version")
    if version and f"## {version}" not in text(changelog_path):
        errors.append(f"manifest version {version} is missing from CHANGELOG.md")

    for name, rel in manifest.get("entrypoints", {}).items():
        if not (root / rel).exists():
            errors.append(f"manifest entrypoint is missing: {name} -> {rel}")

    modes = manifest.get("modes", [])
    if len(modes) != len(set(modes)):
        errors.append("manifest modes contain duplicates")

    dashboard_modes = [mode for mode in modes if "dashboard" in mode]
    if len(dashboard_modes) > 2:
        errors.append("manifest modes contain too many dashboard variants")

    optional_dashboard = manifest.get("optional_dashboard", {})
    if optional_dashboard.get("template") != "10_DASHBOARD/dashboard-template.html":
        errors.append("manifest optional dashboard template must be the canonical HTML/CSS dashboard")
    if optional_dashboard.get("inline_fallback") != "10_DASHBOARD/inline-dashboard.md":
        errors.append("manifest optional dashboard inline fallback is missing or wrong")
    if "advanced_data_template" in optional_dashboard:
        errors.append("manifest optional dashboard must not advertise a second JS/data-template dashboard")
    if "html_dashboard_template" in manifest:
        errors.append("manifest must use optional_dashboard.template as the only rich dashboard template")


def validate_markdown_links(root: Path, errors: list[str]) -> None:
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in public_files(root):
        if path.suffix != ".md":
            continue
        body = text(path)
        for match in link_re.finditer(body):
            raw = match.group(1)
            link = raw.split("#")[0].strip()
            if not link or re.match(r"^[a-z]+:", link) or link.startswith("mailto:"):
                continue
            target = (path.parent / urllib.parse.unquote(link)).resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                ok = False
            else:
                ok = target.exists()
            if not ok:
                line = body[: match.start()].count("\n") + 1
                errors.append(f"broken local markdown link: {path.relative_to(root)}:{line} -> {raw}")


def validate_assets(root: Path, errors: list[str]) -> None:
    assets = root / "assets"
    if not assets.exists():
        return

    by_hash: dict[str, list[str]] = {}
    for path in sorted(assets.iterdir()):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        by_hash.setdefault(digest, []).append(str(path.relative_to(root)))

    for paths in by_hash.values():
        if len(paths) > 1:
            errors.append(f"duplicate asset files: {', '.join(paths)}")


def validate_doc_drift(root: Path, errors: list[str]) -> None:
    canonical = root / "docs/token-efficiency-and-context-control.md"
    shortcut = root / "docs/token-efficiency.md"
    if canonical.exists() and shortcut.exists() and canonical.read_bytes() == shortcut.read_bytes():
        errors.append("token-efficiency docs are exact duplicates")


def validate_public_text(root: Path, errors: list[str]) -> None:
    for path in public_files(root):
        if path.suffix.lower() not in {".md", ".json", ".html", ".txt", ".yml", ".yaml"}:
            continue
        body = text(path)
        for phrase in STALE_PUBLIC_PHRASES:
            if phrase in body:
                errors.append(f"stale public phrase in {path.relative_to(root)}: {phrase}")

    dashboard_context = text(root / "10_DASHBOARD/CONTEXT.md") if (root / "10_DASHBOARD/CONTEXT.md").exists() else ""
    if "canonical HTML/CSS dashboard" not in dashboard_context:
        errors.append("10_DASHBOARD/CONTEXT.md must identify the canonical HTML/CSS dashboard path")
    if "inline Markdown fallback" not in dashboard_context:
        errors.append("10_DASHBOARD/CONTEXT.md must identify the inline Markdown fallback")
    dashboard_prompt = text(root / "05_OUTPUT_TEMPLATES/dashboard-prompt.md") if (root / "05_OUTPUT_TEMPLATES/dashboard-prompt.md").exists() else ""
    if "single canonical HTML/CSS dashboard" not in dashboard_prompt:
        errors.append("05_OUTPUT_TEMPLATES/dashboard-prompt.md must identify the single canonical dashboard")
    if "inline Markdown fallback" not in dashboard_prompt:
        errors.append("05_OUTPUT_TEMPLATES/dashboard-prompt.md must identify the inline Markdown fallback")

    for rel in CANONICAL_LANGUAGE_TEMPLATES:
        path = root / rel
        if not path.exists():
            continue
        body = text(path)
        for phrase in HARDCODED_SECONDARY_LANGUAGE_PHRASES:
            if phrase in body:
                errors.append(f"canonical dashboard template hardcodes a secondary language in {rel}: {phrase}")

    agent_instructions = text(root / "AGENTS.md") if (root / "AGENTS.md").exists() else ""
    if "candidate second language" not in agent_instructions:
        errors.append("AGENTS.md must require runtime candidate second-language detection")
    if "ask the user" not in agent_instructions:
        errors.append("AGENTS.md must require asking before using an inferred second language")

    learning_template = text(root / "05_OUTPUT_TEMPLATES/bespoke-learning-plan.md") if (root / "05_OUTPUT_TEMPLATES/bespoke-learning-plan.md").exists() else ""
    for phrase in ["why_this_source_is_trusted", "authority_level", "checked_at"]:
        if phrase not in learning_template:
            errors.append(f"bespoke learning plan template missing source reliability field: {phrase}")

    for path in public_files(root):
        rel = str(path.relative_to(root))
        if rel.startswith(("04_LEARNING_PLAN/output/", "10_DASHBOARD/output/")):
            continue
        if path.suffix.lower() not in {".md", ".json", ".html", ".txt"}:
            continue
        body = text(path)
        for phrase in AUTO_BILINGUAL_PHRASES:
            if phrase in body:
                errors.append(f"auto-bilingual instruction must ask for confirmation first in {rel}: {phrase}")

    for rel in NON_DOGFOOD_EXAMPLE_DATA:
        path = root / rel
        if not path.exists():
            continue
        body = text(path)
        for phrase in ["plain_other_language", "do_this_next_other_language"]:
            if phrase in body:
                errors.append(f"non-dogfood example must use runtime-neutral secondary-language fields in {rel}: {phrase}")


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    root = root.resolve()
    errors: list[str] = []

    validate_required(root, errors)
    validate_release_boundary(root, errors)
    validate_icm_context(root, errors)
    validate_json(root, errors)
    validate_manifest(root, errors)
    validate_markdown_links(root, errors)
    validate_assets(root, errors)
    validate_doc_drift(root, errors)
    validate_public_text(root, errors)

    if errors:
        print("Public validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OK: public CheckYourself validation passed")
    print(f"Path: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
