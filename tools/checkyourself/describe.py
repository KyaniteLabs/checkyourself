"""Capability manifest, schema registry, and bundled schema loading."""

from __future__ import annotations

from typing import Dict
from .constants import (
    CAPABILITIES_SCHEMA_ID,
    CHALLENGE_RESULT_SCHEMA_ID,
    COVERAGE_SCHEMA_ID,
    COVERAGE_SURFACES,
    MCP_PROTOCOL_VERSION,
    PUBLIC_REPO_SCOPE_GUARDRAILS,
    RECEIPT_SCHEMA_ID,
    ROOT,
    SCAN_SCHEMA_ID,
    SCHEMA_DIR,
    SCORE_CATEGORIES,
    SCORE_SCHEMA_ID,
    SEVERITY_PENALTIES,
    TOOL_NAME,
    VERIFICATION_ARTIFACT_REGISTRY,
)
from .errors import CliError
from .jsonlite import strict_json_loads
from .util import now_iso


def describe_capabilities() -> dict:
    version = read_manifest_version()
    commands = [
        ("describe", "Emit this machine-readable capability manifest.", {}, CAPABILITIES_SCHEMA_ID),
        (
            "scan",
            "Detect stack signals and deterministic local findings.",
            {"project": "path", "deep": "optional boolean"},
            SCAN_SCHEMA_ID,
        ),
        (
            "diagnostic",
            "Alias for scan; use it when docs or agents ask to run a diagnostic.",
            {"project": "path", "deep": "optional boolean"},
            SCAN_SCHEMA_ID,
        ),
        (
            "coverage --emit",
            "Write the 20-surface coverage skeleton by default, or print JSON with --format json.",
            {"project": "optional string"},
            COVERAGE_SCHEMA_ID,
        ),
        (
            "coverage --check",
            "Validate coverage completeness.",
            {"file": "coverage json path"},
            "checkyourself-coverage-check/1",
        ),
        (
            "challenge",
            "Execute committed per-surface commands and mint executed receipts from verifier-captured output.",
            {"project": "optional path", "surface": "optional canonical surface ID"},
            CHALLENGE_RESULT_SCHEMA_ID,
        ),
        (
            "receipt",
            "Issue one verifier-hashed receipt only for a registered, surface-specific verification artifact.",
            {
                "reference": "registered artifact path",
                "surface_id": "canonical surface ID",
                "source_revision": "revision",
                "command": "command recorded at issuance",
                "claim": "claim",
                "result": "observed result",
                "source_state": "source/environment state",
                "subject_digest": "optional content hash assertion",
            },
            RECEIPT_SCHEMA_ID,
        ),
        (
            "score",
            "Compute a deterministic Production Reality Score from findings and optional verifier-checked coverage; opt"
            "ionally record a completion claim without executing a challenge runner.",
            {
                "findings": "json path",
                "coverage": "optional json path",
                "claim": "optional accepted completion claim",
                "history": "optional path",
            },
            SCORE_SCHEMA_ID,
        ),
        (
            "backlog",
            "Rank remediation backlog and return a highest-severity batch; safety analysis is not performed.",
            {"findings": "json path"},
            "checkyourself-backlog/1",
        ),
        (
            "next",
            "Return the next highest-severity unresolved approval batch; safety analysis is not performed.",
            {"findings": "json path"},
            "checkyourself-next-batch/1",
        ),
        (
            "diff",
            "Compare two findings artifacts, report identity-aware transitions, and gate newly open, reopened, or escal"
            "ated P0/P1 findings.",
            {"old": "json path", "new": "json path"},
            "checkyourself-diff/1",
        ),
        (
            "validate",
            "Validate an artifact against a bundled JSON schema subset.",
            {"kind": "schema kind", "file": "json path"},
            "checkyourself-validation/1",
        ),
        ("schema", "Print a bundled schema by name.", {"name": "schema name"}, "json-schema"),
        (
            "init",
            "Create starter generated coverage/context files without overwriting by default.",
            {"project": "path"},
            "checkyourself-init/1",
        ),
        ("mcp", "Run the stdio MCP server that exposes the same verbs as native tools.", {}, "mcp-stdio"),
    ]
    return {
        "tool": TOOL_NAME,
        "schema": CAPABILITIES_SCHEMA_ID,
        "version": version,
        "generated_at": now_iso(),
        "commands": [
            {"name": name, "summary": summary, "inputs": inputs, "output_schema": output}
            for name, summary, inputs, output in commands
        ],
        "public_repo_scope_guardrails": PUBLIC_REPO_SCOPE_GUARDRAILS,
        "coverage_surfaces": [
            {"id": sid, "surface": surface, "category": category} for sid, surface, category in COVERAGE_SURFACES
        ],
        "verification_artifact_registry": VERIFICATION_ARTIFACT_REGISTRY,
        "scoring": {
            "categories": [
                {"id": cid, "category": name, "weight": weight} for cid, (name, weight) in SCORE_CATEGORIES.items()
            ],
            "severity_penalties": SEVERITY_PENALTIES,
            "caps": [
                {"cap": 49, "condition": "any unresolved P0"},
                {"cap": 74, "condition": "any unresolved P1"},
                {"cap": 84, "condition": "missing evidence in C1/C2/C3 (applies in every score mode)"},
                {
                    "cap": 90,
                    "condition": "score above 90 without evidence for key launch gates (applies in every score mode)",
                },
            ],
            "score_modes": [
                {"mode": "coverage-backed", "trigger": "a coverage artifact was supplied", "max_confidence": "high"},
                {
                    "mode": "scan-derived-estimate",
                    "trigger": "findings input is a checkyourself-scan/1 object and no coverage supplied",
                    "max_confidence": "low",
                },
                {
                    "mode": "finding-only-estimate",
                    "trigger": "plain findings without scan context or coverage",
                    "max_confidence": "low",
                },
            ],
            "confidence_labels": ["high", "medium", "low"],
        },
        "schemas": sorted(schema_registry().keys()),
        "exit_codes": {"0": "success", "1": "gating finding or validation failure", "2": "usage/input error"},
        "mcp": {
            "transport": "stdio",
            "protocol_version": MCP_PROTOCOL_VERSION,
            "command": "python3 tools/checkyourself.py mcp",
        },
    }


def read_manifest_version() -> str:
    manifest = ROOT / "checkyourself.manifest.json"
    try:
        data = strict_json_loads(manifest.read_text(encoding="utf-8"))
        return str(data.get("version") or "unknown")
    except Exception:
        return "unknown"


def schema_registry() -> Dict[str, str]:
    return {
        "report": "checkyourself-report.schema.json",
        "dashboard": "dashboard-data.schema.json",
        "dashboard-data": "dashboard-data.schema.json",
        "learning-plan": "learning-plan.schema.json",
        "scan": "scan.schema.json",
        "coverage": "coverage.schema.json",
        "challenges": "challenges.schema.json",
        "challenge": "challenge-result.schema.json",
        "receipt": "receipt.schema.json",
        "score": "score-result.schema.json",
        "backlog": "backlog.schema.json",
        "next": "next-batch.schema.json",
        "diff": "diff.schema.json",
        "capabilities": "capabilities.schema.json",
    }


def load_schema(name: str) -> dict:
    registry = schema_registry()
    if name not in registry:
        raise CliError(f"unknown schema kind: {name}. Known: {', '.join(sorted(registry))}")
    path = SCHEMA_DIR / registry[name]
    if not path.exists():
        raise CliError(f"schema file missing: {path}")
    try:
        return strict_json_loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeError) as exc:
        raise CliError(f"schema file could not be parsed: {path}: {exc}") from exc
