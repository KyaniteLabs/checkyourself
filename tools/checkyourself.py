#!/usr/bin/env python3
"""CheckYourself local CLI and thin MCP wrapper.

CheckYourself is primarily a model-agnostic audit workspace that an AI assistant
loads as operating context. This command is the deterministic machine interface:
it discovers cheap local facts, emits schemas, validates artifacts, scores
finding/coverage JSON, ranks the backlog, and exposes the same verbs through a
small MCP stdio server.

Standard library only. No network. No telemetry. Secret values are never printed.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


TOOL_NAME = "checkyourself-cli"
SCAN_SCHEMA_ID = "checkyourself-scan/1"
COVERAGE_SCHEMA_ID = "checkyourself-coverage/1"
SCORE_SCHEMA_ID = "checkyourself-score/1"
CAPABILITIES_SCHEMA_ID = "checkyourself-capabilities/1"
RECEIPT_SCHEMA_ID = "checkyourself-receipt/1"
RECEIPT_ISSUER = "checkyourself-verifier/1"
MCP_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_MCP_PROTOCOLS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
PUBLIC_REPO_SCOPE_GUARDRAILS = [
    "Name the exact GitHub owner namespace(s) before claiming public repository coverage.",
    "Report the repository count and verification timestamp for each owner namespace.",
    "State whether forks, archived repositories, and externally owned repositories were excluded.",
    "Do not infer ownership from linked repositories, examples, forks, or upstream references.",
    "List the live evidence surfaces checked, including findings, open PRs, dependency alerts, and branch status.",
    "For dependency or security closure, verify the default-branch alert state after merge; local scans and PR checks are not enough.",
    "For a 100% status claim, require scanner findings, default-branch CI, dependency/security alerts, and git branch state to all agree.",
]

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
DEFAULT_COVERAGE_PATH = "CHECKYOURSELF_COVERAGE.generated.json"
DEFAULT_SCORE_HISTORY_PATH = ".checkyourself-score-history.json"
CONFIG_NAMES = (".checkyourself.yml", ".checkyourself.yaml", ".checkyourself.json")

IGNORED_DIRS = {
    ".git", "node_modules", ".next", "dist", "build", "coverage", ".venv", "venv",
    "__pycache__", ".turbo", ".cache", "target", ".idea", ".vscode", ".pytest_cache",
    ".svelte-kit", "out", ".output", "vendor",
}

TEXT_EXTENSIONS = {
    ".js", ".jsx", ".ts", ".tsx", ".py", ".rb", ".go", ".java", ".cs", ".php",
    ".env", ".yaml", ".yml", ".json", ".toml", ".sh", ".rs", ".md", ".txt",
    ".tf", ".tfvars", ".properties", ".ini", ".cfg", ".conf", ".xml",
    ".vue", ".svelte", ".kt", ".swift", ".dart", ".gradle",
}

CODE_EXTENSIONS = {
    ".js", ".jsx", ".ts", ".tsx", ".py", ".rb", ".go", ".java", ".cs", ".php",
    ".vue", ".svelte", ".kt", ".swift", ".dart",
}

CONFIG_EXTENSIONS = {".env", ".cfg", ".ini", ".conf", ".properties", ".toml", ".yaml", ".yml"}
# These files carry configuration even though their names have no useful
# suffix. They must receive the same content checks as extension-based config.
EXTENSIONLESS_CONFIG_NAMES = {"dockerfile", "makefile", "jenkinsfile"}

# One credential-name token list feeds both detection and redaction so the two
# regexes cannot drift apart. The trailing (?![a-z]) rejects identifier
# continuations such as `tokenizer` or `passwordResetUrl` (under re.I it
# rejects any following ASCII letter) while still matching `feedbackToken:`.
_CRED_NAME_TOKENS = (
    r"api[_-]?key|api[_-]?token|access[_-]?key|access[_-]?token|auth[_-]?token|"
    r"refresh[_-]?token|client[_-]?secret|secret[_-]?key|private[_-]?key|"
    r"secret|token|password|passwd|credential"
)
SECRET_NAME_RE = re.compile(rf"(?i)({_CRED_NAME_TOKENS})(?![a-z])")
SECRET_VALUE_RE = re.compile(
    rf"(?i)({_CRED_NAME_TOKENS})(?![a-z])\s*['\"]?\s*[:=]\s*['\"]?"
    r"([A-Za-z0-9_\-\./+=]{16,})"
)
SECRET_SHAPE_RES = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]

DEBUG_FLAG_RES = [
    re.compile(r"(?m)^\s*(?:DEBUG|FLASK_DEBUG|APP_DEBUG|DJANGO_DEBUG)\s*=\s*(?:True|true|1)\s*$"),
    re.compile(r"\bapp\.run\([^)\n]*debug\s*=\s*True"),
    re.compile(r"\bapp\.debug\s*=\s*True"),
]

CORS_WILDCARD_RES = [
    re.compile(r"(?i)['\"]?access-control-allow-origin['\"]?\s*[:=,]\s*['\"]\*['\"]"),
    re.compile(r"(?i)\borigin\s*:\s*['\"]\*['\"]"),
    re.compile(r"(?i)\ballow_origins\s*=\s*\[?\s*['\"]\*['\"]"),
    re.compile(r"\bCORS_ORIGIN_ALLOW_ALL\s*=\s*True\b"),
]

DANGEROUS_SINK_RES = [
    (re.compile(r"(?<![\w.])eval\s*\("), "eval() on dynamic input"),
    (re.compile(r"\bpickle\.loads?\s*\("), "pickle deserialization of untrusted data"),
    (re.compile(r"\byaml\.load\s*\((?![^)\n]*Loader)"), "yaml.load without an explicit safe Loader"),
    (re.compile(r"\bdangerouslySetInnerHTML\b"), "dangerouslySetInnerHTML"),
    (re.compile(r"\bverify\s*=\s*False\b"), "TLS verification disabled (verify=False)"),
    (re.compile(r"\brejectUnauthorized\s*:\s*false\b"), "TLS verification disabled (rejectUnauthorized: false)"),
    (re.compile(r"NODE_TLS_REJECT_UNAUTHORIZED\W{0,4}0"), "TLS verification disabled (NODE_TLS_REJECT_UNAUTHORIZED=0)"),
]

DEFAULT_CRED_RE = re.compile(
    r"(?im)^\s*['\"]?[A-Z0-9_]*(?:PASSWORD|PASSWD|PWD)['\"]?\s*[:=]\s*['\"]?"
    r"(admin|password|passw0rd|changeme|change_me|123456|12345678|root|letmein|secret|"
    r"postgres|mysql|mariadb|redis|guest|test|default)['\"]?\s*,?\s*$"
)
DEFAULT_CRED_URL_RE = re.compile(r"//(?:root:root|admin:admin|postgres:postgres|guest:guest|user:user)@")

SOURCEMAP_RES = [
    re.compile(r"\bproductionBrowserSourceMaps\s*:\s*true\b"),
    re.compile(r"\bdevtool\s*:\s*['\"]source-map['\"]"),
]

LOCKFILE_NAMES = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock", "npm-shrinkwrap.json")

LLM_DEPENDENCY_LABELS = {"OpenAI API", "Anthropic SDK", "LangChain", "LlamaIndex"}

TEST_PATH_MARKERS = ("test", "tests", "spec", "specs", "__tests__", "fixture", "fixtures",
                     "mock", "mocks", "example", "examples", "sample", "samples", "doc", "docs",
                     "__mocks__", "e2e", "stories")
CONTEXT_ONLY_PATH_MARKERS = TEST_PATH_MARKERS + ("audit", "audits", "snapshot", "snapshots")

STACK_FILES = {
    "package.json": "JavaScript/TypeScript project",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "Yarn",
    "package-lock.json": "npm",
    "bun.lockb": "Bun",
    "pyproject.toml": "Python project",
    "requirements.txt": "Python requirements",
    "Pipfile": "Python (pipenv)",
    "go.mod": "Go project",
    "Cargo.toml": "Rust project",
    "Gemfile": "Ruby project",
    "composer.json": "PHP project",
    "pom.xml": "Java/Maven project",
    "build.gradle": "Java/Gradle project",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "compose.yml": "Docker Compose",
    "vercel.json": "Vercel",
    "netlify.toml": "Netlify",
    "fly.toml": "Fly.io",
    "render.yaml": "Render",
    "railway.json": "Railway",
    "supabase/config.toml": "Supabase",
    "prisma/schema.prisma": "Prisma",
    "drizzle.config.ts": "Drizzle ORM",
    ".github/workflows": "GitHub Actions",
    ".gitlab-ci.yml": "GitLab CI",
    "Makefile": "Makefile",
}

DEPENDENCY_HINTS = {
    "next": "Next.js", "react": "React", "vue": "Vue", "svelte": "Svelte",
    "@angular/core": "Angular", "express": "Express", "fastify": "Fastify",
    "hono": "Hono", "@nestjs/core": "NestJS", "django": "Django", "flask": "Flask",
    "fastapi": "FastAPI", "@supabase/supabase-js": "Supabase client",
    "supabase": "Supabase", "prisma": "Prisma", "drizzle-orm": "Drizzle ORM",
    "mongoose": "MongoDB/Mongoose", "pg": "Postgres client", "psycopg2": "Postgres client",
    "mysql2": "MySQL client", "sqlite3": "SQLite", "better-sqlite3": "SQLite",
    "next-auth": "NextAuth/Auth.js", "@auth/core": "Auth.js", "@clerk/nextjs": "Clerk",
    "firebase": "Firebase", "jsonwebtoken": "JWT", "passport": "Passport",
    "stripe": "Stripe/payments", "openai": "OpenAI API", "@anthropic-ai/sdk": "Anthropic SDK",
    "anthropic": "Anthropic SDK", "langchain": "LangChain", "llamaindex": "LlamaIndex",
    "@pinecone-database/pinecone": "Pinecone", "chromadb": "ChromaDB", "weaviate": "Weaviate",
    "jest": "Jest", "vitest": "Vitest", "playwright": "Playwright", "cypress": "Cypress",
    "pytest": "pytest",
}

RISK_PATH_HINTS = [
    ("api", "API routes or handlers"), ("routes", "Routes"), ("middleware", "Middleware"),
    ("auth", "Authentication/authorization"), ("login", "Authentication"),
    ("admin", "Admin surface"), ("upload", "File upload"), ("payment", "Payments"),
    ("stripe", "Payments"), ("webhook", "Webhooks"), ("sql", "Raw SQL or migrations"),
    ("migration", "Database migrations"), ("rag", "RAG/AI"),
    ("embedding", "Embeddings/vector search"), ("agent", "AI agents"),
]

ENV_EXAMPLE_NAMES = {".env.example", ".env.sample", ".env.template", "env.example"}
SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
# Workflow disposition and residual risk are deliberately separate.  A ticket
# can be deferred or accepted while the underlying exposure remains open.
WORKFLOW_DISPOSITIONS = {"fixed", "accepted-risk", "deferred", "not-applicable", "suppressed"}
RESOLVED_STATUSES = {"fixed", "not-applicable"}

COVERAGE_SURFACES = [
    ("S01", "Product purpose, users, and harm model", "context"),
    ("S02", "Stack, architecture, and dependency map", "context"),
    ("S03", "Frontend UX, accessibility, and client safety", "C9"),
    ("S04", "API/backend behavior, validation, uploads, and webhooks", "C4"),
    ("S05", "Auth, permissions, sessions, roles, and admin paths", "C2"),
    ("S06", "Data storage, migrations, backups, and retention", "C1"),
    ("S07", "User, tenant, and role isolation", "C1"),
    ("S08", "Secrets, environment, runtime configuration", "C3"),
    ("S09", "Security and threat model", "C4"),
    ("S10", "Privacy, consent, compliance, and data governance", "C1"),
    ("S11", "Tests, quality gates, and regression coverage", "C5"),
    ("S12", "CI/CD and supply chain", "C6"),
    ("S13", "Hosting, deployment, release, and rollback", "C6"),
    ("S14", "Cloud infrastructure and IaC", "C6"),
    ("S15", "Performance, caching, and rate limits", "C8"),
    ("S16", "Scaling, load, and resilience", "C8"),
    ("S17", "Observability, logs, errors, and incident response", "C7"),
    ("S18", "Availability, recovery, and continuity", "C1"),
    ("S19", "AI/RAG/agent governance", "C10"),
    ("S20", "Learning needs and remediation history", "learning"),
]

# A receipt's cryptographic subject must also be a verifier artifact that is
# relevant to the surface it claims to prove.  Keep the default contract
# intentionally narrow: one per-surface directory, JSON records only, and a
# small common record shape that carries the surface identity and provenance.
# Projects can override individual entries in .checkyourself.json when their
# verifier emits artifacts elsewhere or uses a different record kind.
DEFAULT_VERIFICATION_ARTIFACT_REGISTRY = {
    sid: {
        "path_roots": [f"coverage/verification/{sid}"],
        "path_patterns": ["*.json"],
        "expected_kind": "surface-verification-record",
        "required_fields": ["surface_id", "kind", "source_revision", "command", "result"],
        "required_values": {"surface_id": sid, "kind": "surface-verification-record"},
    }
    for sid, _surface, _category in COVERAGE_SURFACES
}
# Public name for callers that need to inspect the shipped default contract.
VERIFICATION_ARTIFACT_REGISTRY = DEFAULT_VERIFICATION_ARTIFACT_REGISTRY

SCORE_CATEGORIES = {
    "C1": ("Data, privacy, tenant/user isolation", 18),
    "C2": ("Auth, permissions, session safety", 14),
    "C3": ("Secrets, environment, runtime config", 10),
    "C4": ("API, validation, uploads, business logic", 10),
    "C5": ("Testing and quality gates", 10),
    "C6": ("Deployment, release, rollback, CI/CD", 8),
    "C7": ("Observability, logs, errors, incident response", 8),
    "C8": ("Performance, scaling, caching, rate limits", 8),
    "C9": ("Frontend UX, accessibility, client safety", 8),
    "C10": ("AI/RAG/agent governance", 6),
}

SEVERITY_PENALTIES = {"P0": 1.0, "P1": 0.60, "P2": 0.25, "P3": 0.10}
CRITICAL_CATEGORIES = {"C1", "C2", "C3"}
HIGH_SCORE_GATE_CATEGORIES = {"C1", "C2", "C3", "C5", "C6", "C7"}
VALID_COVERAGE_STATUSES = {"Pass", "Finding", "Unknown", "NotApplicable"}
RECEIPT_BINDING_FIELDS = (
    "reference",
    "sha256",
    "subject_digest",
    "surface_id",
    "source_revision",
    "command",
    "claim",
    "origin",
    "source_state",
    "result",
    "issuer",
    "issued_at",
)
_NO_COVERAGE = object()
EVIDENCE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<path>(?:[A-Za-z0-9_./~\\-]+/)?[A-Za-z0-9_.~-]+\.[A-Za-z0-9_-]+)(?::\d+(?::\d+)?)?"
)


class CliError(Exception):
    """User-facing CLI error with a stable exit code."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


class Finding:
    def __init__(
        self,
        fid: str,
        severity: str,
        title: str,
        detail: str,
        evidence: List[str],
        category: str = "C3",
        recommended_fix: str = "",
        status: str = "open",
    ):
        self.id = fid
        self.severity = severity
        self.title = title
        self.detail = detail
        self.evidence = evidence
        self.category = category
        self.recommended_fix = recommended_fix
        self.status = status

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "detail": self.detail,
            "finding": self.title,
            "plain_english_risk": self.detail,
            "evidence": self.evidence,
            "recommended_fix": self.recommended_fix,
            "status": self.status,
        }


def now_iso() -> str:
    # UTC so history entries from laptops and CI machines stay comparable.
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_text(path: Path, max_chars: int = 200_000) -> str:
    try:
        # Never read through symlinks: an adversarial project could point a
        # source-looking file at credentials outside the scanned tree.
        if path.is_symlink():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def read_text_with_status(path: Path, max_chars: int) -> Tuple[str, bool, bool]:
    """Read bounded text and distinguish truncation from an unreadable file."""
    try:
        if path.is_symlink():
            return "", False, True
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read(max_chars + 1)
        return text[:max_chars], len(text) > max_chars, False
    except OSError:
        return "", False, True


def looks_binary(text: str) -> bool:
    return "\x00" in text[:2048]


def redact_sensitive_text(value: str) -> str:
    """Redact credential-shaped substrings before they can reach generated output."""
    redacted = value
    redacted = SECRET_VALUE_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", redacted)
    for pattern in SECRET_SHAPE_RES:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def compact_context(line: str, limit: int = 140) -> str:
    context = " ".join(redact_sensitive_text(line).strip().split())
    if len(context) > limit:
        return context[: limit - 3] + "..."
    return context


def secret_evidence(
    rp: str,
    line_no: int,
    tag: str,
    match_type: str,
    confidence: str,
    line: str,
) -> str:
    return (
        f"{rp}:{line_no} ({tag}; matched: {match_type}; "
        f"confidence: {confidence}; context: \"{compact_context(line)}\")"
    )


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [str(parse_scalar(part)) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value


def parse_minimal_yaml_suppressions(text: str) -> List[dict]:
    suppressions: List[dict] = []
    current: Optional[dict] = None
    current_item_indent: Optional[int] = None
    current_list_key: Optional[str] = None
    in_suppress = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("suppress:"):
            value = stripped.split(":", 1)[1].strip()
            if value not in {"", "[]"}:
                raise ValueError("suppress must be a YAML list")
            in_suppress = True
            continue
        if in_suppress and not raw_line[:1].isspace() and not stripped.startswith("- "):
            # A new zero-indent top-level key ends the suppress block.
            if current:
                suppressions.append(current)
                current = None
            current_list_key = None
            in_suppress = False
        if not in_suppress:
            continue
        if stripped.startswith("- "):
            indent = len(raw_line) - len(raw_line.lstrip())
            if current is not None and current_list_key and current_item_indent is not None and indent > current_item_indent:
                current[current_list_key].append(parse_scalar(stripped[2:].strip()))
                continue
            if current:
                suppressions.append(current)
            current = {}
            current_item_indent = indent
            current_list_key = None
            stripped = stripped[2:].strip()
            if stripped and ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key.strip()] = parse_scalar(value)
            elif stripped:
                raise ValueError("suppression list items must be mappings")
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            current[key] = [] if not value.strip() else parse_scalar(value)
            current_list_key = key if not value.strip() else None

    if current:
        suppressions.append(current)
    return suppressions


def validate_suppressions_config(data: Any, name: str) -> dict:
    if not isinstance(data, dict):
        return {"suppress": [], "config_error": f"{name} must contain a JSON/YAML object"}
    suppressions = data.get("suppress", [])
    if not isinstance(suppressions, list):
        return {"suppress": [], "config_error": f"{name} suppress must be a list"}
    for index, suppression in enumerate(suppressions):
        if not isinstance(suppression, dict):
            return {"suppress": [], "config_error": f"{name} suppression {index} must be an object"}
        for key in ("id", "reason", "reviewed_by", "reviewed_at"):
            if key in suppression and not isinstance(suppression[key], str):
                return {"suppress": [], "config_error": f"{name} suppression {index} field {key} must be a string"}
        for key in ("files", "paths"):
            if key not in suppression:
                continue
            value = suppression[key]
            if isinstance(value, str):
                continue
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                return {"suppress": [], "config_error": f"{name} suppression {index} field {key} must be a string or list of strings"}
        has_id = isinstance(suppression.get("id"), str) and bool(suppression["id"].strip())
        has_path = any(
            (isinstance(suppression.get(key), str) and bool(suppression[key].strip()))
            or (isinstance(suppression.get(key), list) and bool(suppression[key]))
            for key in ("files", "paths")
        )
        if not has_id and not has_path:
            return {"suppress": [], "config_error": f"{name} suppression {index} needs id, files, or paths"}
    return {"suppress": suppressions}


def _copy_verification_registry(registry: dict) -> dict:
    return {
        sid: {
            "path_roots": list(contract["path_roots"]),
            "path_patterns": list(contract["path_patterns"]),
            "expected_kind": contract["expected_kind"],
            "required_fields": list(contract["required_fields"]),
            "required_values": dict(contract.get("required_values") or {}),
        }
        for sid, contract in registry.items()
    }


def _registry_list(value: Any, field: str, name: str, sid: str) -> Tuple[Optional[List[str]], Optional[str]]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        return None, f"{name} verification registry {sid} field {field} must be a non-empty string list"
    return [item.strip() for item in value], None


def validate_verification_registry_config(data: Any, name: str) -> Tuple[dict, Optional[str]]:
    """Validate and normalize explicit per-surface artifact contracts."""
    defaults = _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY)
    if not isinstance(data, dict):
        return defaults, None
    configured = data.get("verification_artifact_registry")
    if configured is None:
        return defaults, None
    if not isinstance(configured, dict):
        return defaults, f"{name} verification_artifact_registry must be an object"

    registry = _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY)
    canonical_ids = {sid for sid, _surface, _category in COVERAGE_SURFACES}
    for sid, raw_contract in configured.items():
        if sid not in canonical_ids:
            return defaults, f"{name} verification registry has unknown surface: {sid!r}"
        if not isinstance(raw_contract, dict):
            return defaults, f"{name} verification registry {sid} must be an object"

        # Accept the shorter aliases so an explicit config can stay readable,
        # while exposing one stable normalized shape to the verifier.
        contract = dict(registry[sid])
        aliases = {
            "path_roots": ("path_roots", "roots", "allowed_roots"),
            "path_patterns": ("path_patterns", "patterns", "allowed_patterns"),
        }
        for target, keys in aliases.items():
            for key in keys:
                if key in raw_contract:
                    values, error = _registry_list(raw_contract[key], target, name, sid)
                    if error:
                        return defaults, error
                    contract[target] = values or []
                    break
        if "expected_kind" in raw_contract:
            if not isinstance(raw_contract["expected_kind"], str) or not raw_contract["expected_kind"].strip():
                return defaults, f"{name} verification registry {sid} field expected_kind must be a non-empty string"
            contract["expected_kind"] = raw_contract["expected_kind"].strip()
        if "required_fields" in raw_contract:
            values, error = _registry_list(raw_contract["required_fields"], "required_fields", name, sid)
            if error:
                return defaults, error
            contract["required_fields"] = values or []
        if "required_values" in raw_contract:
            values = raw_contract["required_values"]
            if not isinstance(values, dict) or not all(
                isinstance(key, str) and key.strip() and isinstance(value, (str, int, float, bool))
                for key, value in values.items()
            ):
                return defaults, f"{name} verification registry {sid} field required_values must be an object of scalar values"
            contract["required_values"] = dict(values)

        for root in contract["path_roots"]:
            root_path = Path(root)
            if root_path.is_absolute() or ".." in root_path.parts:
                return defaults, f"{name} verification registry {sid} path_roots must stay inside the evidence root"
        for pattern in contract["path_patterns"]:
            if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                return defaults, f"{name} verification registry {sid} path_patterns must stay inside the surface root"

        required_fields = list(dict.fromkeys(contract["required_fields"] + ["surface_id", "kind"]))
        required_values = dict(contract.get("required_values") or {})
        required_values["surface_id"] = sid
        required_values.setdefault("kind", contract["expected_kind"])
        contract["required_fields"] = required_fields
        contract["required_values"] = required_values
        registry[sid] = contract
    return registry, None


def _config_with_registry(data: Any, name: str) -> dict:
    suppressions = validate_suppressions_config(data, name)
    registry, registry_error = validate_verification_registry_config(data, name)
    result = {
        "suppress": suppressions.get("suppress", []),
        "verification_artifact_registry": registry,
    }
    if suppressions.get("config_error"):
        result["config_error"] = suppressions["config_error"]
    if registry_error:
        result["verification_registry_error"] = registry_error
        result["config_error"] = "; ".join(
            item for item in (result.get("config_error"), registry_error) if item
        )
    return result


def load_checkyourself_config(root: Path) -> dict:
    for name in CONFIG_NAMES:
        path = root / name
        if not path.exists():
            continue
        if path.suffix == ".json":
            try:
                data = strict_json_loads(path.read_text(encoding="utf-8"))
                return _config_with_registry(data, name)
            except (ValueError, OSError, UnicodeError):
                return {
                    "suppress": [],
                    "verification_artifact_registry": _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY),
                    "verification_registry_error": f"{name} could not be parsed as JSON",
                    "config_error": f"{name} could not be parsed as JSON",
                }
        try:
            # The minimal YAML parser intentionally remains suppression-only.
            # JSON is the explicit configuration format for registry overrides.
            return _config_with_registry(
                {"suppress": parse_minimal_yaml_suppressions(path.read_text(encoding="utf-8"))},
                name,
            )
        except (OSError, UnicodeError, ValueError) as exc:
            return {
                "suppress": [],
                "verification_artifact_registry": _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY),
                "verification_registry_error": f"{name} is invalid: {exc}",
                "config_error": f"{name} is invalid: {exc}",
            }
    return {
        "suppress": [],
        "verification_artifact_registry": _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY),
    }


def evidence_path(evidence: str) -> str:
    first = evidence.split(" (", 1)[0]
    match = re.match(r"^(.+):(\d+)$", first)
    return match.group(1) if match else first


def suppression_matches(finding: dict, suppression: dict) -> bool:
    sid = str(suppression.get("id") or "").strip()
    files = suppression.get("files") or suppression.get("paths") or []
    if not sid and not files:
        return False
    if sid and sid not in {str(finding.get("id")), str(finding.get("finding")), str(finding.get("title"))}:
        return False
    if isinstance(files, str):
        files = [files]
    if files:
        paths = [evidence_path(str(item)) for item in finding.get("evidence") or []]
        if not any(fnmatch.fnmatch(path, pattern) or path == pattern for path in paths for pattern in files):
            return False
    return True


def apply_suppressions(findings: List[dict], suppressions: List[dict]) -> List[dict]:
    for finding in findings:
        for suppression in suppressions:
            sid = str(suppression.get("id") or "").strip()
            files = suppression.get("files") or suppression.get("paths") or []
            if isinstance(files, str):
                files = [files]
            if sid and sid not in {str(finding.get("id")), str(finding.get("finding")), str(finding.get("title"))}:
                continue
            evidence = [str(item) for item in finding.get("evidence") or []]
            if files:
                matched = [
                    item for item in evidence
                    if any(fnmatch.fnmatch(evidence_path(item), pattern) or evidence_path(item) == pattern for pattern in files)
                ]
                if not matched:
                    continue
                finding["evidence"] = [item for item in evidence if item not in matched]
                finding.setdefault("suppressed_evidence", []).extend({
                    "evidence": item,
                    "reason": str(suppression.get("reason") or "reviewed suppression"),
                    "reviewed_by": str(suppression.get("reviewed_by") or ""),
                    "reviewed_at": str(suppression.get("reviewed_at") or ""),
                } for item in matched)
                if finding["evidence"]:
                    continue
            elif not suppression_matches(finding, suppression):
                continue
            if not files or not finding.get("evidence"):
                finding["status"] = "suppressed"
                finding["suppression"] = {
                    "reason": str(suppression.get("reason") or "reviewed suppression"),
                    "reviewed_by": str(suppression.get("reviewed_by") or ""),
                    "reviewed_at": str(suppression.get("reviewed_at") or ""),
                }
                break
    return findings


DEFAULT_MAX_FILES = 6000


def keep_dir(parent: Path, name: str) -> bool:
    if name in IGNORED_DIRS:
        return False
    if name.startswith(".") and name != ".github":
        return False
    # Never descend symlinked directories: they can escape the project tree.
    return not (parent / name).is_symlink()


def iter_files(root: Path, limit: int = DEFAULT_MAX_FILES) -> Tuple[List[Path], dict]:
    root = root.resolve()
    files: List[Path] = []
    stats = {
        "max_files": limit,
        "truncated": False,
        "files_beyond_limit": 0,
        "symlinks_skipped": 0,
        "symlink_dirs_skipped": 0,
        "files_oversized": 0,
        "files_unreadable": 0,
        "content_truncated": 0,
        "skipped_files": [],
        "oversized_files": [],
        "unreadable_files": [],
        "truncated_files": [],
        "incomplete": False,
    }
    for dirpath, dirnames, filenames in os.walk(root):
        parent = Path(dirpath)
        # Sorting dirnames keeps walk order deterministic across filesystems.
        kept_dirnames = []
        for dirname in sorted(dirnames):
            if dirname in IGNORED_DIRS or (dirname.startswith(".") and dirname != ".github"):
                continue
            if (parent / dirname).is_symlink():
                stats["symlink_dirs_skipped"] += 1
                stats["skipped_files"].append(rel(root, parent / dirname))
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames
        for name in sorted(filenames):
            p = parent / name
            if p.is_symlink():
                stats["symlinks_skipped"] += 1
                stats["skipped_files"].append(rel(root, p))
                continue
            try:
                real = p.resolve(strict=True)
                real.relative_to(root)
                if real.stat().st_size > 2_000_000:
                    stats["files_oversized"] += 1
                    stats["oversized_files"].append(rel(root, p))
                    continue
            except ValueError:
                # Resolves outside the scanned tree (e.g. via a parent link).
                stats["symlinks_skipped"] += 1
                stats["skipped_files"].append(rel(root, p))
                continue
            except RuntimeError:
                # Symlink loops can make Path.resolve fail without an OSError.
                stats["symlinks_skipped"] += 1
                stats["skipped_files"].append(rel(root, p))
                continue
            except OSError:
                stats["files_unreadable"] += 1
                stats["unreadable_files"].append(rel(root, p))
                continue
            if len(files) >= limit:
                stats["truncated"] = True
                stats["files_beyond_limit"] += 1
                stats["truncated_files"].append(rel(root, p))
                continue
            files.append(p)
    stats["skipped_files"] = sorted(set(stats["skipped_files"]))
    stats["oversized_files"] = sorted(set(stats["oversized_files"]))
    stats["unreadable_files"] = sorted(set(stats["unreadable_files"]))
    stats["truncated_files"] = sorted(set(stats["truncated_files"]))
    stats["incomplete"] = bool(
        stats["truncated"]
        or stats["symlinks_skipped"]
        or stats["symlink_dirs_skipped"]
        or stats["files_oversized"]
        or stats["files_unreadable"]
    )
    return files, stats


def detect_stack(root: Path) -> Tuple[List[str], Dict[str, str], Dict[str, List[str]]]:
    signals: List[str] = []
    scripts: Dict[str, str] = {}
    deps_found: Dict[str, List[str]] = {}

    for key, label in STACK_FILES.items():
        if (root / key).exists():
            signals.append(f"{label}: `{key}`")

    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(read_text(package_json))
            if not isinstance(data, dict):
                signals.append("package.json exists but must contain a JSON object")
                data = {}
            if isinstance(data.get("scripts"), dict):
                scripts = {
                    str(k): redact_sensitive_text(str(v))
                    for k, v in sorted(data["scripts"].items())
                }
            deps: Dict[str, str] = {}
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                if isinstance(data.get(section), dict):
                    deps.update(data[section])
            for dep, label in DEPENDENCY_HINTS.items():
                if dep in deps:
                    deps_found.setdefault(label, []).append(dep)
        except (ValueError, UnicodeError):
            signals.append("package.json exists but could not be parsed")

    py_manifests = ["pyproject.toml", "requirements.txt", "Pipfile"]
    py_text = "\n".join(read_text(root / f) for f in py_manifests if (root / f).exists()).lower()
    for dep, label in DEPENDENCY_HINTS.items():
        if dep.lower() in py_text:
            deps_found.setdefault(label, []).append(dep)

    return sorted(signals), scripts, deps_found


def parse_gitignore_patterns(text: str) -> List[str]:
    patterns: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip(" \t")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(r"\#"):
            line = line[1:]
        patterns.append(line)
    return patterns


def gitignore_entries(root: Path) -> List[str]:
    gi = root / ".gitignore"
    return parse_gitignore_patterns(read_text(gi)) if gi.exists() else []


def _gitignore_pattern_matches(pattern: str, path: str) -> bool:
    rule = pattern[1:] if pattern.startswith("!") else pattern
    if rule.startswith(r"\!"):
        rule = rule[1:]
    directory_only = rule.endswith("/")
    anchored = rule.startswith("/")
    rule = rule.strip("/")
    candidate = path.replace(os.sep, "/")
    if candidate.startswith("./"):
        candidate = candidate[2:]
    candidate = candidate.lstrip("/")
    if not rule or not candidate:
        return False
    if "/" not in rule:
        segments = candidate.split("/")
        if directory_only:
            segments = segments[:-1]
        if anchored:
            return bool(segments) and fnmatch.fnmatchcase("/".join(segments), rule)
        return any(fnmatch.fnmatchcase(segment, rule) for segment in segments)
    parts = candidate.split("/")
    candidates = ["/".join(parts[:index]) for index in range(1, len(parts))]
    if not directory_only:
        candidates.append(candidate)
    if not anchored:
        candidates.extend(
            "/".join(value.split("/")[index:])
            for value in list(candidates)
            for index in range(1, len(value.split("/")))
        )
    return any(fnmatch.fnmatchcase(value, rule) for value in candidates)


def gitignore_ignores_path(patterns: List[str], path: str) -> bool:
    ignored = False
    for pattern in patterns:
        if _gitignore_pattern_matches(pattern, path):
            ignored = not pattern.startswith("!")
    return ignored


def is_env_example_name(name: str) -> bool:
    lower = name.lower()
    return lower in ENV_EXAMPLE_NAMES or (
        lower.startswith((".env.", "env."))
        and lower.endswith((".example", ".sample", ".template"))
    ) or (
        lower.endswith(".env")
        and any(token in lower for token in ("example", "sample", "template"))
    )


def classify_env_file(name: str) -> Optional[str]:
    """Classify a file name as an 'example' env file, a 'real' one, or neither."""
    lower = name.lower()
    if is_env_example_name(lower):
        return "example"
    if lower == ".env" or lower.startswith(".env.") or lower.endswith(".env"):
        return "real"
    return None


def is_placeholder_secret_value(value: str) -> bool:
    lower = value.lower().strip("\"'")
    placeholder_tokens = (
        "your_",
        "replace",
        "placeholder",
        "example",
        "sample",
        "changeme",
        "change_me",
        "dummy",
        "fake",
        "redacted",
    )
    return any(token in lower for token in placeholder_tokens)


def context_path_reason(path: str) -> Optional[str]:
    """Return a review-context reason for low-confidence heuristic matches."""
    for segment in (part.lower() for part in Path(path).parts):
        segment_tokens = set(re.split(r"[._-]+", segment))
        if any(
            segment == marker
            or marker in segment_tokens
            or segment.startswith((marker + ".", marker + "-", marker + "_"))
            for marker in CONTEXT_ONLY_PATH_MARKERS
        ):
            return "documentation, test, fixture, example, audit, or snapshot path; heuristic match is review context"
    return None


def detector_or_guard_context_reason(lines: Sequence[str], index: int) -> Optional[str]:
    """Suppress quoted detector patterns and explicitly guarded eval calls only."""
    line = lines[index]
    lower = line.lower()
    window = "\n".join(lines[max(0, index - 14): index + 1]).lower()
    if re.search(r"\b(?:pattern|patterns|regex|regexp|risky_patterns?|re\.compile|new\s+regexp)\b", lower):
        return "detector source string, not an executable sink"
    if any(marker in lower for marker in ("never use eval", "no eval", "dangerous eval() detected")):
        return "quoted detector or guard guidance, not an executable sink"
    if "eval" not in lower:
        return None
    if (
        "blockedpatterns" in window
        and re.search(r"if\s*\([^\n)]*blockedpatterns[^\n)]*(?:length|includes)", window)
        and re.search(r"eval\s*\(\s*(?:wrapped|compiled|safe|validated|isolated|sandbox)", lower)
    ):
        return "intentional guarded eval follows a nearby blocked-pattern check"
    if "page!.evaluate" in window and "sourcesfnsource" in window:
        return "intentional eval rebuilds a function inside an isolated page.evaluate callback"
    return None


SOURCEMAP_CONFIG_NAMES = {
    "next.config.js", "next.config.mjs", "next.config.ts",
    "webpack.config.js", "webpack.config.ts",
}


def scan_file_contents(root: Path, files: List[Path], scan_limits: Optional[dict] = None) -> Dict[str, Any]:
    """Single content pass over every scannable file, feeding all detectors.

    High-confidence secrets are scanned everywhere, including tests and docs,
    because real credentials get committed in both. Low-confidence secret
    assignments and heuristic sink matches record context suppression reasons
    for docs/tests/audits and detector or explicitly guarded eval text.
    """
    results: Dict[str, List[str]] = {
        "env_files": [],
        "real_env_files": [],
        "suspicious_high": [],
        "suspicious_low": [],
        "debug_flags": [],
        "cors_wildcards": [],
        "dangerous_sinks": [],
        "default_credentials": [],
        "sourcemap_configs": [],
        "context_suppressions": [],
        "context_suppression_count": 0,
    }

    def suppress_context(rp: str, line_no: int, detector: str, reason: str) -> None:
        results["context_suppression_count"] += 1
        results["context_suppressions"].append({
            "path": rp,
            "line": line_no,
            "detector": detector,
            "reason": reason,
        })

    for p in files:
        rp = rel(root, p)
        name = p.name.lower()
        suffix = p.suffix.lower()
        kind = classify_env_file(name)
        is_example = kind == "example"
        if kind == "real":
            results["real_env_files"].append(rp)
            results["env_files"].append(rp)
        elif kind == "example":
            results["env_files"].append(rp)

        is_known_config = name in EXTENSIONLESS_CONFIG_NAMES
        if suffix not in TEXT_EXTENSIONS and not name.startswith(".env") and kind is None and not is_known_config:
            continue
        text, was_truncated, unreadable = read_text_with_status(p, max_chars=2_000_000)
        if scan_limits is not None:
            if was_truncated:
                scan_limits["content_truncated"] += 1
                scan_limits["truncated_files"].append(rp)
            if unreadable:
                scan_limits["files_unreadable"] += 1
                scan_limits["unreadable_files"].append(rp)
        if unreadable:
            continue
        if not text or looks_binary(text):
            continue

        # Match markers against whole path segments (and segment stems like
        # `app.test.ts`) so `docker-compose.yml` is not mistaken for a doc path.
        path_reason = context_path_reason(rp)
        in_test_path = path_reason is not None
        is_code = suffix in CODE_EXTENSIONS
        is_config = suffix in CONFIG_EXTENSIONS or kind is not None or is_known_config

        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if any(r.search(line) for r in SECRET_SHAPE_RES):
                results["suspicious_high"].append(secret_evidence(
                    rp, line_no, "high-confidence credential shape",
                    "credential_shape", "high", line,
                ))
            else:
                value_match = SECRET_VALUE_RE.search(line)
                if (
                    value_match
                    and SECRET_NAME_RE.search(line)
                    and not stripped.startswith(("#", "//", "*"))
                    and not is_placeholder_secret_value(value_match.group(2))
                ):
                    if path_reason:
                        suppress_context(rp, line_no, "secret_name_and_assignment", path_reason)
                    else:
                        results["suspicious_low"].append(secret_evidence(
                            rp, line_no, "possible secret-like assignment",
                            "secret_name_and_assignment", "low", line,
                        ))

            if in_test_path:
                for sink_re, label in DANGEROUS_SINK_RES:
                    if sink_re.search(line):
                        suppress_context(rp, line_no, label, path_reason or "heuristic detector skipped in review context")
                continue
            if (is_config or suffix == ".py") and any(r.search(line) for r in DEBUG_FLAG_RES):
                results["debug_flags"].append(f"{rp}:{line_no} ({compact_context(line)})")
            if is_code or is_config:
                if any(r.search(line) for r in CORS_WILDCARD_RES):
                    results["cors_wildcards"].append(f"{rp}:{line_no} ({compact_context(line)})")
                if not is_example and (DEFAULT_CRED_RE.search(line) or DEFAULT_CRED_URL_RE.search(line)):
                    results["default_credentials"].append(f"{rp}:{line_no} ({compact_context(line)})")
            if is_code:
                for sink_re, label in DANGEROUS_SINK_RES:
                    if sink_re.search(line):
                        reason = detector_or_guard_context_reason(lines, line_no - 1)
                        if reason:
                            suppress_context(rp, line_no, label, reason)
                        else:
                            results["dangerous_sinks"].append(f"{rp}:{line_no} ({label}; {compact_context(line)})")
                        break
            if name in SOURCEMAP_CONFIG_NAMES and any(r.search(line) for r in SOURCEMAP_RES):
                results["sourcemap_configs"].append(f"{rp}:{line_no} ({compact_context(line)})")

    output: Dict[str, Any] = {}
    for key, values in results.items():
        if key == "context_suppression_count":
            output[key] = values
            continue
        if key == "context_suppressions":
            unique = {json.dumps(value, sort_keys=True): value for value in values}
            output[key] = [unique[item] for item in sorted(unique)[:100]]
        else:
            output[key] = sorted(set(values))[:50]
    return output


def find_tests(root: Path, files: List[Path]) -> List[str]:
    test_dirs = {"test", "tests", "spec", "specs", "__tests__", "playwright", "cypress", "e2e"}
    test_extensions = {".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".java", ".rb", ".rs"}
    tests: List[str] = []
    for p in files:
        rp = rel(root, p)
        lower = rp.lower()
        suffix = p.suffix.lower()
        if suffix not in test_extensions:
            continue
        parts = [part.lower() for part in Path(lower).parts]
        stem = p.stem.lower()
        in_test_dir = any(part in test_dirs for part in parts[:-1])
        conventional_name = (
            stem in {"test", "spec"}
            or stem.startswith("test_")
            or stem.endswith("_test")
            or stem.endswith(".test")
            or stem.endswith(".spec")
            or (suffix == ".java" and stem.startswith("test"))
        )
        if in_test_dir or conventional_name:
            tests.append(rp)
    return sorted(set(tests))[:100]


def find_ci(root: Path) -> List[str]:
    ci: List[str] = []
    wf = root / ".github" / "workflows"
    if wf.exists():
        ci.extend(sorted(rel(root, p) for p in wf.glob("*") if p.is_file()))
    for f in (".gitlab-ci.yml", "azure-pipelines.yml", ".circleci/config.yml", "Jenkinsfile"):
        if (root / f).exists():
            ci.append(f)
    return sorted(set(ci))


def run_deep_checks(root: Path, ci: List[str], gitignore: List[str]) -> List[Finding]:
    findings: List[Finding] = []
    mutable_actions: List[str] = []
    npm_install_in_ci: List[str] = []
    action_re = re.compile(r"uses:\s*['\"]?([^@\s'\"]+)@([^@\s'\"]+)", re.I)
    pinned_sha_re = re.compile(r"^[0-9a-f]{40}$", re.I)
    npm_install_re = re.compile(r"\bnpm\s+install\b(?!\s+-g)")

    for workflow in ci:
        if not workflow.startswith(".github/workflows/"):
            continue
        path = root / workflow
        for line_no, line in enumerate(read_text(path).splitlines(), start=1):
            match = action_re.search(line)
            if match:
                action, ref = match.groups()
                if not pinned_sha_re.match(ref):
                    mutable_actions.append(
                        f"{workflow}:{line_no} (uses {action}@{ref}; pin to a full commit SHA)"
                    )
            if npm_install_re.search(line):
                npm_install_in_ci.append(f"{workflow}:{line_no} (use `npm ci` for reproducible installs)")

    if mutable_actions:
        findings.append(Finding(
            "CY-SUPPLY-001",
            "P2",
            "Mutable GitHub Action references",
            "One or more workflow steps use a version tag instead of an immutable commit SHA. "
            "A compromised or moved tag can change your CI behavior without a code diff.",
            mutable_actions[:50],
            category="C6",
            recommended_fix="Pin each third-party action to a full commit SHA and leave a version comment for readability.",
        ))

    if ci and not any((root / path).exists() for path in (".github/dependabot.yml", ".github/dependabot.yaml", "renovate.json")):
        findings.append(Finding(
            "CY-SUPPLY-003",
            "P3",
            "No dependency update automation detected",
            "CI exists, but no Dependabot or Renovate configuration was found. Dependency risk can silently age.",
            [".github/dependabot.yml or renovate.json not found"],
            category="C6",
            recommended_fix="Add Dependabot or Renovate for the detected package ecosystems.",
        ))

    if npm_install_in_ci:
        findings.append(Finding(
            "CY-SUPPLY-004",
            "P3",
            "CI installs dependencies without the lockfile contract",
            "A workflow runs `npm install` instead of `npm ci`. Installs can drift from the lockfile, "
            "so CI may pass with different dependency versions than production.",
            npm_install_in_ci[:50],
            category="C6",
            recommended_fix="Use `npm ci` (or the pnpm/yarn frozen-lockfile equivalent) in CI.",
        ))

    gitignore_targets = {".env": ".env", "*.pem": "secret.pem", "*.key": "secret.key"}
    missing_gitignore = [
        pattern for pattern, target in gitignore_targets.items()
        if not gitignore_ignores_path(gitignore, target)
    ]
    if missing_gitignore:
        findings.append(Finding(
            "CY-SECRET-003",
            "P3",
            "Sensitive file patterns missing from .gitignore",
            "Common local secret file patterns are not explicitly ignored.",
            [f"missing gitignore pattern: {pattern}" for pattern in missing_gitignore],
            category="C3",
            recommended_fix="Add local secret file patterns to `.gitignore` and verify no matching files were previously committed.",
        ))

    return findings


def _segment_hit(needle: str, segment: str) -> bool:
    """Match a risk hint against one path segment on word boundaries.

    Substring matching produced noise (`rapid/` matched `api`, `user-agent.ts`
    matched `agent`), so hints only match whole segments, simple plurals, and
    boundary-delimited prefixes.
    """
    if segment in (needle, needle + "s", needle + "es"):
        return True
    return segment.startswith((needle + ".", needle + "-", needle + "_", needle + "s.", needle + "es."))


def path_hints(root: Path, files: List[Path]) -> Dict[str, List[str]]:
    hints: Dict[str, List[str]] = {}
    for p in files:
        rp = rel(root, p)
        segments = [s.lower() for s in Path(rp).parts]
        for needle, label in RISK_PATH_HINTS:
            if any(_segment_hit(needle, segment) for segment in segments):
                hints.setdefault(label, []).append(rp)
    return {k: sorted(set(v))[:40] for k, v in sorted(hints.items())}


def tree_sample(root: Path, max_lines: int = 140) -> List[str]:
    lines: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        parent = Path(dirpath)
        dirnames[:] = sorted(d for d in dirnames if keep_dir(parent, d))
        cur = parent
        depth = len(cur.relative_to(root).parts) if cur != root else 0
        if depth > 3:
            dirnames[:] = []
            continue
        indent = "  " * depth
        lines.append("." if cur == root else f"{indent}{cur.name}/")
        for name in sorted(filenames)[:20]:
            lines.append(f"{indent}  {name}")
        if len(lines) >= max_lines:
            lines.append("...truncated...")
            return lines
    return lines


def build_findings(
    content: Dict[str, List[str]],
    tests: List[str],
    ci: List[str],
    gitignore: List[str],
    deps_found: Dict[str, List[str]],
    missing_lockfile: bool = False,
    deep_findings: Optional[List[Finding]] = None,
    config_error: Optional[str] = None,
) -> List[Finding]:
    """Build scan findings with stable, semantic rule IDs.

    IDs are part of the public contract: suppressions, diffs, and CI gates key
    off them, so they must stay identical run-to-run and release-to-release.
    """
    findings: List[Finding] = []
    real_env_files = content["real_env_files"]
    env_files = content["env_files"]

    if config_error:
        findings.append(Finding(
            "CY-CONFIG-003", "P2", "Invalid CheckYourself suppression configuration",
            "The optional suppression configuration could not be validated, so no suppressions were applied. "
            "Fix the configuration before relying on a clean scan.",
            [config_error],
            category="C3",
            recommended_fix="Correct the suppression file shape and rerun the scan; invalid configuration must never hide findings.",
        ))

    if content["suspicious_high"]:
        findings.append(Finding(
            "CY-SECRET-001", "P0", "High-confidence credential shape in source",
            "One or more files contain a credential-shaped value. "
            "Rotate anything real, move it to environment variables, and confirm it is gitignored.",
            content["suspicious_high"],
            category="C3",
            recommended_fix="Rotate anything real, remove it from source, load it from environment variables, and confirm history exposure.",
        ))

    if content["suspicious_low"]:
        findings.append(Finding(
            "CY-SECRET-002", "P2", "Possible secret-like field without credential shape",
            "A file contains a secret-like assignment, but no known credential shape was found. "
            "Review it before renaming fields or accepting it as benign.",
            content["suspicious_low"],
            category="C3",
            recommended_fix="Verify whether the value is a credential. If it is benign, add a reviewed `.checkyourself.yml` suppression; if real, move it to environment variables.",
        ))

    unignored_env_files = [
        path for path in real_env_files if not gitignore_ignores_path(gitignore, path)
    ]
    if unignored_env_files:
        findings.append(Finding(
            "CY-ENV-001", "P0", "A real .env file may be committed",
            "A non-example .env file exists and `.env` is not in .gitignore. "
            "If this is tracked by git, secrets are in your history. Gitignore it and rotate.",
            unignored_env_files,
            category="C3",
            recommended_fix="Add `.env` patterns to `.gitignore`, remove tracked env files, and rotate exposed values.",
        ))
    elif real_env_files:
        findings.append(Finding(
            "CY-ENV-002", "P2", "Local .env present (verify it is not tracked)",
            "A non-example .env exists; `.env` is in .gitignore, but confirm it was never committed earlier.",
            real_env_files,
            category="C3",
            recommended_fix="Run git history/secret checks and keep only redacted `.env.example` files in the repo.",
        ))

    has_example = any(is_env_example_name(Path(e).name) for e in env_files)
    if real_env_files and not has_example:
        findings.append(Finding(
            "CY-ENV-003", "P1", "No .env.example for required configuration",
            "The app uses environment variables but ships no .env.example. New contributors and "
            "deploys can miss required config. Add a documented example with no real values.",
            real_env_files,
            category="C3",
            recommended_fix="Add `.env.example` with variable names, safe placeholders, and setup notes.",
        ))

    if content["default_credentials"]:
        findings.append(Finding(
            "CY-CONFIG-002", "P1", "Default or weak credentials in committed configuration",
            "A committed file assigns a well-known default password or uses a default-credential "
            "connection string. Anyone who reads the repo can log in.",
            content["default_credentials"],
            category="C3",
            recommended_fix="Replace default credentials with strong generated values loaded from the environment, and rotate anything already deployed.",
        ))

    if content["debug_flags"]:
        findings.append(Finding(
            "CY-CONFIG-001", "P2", "Debug mode enabled in configuration",
            "A debug flag is switched on in committed configuration. If this reaches production it can "
            "leak stack traces, secrets, and internal state to users.",
            content["debug_flags"],
            category="C3",
            recommended_fix="Default debug to off, enable it only via local environment overrides, and verify production config never sets it.",
        ))

    if content["cors_wildcards"]:
        findings.append(Finding(
            "CY-API-001", "P2", "CORS allows any origin",
            "A wildcard CORS origin was found. Combined with credentials or sensitive responses, "
            "any website can call your API on behalf of its visitors.",
            content["cors_wildcards"],
            category="C4",
            recommended_fix="Replace the wildcard with an explicit allowlist of trusted origins and never combine `*` with credentials.",
        ))

    if content["dangerous_sinks"]:
        findings.append(Finding(
            "CY-CODE-001", "P2", "Dangerous code pattern in application source",
            "The code uses a pattern that is unsafe with untrusted input, such as eval, unsafe "
            "deserialization, raw HTML injection, or disabled TLS verification.",
            content["dangerous_sinks"],
            category="C4",
            recommended_fix="Replace each flagged pattern with the safe equivalent, or document why the input can never be attacker-controlled.",
        ))

    if content["sourcemap_configs"]:
        findings.append(Finding(
            "CY-WEB-001", "P3", "Source maps enabled for production builds",
            "Production source maps ship your original source to every visitor, making "
            "reverse-engineering and secret-hunting easier.",
            content["sourcemap_configs"],
            category="C9",
            recommended_fix="Disable production source maps, or restrict them to your error-tracking service.",
        ))

    if missing_lockfile:
        findings.append(Finding(
            "CY-SUPPLY-002", "P2", "No dependency lockfile committed",
            "package.json exists but no lockfile was found. Every install can resolve different "
            "dependency versions, so builds are not reproducible and supply-chain risk is unpinned.",
            ["package.json present without package-lock.json, pnpm-lock.yaml, yarn.lock, or bun.lock"],
            category="C6",
            recommended_fix="Commit the lockfile for your package manager and use frozen-lockfile installs in CI.",
        ))

    if not tests:
        findings.append(Finding(
            "CY-TEST-001", "P1", "No automated tests detected",
            "No test files were found. At minimum, add tests around auth, money, and data-loss paths.",
            [],
            category="C5",
            recommended_fix="Add the smallest regression tests around the highest-risk user paths.",
        ))

    if not ci:
        findings.append(Finding(
            "CY-CI-001", "P2", "No CI pipeline detected",
            "No CI configuration found. A CI gate catches regressions before they reach users.",
            [],
            category="C6",
            recommended_fix="Add a minimal CI workflow that installs, builds, tests, and runs secret checks.",
        ))

    if "Stripe/payments" in deps_found and not tests:
        findings.append(Finding(
            "CY-PAY-001", "P1", "Payments present but no tests",
            "A payments dependency was detected with no tests. Payment flows are high-blast-radius; "
            "add negative and webhook tests.",
            [],
            category="C4",
            recommended_fix="Add payment success, failure, idempotency, and webhook signature tests.",
        ))

    llm_deps = sorted(set(deps_found) & LLM_DEPENDENCY_LABELS)
    if llm_deps and not tests:
        findings.append(Finding(
            "CY-AI-001", "P2", "LLM integration present but no tests",
            "An LLM dependency was detected with no tests. Untested AI paths fail in expensive ways: "
            "malformed outputs, runaway token spend, and prompt-injection regressions.",
            [f"LLM dependency detected: {label}" for label in llm_deps],
            category="C10",
            recommended_fix="Add tests for output validation, failure handling, and cost guards around every model call.",
        ))

    findings.extend(deep_findings or [])
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.id))
    return findings


def scan(root: Path, deep: bool = False, max_files: int = DEFAULT_MAX_FILES) -> dict:
    root = root.resolve()
    files, scan_limits = iter_files(root, limit=max_files)
    stack_signals, scripts, deps_found = detect_stack(root)
    content = scan_file_contents(root, files, scan_limits)
    scan_limits["truncated_files"] = sorted(set(scan_limits["truncated_files"]))
    scan_limits["unreadable_files"] = sorted(set(scan_limits["unreadable_files"]))
    scan_limits["incomplete"] = bool(
        scan_limits["truncated"]
        or scan_limits["symlinks_skipped"]
        or scan_limits["symlink_dirs_skipped"]
        or scan_limits["files_oversized"]
        or scan_limits["files_unreadable"]
        or scan_limits["content_truncated"]
    )
    tests = find_tests(root, files)
    ci = find_ci(root)
    hints = path_hints(root, files)
    gitignore = gitignore_entries(root)
    deep_results = run_deep_checks(root, ci, gitignore) if deep else []
    config = load_checkyourself_config(root)
    missing_lockfile = (root / "package.json").exists() and not any(
        (root / name).exists() for name in LOCKFILE_NAMES
    )
    findings = build_findings(
        content,
        tests,
        ci,
        gitignore,
        deps_found,
        missing_lockfile=missing_lockfile,
        deep_findings=deep_results,
        config_error=config.get("config_error"),
    )
    finding_dicts = apply_suppressions([f.to_dict() for f in findings], config.get("suppress") or [])

    counts = {sev: 0 for sev in ("P0", "P1", "P2", "P3")}
    suppression_count = 0
    for f in finding_dicts:
        if f.get("status") == "suppressed":
            suppression_count += 1
            continue
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    return {
        "tool": TOOL_NAME,
        "schema": SCAN_SCHEMA_ID,
        "generated_at": now_iso(),
        "project": str(root),
        "deep": deep,
        "files_scanned": len(files),
        "scan_limits": scan_limits,
        "stack_signals": stack_signals,
        "dependencies": {k: sorted(set(v)) for k, v in sorted(deps_found.items())},
        "scripts": scripts,
        "env_files": content["env_files"],
        "tests": tests,
        "ci": ci,
        "risk_surfaces": hints,
        "findings": finding_dicts,
        "context_suppressions": content["context_suppressions"],
        "context_suppression_count": content["context_suppression_count"],
        "counts": counts,
        "suppression_count": suppression_count,
        "config_error": config.get("config_error"),
        "tree": tree_sample(root),
        "public_repo_scope_guardrails": PUBLIC_REPO_SCOPE_GUARDRAILS,
    }


def render_markdown(root: Path, data: dict) -> str:
    lines: List[str] = []
    add = lines.append
    add("# CheckYourself Project Context")
    add("")
    add("Generated locally by the CheckYourself scan & scaffold CLI (`tools/checkyourself.py`).")
    add("No secret values are included. Review before sharing with an AI assistant.")
    add("")
    add(f"- Generated at: {data['generated_at']}")
    add(f"- Project root: `{data['project']}`")
    add(f"- Files scanned: {data['files_scanned']}")
    limits = data.get("scan_limits") or {}
    if limits.get("incomplete"):
        add("- WARNING: scan incomplete; skipped, unreadable, oversized, or truncated inputs may hide findings.")
    if limits.get("truncated"):
        add(f"- WARNING: scan truncated at {limits.get('max_files')} files; "
            f"{limits.get('files_beyond_limit')} files were not scanned. "
            "Findings may be incomplete — rerun with a higher --max-files.")
    if limits.get("symlinks_skipped"):
        add(f"- Note: {limits['symlinks_skipped']} symlinked path(s) were skipped and not scanned.")
    if limits.get("files_unreadable"):
        add(f"- Note: {limits['files_unreadable']} file(s) could not be read and were not scanned.")
    add("")
    add("## Scope guardrails")
    add("")
    add("- Before claiming an entire GitHub namespace is clean, name the exact owner namespace, repository count, verification timestamp, and live evidence surfaces checked.")
    add("- Leave forks, externally owned repositories, and upstream references out of scope unless the user explicitly includes them.")
    add("")

    add("## Deterministic findings (local scan only)")
    add("")
    add("> These are cheap, high-confidence checks. The full CheckYourself diagnostic, run by your")
    add("> AI assistant, sweeps the entire production surface and explains, ranks, and fixes findings.")
    add("")
    if data["findings"]:
        c = data["counts"]
        add(f"Counts — P0: {c['P0']}, P1: {c['P1']}, P2: {c['P2']}, P3: {c['P3']}")
        add("")
        for f in data["findings"]:
            add(f"### [{f['severity']}] {f['id']} — {f['finding']}")
            add("")
            add(f["plain_english_risk"])
            if f.get("recommended_fix"):
                add("")
                add(f"Recommended first move: {f['recommended_fix']}")
            if f["evidence"]:
                add("")
                for e in f["evidence"]:
                    add(f"- {e}")
            add("")
    else:
        add("- No deterministic issues found by this lightweight scan. (This is not a clean bill of health.)")
        add("")

    def section(title: str, items: Iterable[str], empty: str) -> None:
        add(f"## {title}")
        add("")
        values = list(items)
        if values:
            for i in values:
                add(f"- {i}")
        else:
            add(f"- {empty}")
        add("")

    section("Detected stack signals", data["stack_signals"], "No common stack files detected.")
    section(
        "Dependency hints",
        (f"{label}: {', '.join(deps)}" for label, deps in data["dependencies"].items()),
        "No known dependency hints found.",
    )
    section("Package scripts", (f"`{k}`: `{v}`" for k, v in data["scripts"].items()), "No package scripts detected.")
    section("Environment files", (f"`{e}`" for e in data["env_files"]), "No .env-style files detected.")
    section("Test files/configs", (f"`{t}`" for t in data["tests"]), "No obvious test files detected.")
    section("CI workflows", (f"`{w}`" for w in data["ci"]), "No CI configuration detected.")

    add("## Risk-surface path hints")
    add("")
    if data["risk_surfaces"]:
        for label, paths in data["risk_surfaces"].items():
            add(f"### {label}")
            for p in paths:
                add(f"- `{p}`")
            add("")
    else:
        add("- No obvious risk-surface path hints detected.")
        add("")

    add("## Directory sample")
    add("")
    add("```text")
    lines.extend(data["tree"])
    add("```")
    add("")
    add("## Hand this to CheckYourself")
    add("")
    add("```text")
    add("Use this generated context with the CheckYourself diagnostic. Treat the deterministic")
    add("findings above as confirmed evidence, then sweep the whole production surface: infer the")
    add("stack, list unknowns, score production readiness 0-100 with caps, rank P0/P1/P2/P3 risks,")
    add("produce the complete remediation backlog and the highest-severity approval batch, and generate")
    add("a bespoke learning plan from the gaps.")
    add("```")
    return "\n".join(lines) + "\n"


def coverage_emit(project: str = "") -> dict:
    return {
        "tool": TOOL_NAME,
        "schema": COVERAGE_SCHEMA_ID,
        "generated_at": now_iso(),
        "project": project,
        "surfaces": [
            {
                "id": sid,
                "surface": surface,
                "category": category,
                "status": None,
                "evidence_reviewed": [],
                "evidence_receipts": [],
                "missing_evidence": [],
                "not_applicable_reason": "",
                "delegation_receipts": [],
                "claim_bound_evidence": [],
                "claim": "",
                "finding_ids": [],
            }
            for sid, surface, category in COVERAGE_SURFACES
        ],
    }


def _evidence_reference(value: Any) -> Optional[str]:
    """Extract a conservative relative file reference from an assertion."""
    if not isinstance(value, str):
        return None
    matches = list(EVIDENCE_PATH_RE.finditer(value))
    if not matches:
        return None
    return matches[-1].group("path").replace("\\", "/")


def _evidence_root(root: Optional[Path]) -> Path:
    return (root or Path.cwd()).resolve()


def _resolve_evidence_reference(reference: Any, root: Optional[Path]) -> Tuple[Optional[Path], str]:
    extracted = _evidence_reference(reference)
    if not extracted:
        return None, "reference does not contain a file path"
    base = _evidence_root(root)
    candidate = Path(extracted)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(base)
    except (OSError, RuntimeError, ValueError):
        return None, f"reference is outside evidence root {base}"
    if not resolved.is_file():
        return None, "referenced artifact does not exist"
    try:
        content = resolved.read_bytes()
    except (OSError, UnicodeError) as exc:
        return None, f"referenced artifact could not be read: {exc}"
    if not content:
        return None, "referenced artifact is empty"
    return resolved, ""


def _verification_registry_for_root(
    root: Optional[Path], explicit_registry: Optional[dict] = None
) -> Tuple[dict, Optional[str]]:
    if explicit_registry is not None:
        return validate_verification_registry_config(
            {"verification_artifact_registry": explicit_registry},
            "explicit registry",
        )
    config = load_checkyourself_config(_evidence_root(root))
    registry = config.get("verification_artifact_registry")
    if not isinstance(registry, dict):
        registry = _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY)
    return registry, config.get("verification_registry_error")


def _verification_artifact_error(
    artifact: Path,
    root: Optional[Path],
    surface_id: str,
    explicit_registry: Optional[dict] = None,
) -> Optional[str]:
    registry, registry_error = _verification_registry_for_root(root, explicit_registry)
    if registry_error:
        return f"verification artifact registry is invalid: {registry_error}"
    contract = registry.get(surface_id)
    if not isinstance(contract, dict):
        return f"surface {surface_id} has no registered verification artifact contract"
    base = _evidence_root(root)
    try:
        relative = artifact.relative_to(base).as_posix()
    except ValueError:
        return f"artifact is outside evidence root {base}"

    path_match = False
    for root_pattern in contract.get("path_roots", []):
        clean_root = str(root_pattern).strip().strip("/")
        if not clean_root:
            continue
        prefix = clean_root + "/"
        if relative.startswith(prefix):
            within_root = relative[len(prefix):]
            if within_root and any(
                fnmatch.fnmatch(within_root, pattern)
                or fnmatch.fnmatch(Path(within_root).name, pattern)
                for pattern in contract.get("path_patterns", [])
            ):
                path_match = True
                break
    if not path_match:
        roots = ", ".join(str(item) for item in contract.get("path_roots", []))
        patterns = ", ".join(str(item) for item in contract.get("path_patterns", []))
        return f"artifact path {relative!r} is not registered for {surface_id} (roots: {roots}; patterns: {patterns})"

    try:
        record = strict_json_loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        return f"artifact {relative!r} is not a valid JSON verification record: {exc}"
    if not isinstance(record, dict):
        return f"artifact {relative!r} must contain a JSON object verification record"
    expected_kind = contract.get("expected_kind")
    if record.get("kind") != expected_kind:
        return f"artifact {relative!r} has kind {record.get('kind')!r}; expected {expected_kind!r}"
    for field in contract.get("required_fields", []):
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"artifact {relative!r} is missing required verification field {field!r}"
    for field, expected in (contract.get("required_values") or {}).items():
        if record.get(field) != expected:
            return f"artifact {relative!r} field {field!r} must equal {expected!r}"
    return None


def _receipt_binding_digest(receipt: dict) -> str:
    """Hash the complete verifier-issued receipt binding, excluding its hash."""
    binding = {field: receipt.get(field) for field in RECEIPT_BINDING_FIELDS}
    encoded = json.dumps(
        binding,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _receipt_text_fields(receipt: dict) -> List[str]:
    return [
        field
        for field in (
            "reference",
            "subject_digest",
            "surface_id",
            "source_revision",
            "command",
            "claim",
            "origin",
            "source_state",
            "result",
            "issuer",
            "issued_at",
        )
        if not isinstance(receipt.get(field), str) or not receipt.get(field, "").strip()
    ]


def issue_receipt(
    reference: str,
    root: Optional[Path],
    *,
    surface_id: str,
    source_revision: str,
    command: str,
    claim: str,
    result: str,
    source_state: str,
    subject_digest: Optional[str] = None,
    registry: Optional[dict] = None,
) -> dict:
    """Issue one receipt bound to a registered verification artifact."""
    canonical_surfaces = {sid for sid, _surface, _category in COVERAGE_SURFACES}
    if surface_id not in canonical_surfaces:
        raise CliError(f"receipt surface_id must be one canonical coverage surface: {surface_id!r}")
    resolved, reason = _resolve_evidence_reference(reference, root)
    if resolved is None:
        raise CliError(f"receipt reference is invalid: {reason}")
    contract_error = _verification_artifact_error(resolved, root, surface_id, registry)
    if contract_error:
        raise CliError(f"receipt reference is not a registered verification artifact: {contract_error}")
    artifact_digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    if subject_digest is not None:
        if not isinstance(subject_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", subject_digest):
            raise CliError("receipt subject_digest must be a 64-character hexadecimal content hash")
        if subject_digest.lower() != artifact_digest.lower():
            raise CliError("receipt subject_digest must match the registered verification artifact")
    subject_digest = artifact_digest
    missing = {
        "source_revision": source_revision,
        "command": command,
        "claim": claim,
        "result": result,
        "source_state": source_state,
    }
    missing_fields = [field for field, value in missing.items() if not str(value or "").strip()]
    if missing_fields:
        raise CliError("receipt fields must not be empty: " + ", ".join(missing_fields))
    try:
        relative = resolved.relative_to(_evidence_root(root)).as_posix()
    except ValueError:
        relative = str(resolved)
    receipt = {
        "reference": relative,
        "sha256": artifact_digest,
        "subject_digest": subject_digest,
        "surface_id": surface_id,
        "source_revision": str(source_revision).strip(),
        "command": str(command).strip(),
        "claim": str(claim).strip(),
        "origin": "checkyourself verifier receipt command",
        "source_state": str(source_state).strip(),
        "result": str(result).strip(),
        "issuer": RECEIPT_ISSUER,
        "issued_at": now_iso(),
    }
    receipt["receipt_sha256"] = _receipt_binding_digest(receipt)
    return receipt


def _verify_receipts(
    receipts: Any,
    root: Optional[Path],
    *,
    require_provenance: bool = True,
    expected_surface_id: Optional[str] = None,
    expected_claim: Optional[str] = None,
    used_receipt_ids: Optional[set[str]] = None,
    registry: Optional[dict] = None,
) -> Tuple[List[str], List[str]]:
    """Verify verifier-issued, surface-bound receipts without trusting prose."""
    if not isinstance(receipts, list) or not receipts:
        return [], ["no verifier-captured receipts supplied"]
    verified: List[str] = []
    errors: List[str] = []
    seen_receipt_ids = used_receipt_ids if used_receipt_ids is not None else set()
    for index, receipt in enumerate(receipts):
        prefix = f"receipt {index}"
        if not isinstance(receipt, dict):
            errors.append(f"{prefix} is not an object")
            continue
        missing_fields = _receipt_text_fields(receipt)
        if missing_fields:
            errors.append(f"{prefix}: missing verifier binding fields: {', '.join(missing_fields)}")
            continue
        if receipt.get("issuer") != RECEIPT_ISSUER:
            errors.append(f"{prefix}: receipt was not issued by {RECEIPT_ISSUER}")
            continue
        receipt_id = receipt.get("receipt_sha256")
        if not isinstance(receipt_id, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", receipt_id):
            errors.append(f"{prefix}: receipt_sha256 must be a 64-character hexadecimal binding hash")
            continue
        if receipt_id.lower() in seen_receipt_ids:
            errors.append(f"{prefix}: receipt reuse is not allowed across surfaces or claims")
            continue
        if expected_surface_id is None:
            errors.append(f"{prefix}: verifier expected a canonical surface binding")
            continue
        if receipt.get("surface_id") != expected_surface_id:
            errors.append(
                f"{prefix}: surface binding {receipt.get('surface_id')!r} does not match {expected_surface_id}"
            )
            continue
        if expected_claim is not None and receipt.get("claim") != expected_claim:
            errors.append(f"{prefix}: claim binding does not match the coverage claim")
            continue
        if receipt_id.lower() != _receipt_binding_digest(receipt).lower():
            errors.append(f"{prefix}: receipt_sha256 does not cover its bound fields")
            continue
        reference = receipt.get("reference")
        resolved, reason = _resolve_evidence_reference(reference, root)
        if resolved is None:
            errors.append(f"{prefix}: {reason}")
            continue
        contract_error = _verification_artifact_error(resolved, root, expected_surface_id, registry)
        if contract_error:
            errors.append(f"{prefix}: {contract_error}")
            continue
        expected_hash = receipt.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash):
            errors.append(f"{prefix}: sha256 must be a 64-character hexadecimal content hash")
            continue
        subject_digest = receipt.get("subject_digest")
        if not isinstance(subject_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", subject_digest):
            errors.append(f"{prefix}: subject_digest must be a 64-character hexadecimal content hash")
            continue
        if subject_digest.lower() != expected_hash.lower():
            errors.append(f"{prefix}: subject_digest does not match the registered verification artifact")
            continue
        try:
            actual_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        except OSError as exc:
            errors.append(f"{prefix}: could not hash referenced artifact: {exc}")
            continue
        if actual_hash.lower() != expected_hash.lower():
            errors.append(f"{prefix}: content hash does not match referenced artifact")
            continue
        subject_key = f"subject:{subject_digest.lower()}"
        reference_key = f"artifact:{receipt.get('reference')}:{subject_digest.lower()}"
        if subject_key in seen_receipt_ids or reference_key in seen_receipt_ids:
            errors.append(f"{prefix}: receipt subject reuse is not allowed across surfaces or claims")
            continue
        if require_provenance:
            missing = [field for field in ("origin", "source_state", "result") if not str(receipt.get(field) or "").strip()]
            if missing:
                errors.append(f"{prefix}: missing provenance fields: {', '.join(missing)}")
                continue
        try:
            relative = resolved.relative_to(_evidence_root(root)).as_posix()
        except ValueError:
            relative = str(resolved)
        verified.append(relative)
        seen_receipt_ids.add(receipt_id.lower())
        seen_receipt_ids.add(subject_key)
        seen_receipt_ids.add(reference_key)
    return sorted(set(verified)), errors


def _coverage_surface_id(item: dict) -> Optional[str]:
    by_name = {surface: sid for sid, surface, _category in COVERAGE_SURFACES}
    raw_id = item.get("id")
    if isinstance(raw_id, str) and raw_id in {sid for sid, _surface, _category in COVERAGE_SURFACES}:
        return raw_id
    raw_surface = item.get("surface")
    return by_name.get(raw_surface) if isinstance(raw_surface, str) else None


def _coverage_evidence_state(
    item: dict,
    evidence_root: Optional[Path],
    *,
    used_receipt_ids: Optional[set[str]] = None,
) -> dict:
    status = item.get("status")
    result = {
        "status": status,
        "verified_evidence": [],
        "verified_delegation": [],
        "warnings": [],
    }
    surface_id = _coverage_surface_id(item)
    claim_value = item.get("claim") if isinstance(item.get("claim"), str) else ""
    claim = claim_value.strip() or None
    if status == "Pass":
        if not item.get("evidence_reviewed"):
            result["warnings"].append("Pass requires reviewer assertions in evidence_reviewed")
        verified, errors = _verify_receipts(
            item.get("evidence_receipts"),
            evidence_root,
            expected_surface_id=surface_id,
            expected_claim=claim,
            used_receipt_ids=used_receipt_ids,
        )
        asserted: List[str] = []
        for assertion in item.get("evidence_reviewed") or []:
            resolved, _reason = _resolve_evidence_reference(assertion, evidence_root)
            if resolved is not None:
                try:
                    asserted.append(resolved.relative_to(_evidence_root(evidence_root)).as_posix())
                except ValueError:
                    asserted.append(str(resolved))
        result["verified_evidence"] = sorted(set(verified).intersection(asserted))
        result["warnings"].extend(f"evidence receipt: {error}" for error in errors)
        if verified and not result["verified_evidence"]:
            result["warnings"].append("verifier receipt is not bound to an evidence_reviewed artifact reference")
        if not result["verified_evidence"]:
            result["status"] = "Unknown"
    elif status == "NotApplicable":
        if not str(item.get("not_applicable_reason") or "").strip():
            result["warnings"].append("NotApplicable requires a concrete reason")
        verified, errors = _verify_receipts(
            item.get("delegation_receipts"),
            evidence_root,
            expected_surface_id=surface_id,
            expected_claim=claim,
            used_receipt_ids=used_receipt_ids,
        )
        result["verified_delegation"] = verified
        result["warnings"].extend(f"delegation receipt: {error}" for error in errors)
        if not verified:
            result["status"] = "Unknown"
    return result


def _coverage_surfaces(data: Any) -> Tuple[List[Any], List[str]]:
    """Return coverage rows and structural errors without trusting input shape."""
    if not isinstance(data, dict):
        return [], ["coverage artifact must be an object"]
    if "schema" in data and data.get("schema") != COVERAGE_SCHEMA_ID:
        return [], [f"coverage artifact has unsupported schema: {data.get('schema')!r}"]
    if "surfaces" in data:
        surfaces = data["surfaces"]
    elif "coverage" in data:
        surfaces = data["coverage"]
    else:
        return [], ["coverage artifact must contain a surfaces array"]
    if not isinstance(surfaces, list):
        return [], ["coverage artifact must contain a surfaces array"]
    return surfaces, []


def _coverage_validation_errors(data: Any) -> List[str]:
    """Validate rows that can influence a coverage-backed score.

    Missing canonical rows remain valid incomplete evidence and are handled by
    ``category_coverage``. Any supplied row, however, must identify one
    canonical surface and must not contradict its category or status contract.
    """
    surfaces, errors = _coverage_surfaces(data)
    if errors:
        return errors

    by_id = {sid: (surface, category) for sid, surface, category in COVERAGE_SURFACES}
    by_name = {surface: sid for sid, surface, _category in COVERAGE_SURFACES}
    seen_ids: set[str] = set()

    for index, item in enumerate(surfaces):
        prefix = f"coverage row {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue

        raw_id = item.get("id")
        raw_surface = item.get("surface")
        raw_category = item.get("category")
        if "id" not in item:
            errors.append(f"{prefix} is missing id")
        elif not isinstance(raw_id, str) or not raw_id.strip():
            errors.append(f"{prefix} has an invalid id: {raw_id!r}")
            raw_id = None
        if "surface" not in item:
            errors.append(f"{prefix} is missing surface")
        elif not isinstance(raw_surface, str) or not raw_surface.strip():
            errors.append(f"{prefix} has an invalid surface: {raw_surface!r}")
            raw_surface = None
        if "category" not in item:
            errors.append(f"{prefix} is missing category")
        elif not isinstance(raw_category, str) or not raw_category.strip():
            errors.append(f"{prefix} has an invalid category: {raw_category!r}")

        if "id" in item:
            sid = raw_id
        elif isinstance(raw_surface, str):
            sid = by_name.get(raw_surface)
        else:
            sid = None

        if not sid:
            errors.append(f"{prefix} must identify a canonical surface by id or surface")
            continue
        if sid not in by_id:
            errors.append(f"{prefix} has unknown coverage id: {sid!r}")
            continue
        if sid in seen_ids:
            errors.append(f"{prefix} duplicates coverage id: {sid}")
        seen_ids.add(sid)

        expected_surface, expected_category = by_id[sid]
        if raw_surface is not None and raw_surface != expected_surface:
            errors.append(
                f"{prefix} surface {raw_surface!r} does not match {sid} ({expected_surface!r})"
            )

        if isinstance(raw_category, str) and raw_category.strip() and raw_category != expected_category:
            errors.append(
                f"{prefix} category {raw_category!r} does not match {sid} ({expected_category!r})"
            )

        if "status" not in item or item.get("status") is None:
            errors.append(f"{prefix} has a null or missing status")
        elif not isinstance(item.get("status"), str) or item.get("status") not in VALID_COVERAGE_STATUSES:
            errors.append(f"{prefix} has invalid status: {item.get('status')!r}")

        for field in ("evidence_reviewed", "missing_evidence", "claim_bound_evidence", "finding_ids"):
            if field in item:
                value = item.get(field)
                if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
                    errors.append(f"{prefix} has an invalid {field} array")
        if "not_applicable_reason" in item and not isinstance(item.get("not_applicable_reason"), str):
            errors.append(f"{prefix} has an invalid not_applicable_reason")
        for field in ("evidence_receipts", "delegation_receipts"):
            if field in item and (
                not isinstance(item.get(field), list)
                or not all(isinstance(entry, dict) for entry in item.get(field))
            ):
                errors.append(f"{prefix} has an invalid {field} array")

    return list(dict.fromkeys(errors))


def coverage_check(data: Any, evidence_root: Optional[Path] = None) -> dict:
    errors = _coverage_validation_errors(data)
    warnings: List[str] = []
    surfaces, shape_errors = _coverage_surfaces(data)
    if shape_errors:
        return {
            "tool": TOOL_NAME,
            "schema": "checkyourself-coverage-check/1",
            "complete": False,
            "surface_count": 0,
            "required_surface_count": len(COVERAGE_SURFACES),
            "errors": errors,
            "warnings": warnings,
        }

    by_id = {str(item.get("id")): item for item in surfaces if isinstance(item, dict) and item.get("id")}
    # Key strictly on the surface name: falling back to category collapsed
    # multiple surfaces onto one key and over-reported missing rows.
    by_name = {str(item.get("surface")): item for item in surfaces if isinstance(item, dict) and item.get("surface")}
    valid_statuses = VALID_COVERAGE_STATUSES
    pathlike_re = re.compile(r"[\w./\\-]+\.\w+|:\d+")
    verification_gap = False
    used_receipt_ids: set[str] = set()

    for sid, surface, _category in COVERAGE_SURFACES:
        item = by_id.get(sid) or by_name.get(surface)
        if not item:
            errors.append(f"{sid} missing: {surface}")
            continue
        status = item.get("status")
        if status not in valid_statuses:
            errors.append(f"{sid} has invalid or empty status: {status!r}")
            continue
        evidence = item.get("evidence_reviewed") or []
        missing = item.get("missing_evidence") or []
        if status == "Pass" and not evidence:
            errors.append(f"{sid} is Pass but has no evidence_reviewed")
        if status == "Pass" and evidence and not any(pathlike_re.search(str(e)) for e in evidence):
            warnings.append(f"{sid} Pass evidence has no file or file:line reference; prefer concrete receipts")
        evidence_state = _coverage_evidence_state(
            item,
            evidence_root,
            used_receipt_ids=used_receipt_ids,
        )
        for warning in evidence_state["warnings"]:
            warnings.append(f"{sid} {warning}")
        if status == "Unknown" and not missing:
            warnings.append(f"{sid} is Unknown but missing_evidence is empty")
        if status == "NotApplicable" and not item.get("not_applicable_reason"):
            errors.append(f"{sid} is NotApplicable but has no not_applicable_reason")
        if status in {"Pass", "NotApplicable"} and evidence_state["status"] == "Unknown":
            verification_gap = True
            warnings.append(f"{sid} is treated as Unknown until its verifier-captured evidence resolves")

    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-coverage-check/1",
        "complete": not errors and not verification_gap,
        "surface_count": len(surfaces),
        "required_surface_count": len(COVERAGE_SURFACES),
        "errors": errors,
        "warnings": warnings,
    }


def normalize_findings(data: Any) -> List[dict]:
    if isinstance(data, list):
        findings = data
    elif isinstance(data, dict):
        if isinstance(data.get("findings"), list):
            findings = data["findings"]
        elif isinstance(data.get("remediation_backlog"), list):
            findings = data["remediation_backlog"]
        else:
            findings = []
    else:
        findings = []

    normalized: List[dict] = []
    for i, raw in enumerate(findings, start=1):
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("finding") or raw.get("title") or raw.get("fix_summary") or "Untitled finding")
        detail = str(raw.get("plain_english_risk") or raw.get("detail") or raw.get("why_this_order") or "")
        severity = str(raw.get("severity") or "P3")
        status = str(raw.get("status") or "open")
        fid = str(raw.get("id") or raw.get("finding_id") or f"F-{i:03d}")
        raw_category = str(raw.get("category") or "")
        # Unknown category labels (e.g. "security") would be counted toward
        # caps but never penalized per-category, so normalize them here.
        category = raw_category if raw_category in SCORE_CATEGORIES else infer_category(title + " " + detail)
        evidence = raw.get("evidence") if isinstance(raw.get("evidence"), list) else []
        normalized.append({
            "id": fid,
            "finding_id": fid,
            "severity": severity if severity in SEVERITY_ORDER else "P3",
            "category": category,
            "finding": title,
            "title": title,
            "plain_english_risk": detail,
            "detail": detail,
            "evidence": [str(e) for e in evidence],
            "recommended_fix": str(raw.get("recommended_fix") or raw.get("fix_summary") or default_fix_for(title, category)),
            "status": status,
        })
    normalized.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["category"], f["id"]))
    return normalized


def findings_artifact_errors(data: Any) -> List[str]:
    """Reject malformed findings receipts instead of treating them as empty."""
    if isinstance(data, list):
        findings = data
    elif isinstance(data, dict):
        if "findings" in data:
            findings = data["findings"]
            if not isinstance(findings, list):
                return ["findings must be an array"]
        elif "remediation_backlog" in data:
            findings = data["remediation_backlog"]
            if not isinstance(findings, list):
                return ["remediation_backlog must be an array"]
        else:
            return ["artifact must contain a findings or remediation_backlog array"]
    else:
        return ["findings artifact must be an object or array"]

    errors = []
    for index, item in enumerate(findings):
        if not isinstance(item, dict):
            errors.append(f"finding {index} must be an object")
    return errors


def require_findings_artifact(data: Any) -> None:
    errors = findings_artifact_errors(data)
    if errors:
        raise CliError("invalid findings artifact: " + "; ".join(errors))


def infer_category(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ("secret", ".env", "token", "credential", "runtime config", "api key")):
        return "C3"
    if any(w in lower for w in ("auth", "permission", "session", "role", "admin")):
        return "C2"
    if any(w in lower for w in ("data", "tenant", "privacy", "backup", "retention", "isolation")):
        return "C1"
    if any(w in lower for w in ("api", "upload", "webhook", "validation", "payment", "stripe")):
        return "C4"
    if any(w in lower for w in ("test", "quality", "regression")):
        return "C5"
    if any(w in lower for w in ("ci", "deploy", "release", "rollback", "supply chain")):
        return "C6"
    if any(w in lower for w in ("observability", "log", "alert", "incident", "error")):
        return "C7"
    if any(w in lower for w in ("performance", "cache", "rate limit", "scaling", "load")):
        return "C8"
    if any(w in lower for w in ("frontend", "accessibility", "ux", "client")):
        return "C9"
    if any(w in lower for w in ("ai", "rag", "agent", "model", "prompt")):
        return "C10"
    return "C4"


def default_fix_for(title: str, category: str) -> str:
    if category == "C3":
        return "Move configuration to safe environment handling and verify no secret values are committed."
    if category == "C5":
        return "Add the smallest regression test that proves this path stays fixed."
    if category == "C6":
        return "Add or tighten the release gate and document rollback."
    return f"Make the smallest reversible fix for: {title}"


def category_coverage(
    coverage_data: Optional[dict], evidence_root: Optional[Path] = None
) -> Tuple[Dict[str, dict], bool]:
    """Fold surface-level coverage into per-category scoring state.

    Anti-gaming rules: a surface omitted from the artifact counts as Unknown
    (never as full credit), Pass without evidence downgrades to Unknown, and
    NotApplicable without a reason downgrades to Unknown. Omitting or
    hand-waving a surface must never score better than honestly reporting it.
    Evidence gaps are tracked independently from Finding rows so a Finding
    cannot erase a critical Unknown.
    """
    category_state: Dict[str, dict] = {
        cid: {
            "status": "MissingCoverage",
            "evidence_reviewed": [],
            "verified_evidence": [],
            "claim_bound_evidence": [],
            "missing_evidence": ["coverage artifact was not supplied"],
            "surfaces": [],
            "has_unknown": True,
            "coverage_findings": [],
        }
        for cid in SCORE_CATEGORIES
    }
    if not coverage_data:
        return category_state, False

    surfaces = coverage_data.get("surfaces") or coverage_data.get("coverage") or []
    if not isinstance(surfaces, list):
        return category_state, False

    name_to_id = {surface: sid for sid, surface, _category in COVERAGE_SURFACES}
    id_to_category = {sid: category for sid, _surface, category in COVERAGE_SURFACES}
    scored_surface_ids = {sid for sid, _surface, category in COVERAGE_SURFACES if category in SCORE_CATEGORIES}

    category_state = {
        cid: {
            "status": None,
            "evidence_reviewed": [],
            "verified_evidence": [],
            "claim_bound_evidence": [],
            "missing_evidence": [],
            "surfaces": [],
            "has_unknown": False,
            "coverage_findings": [],
        }
        for cid in SCORE_CATEGORIES
    }
    status_rank = {"Finding": 4, "Unknown": 3, "Pass": 2, "NotApplicable": 1}
    present_ids = set()
    used_receipt_ids: set[str] = set()
    unscored_verification_gaps: List[str] = []
    verification_gap = False

    for item in surfaces:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or name_to_id.get(str(item.get("surface") or ""), ""))
        category = str(item.get("category") or id_to_category.get(sid, ""))
        if category not in SCORE_CATEGORIES:
            if sid:
                present_ids.add(sid)
            if item.get("status") in {"Pass", "NotApplicable"}:
                evidence_state = _coverage_evidence_state(
                    item,
                    evidence_root,
                    used_receipt_ids=used_receipt_ids,
                )
                if evidence_state["status"] == "Unknown":
                    verification_gap = True
                    unscored_verification_gaps.extend(
                        f"{sid or 'surface'}: {warning}" for warning in evidence_state["warnings"]
                    )
            continue
        if sid:
            present_ids.add(sid)
        state = category_state[category]
        status = item.get("status") or "Unknown"
        evidence = [str(x) for x in item.get("evidence_reviewed") or []]
        evidence_state = _coverage_evidence_state(
            item,
            evidence_root,
            used_receipt_ids=used_receipt_ids,
        )
        if status == "Pass" and not evidence:
            status = "Unknown"
            state["missing_evidence"].append(f"{sid or 'surface'} marked Pass without evidence_reviewed")
        if status == "NotApplicable" and not str(item.get("not_applicable_reason") or "").strip():
            status = "Unknown"
            state["missing_evidence"].append(f"{sid or 'surface'} marked NotApplicable without a reason")
        if evidence_state["status"] == "Unknown" and status in {"Pass", "NotApplicable"}:
            verification_gap = True
            status = "Unknown"
            state["missing_evidence"].extend(
                f"{sid or 'surface'}: {warning}" for warning in evidence_state["warnings"]
            )
        if status == "Unknown":
            state["has_unknown"] = True
        if status == "Finding":
            state["coverage_findings"].append({
                "id": f"CY-COVERAGE-{sid or category}",
                "finding_id": f"CY-COVERAGE-{sid or category}",
                "severity": "P2",
                "category": category,
                "finding": f"Coverage finding requires review: {sid or category}",
                "plain_english_risk": "The coverage reviewer recorded a gap on this production surface.",
                "status": "open",
                "linked_finding_ids": [str(x) for x in item.get("finding_ids") or []],
            })
        if state["status"] is None or status_rank.get(status, 3) > status_rank.get(state["status"], 0):
            state["status"] = status
        state["surfaces"].append(sid or str(item.get("surface") or category))
        state["evidence_reviewed"].extend(evidence)
        state["verified_evidence"].extend(evidence_state["verified_evidence"])
        state["claim_bound_evidence"].extend(str(x) for x in item.get("claim_bound_evidence") or [])
        state["missing_evidence"].extend(str(x) for x in item.get("missing_evidence") or [])

    if unscored_verification_gaps:
        # Context and learning surfaces do not own score weight, but a broken
        # verifier receipt anywhere in the canonical matrix must still prevent
        # a launch-ready score from hiding that gap.
        critical_state = category_state["C1"]
        critical_state["has_unknown"] = True
        critical_state["missing_evidence"].extend(unscored_verification_gaps)

    for sid in sorted(scored_surface_ids - present_ids):
        category = id_to_category[sid]
        state = category_state[category]
        state["has_unknown"] = True
        state["missing_evidence"].append(f"surface {sid} missing from coverage artifact")
        if state["status"] is None or status_rank.get("Unknown", 3) > status_rank.get(state["status"], 0):
            state["status"] = "Unknown"

    for state in category_state.values():
        if state["status"] is None:
            state["status"] = "MissingCoverage"
            state["has_unknown"] = True
            state["missing_evidence"].append("no coverage entries supplied for this category")
        state["evidence_reviewed"] = sorted(set(state["evidence_reviewed"]))
        state["verified_evidence"] = sorted(set(state["verified_evidence"]))
        state["claim_bound_evidence"] = sorted(set(state["claim_bound_evidence"]))
        state["missing_evidence"] = sorted(set(state["missing_evidence"]))

    required_ids = {sid for sid, _surface, _category in COVERAGE_SURFACES}
    complete = required_ids <= present_ids and not verification_gap
    return category_state, complete


def missing_manual_evidence(coverage_by_category: Dict[str, dict]) -> List[dict]:
    needed: List[dict] = []
    for cid, (name, _weight) in SCORE_CATEGORIES.items():
        state = coverage_by_category[cid]
        if state.get("has_unknown") or state["status"] == "MissingCoverage":
            needed.append({
                "category": cid,
                "surface": name,
                "needed": state["missing_evidence"] or ["manual coverage evidence"],
            })
    return needed


def inferred_coverage_from_scan(scan_data: dict, findings: List[dict]) -> Dict[str, dict]:
    category_state: Dict[str, dict] = {
        cid: {
            "status": "MissingCoverage",
            "evidence_reviewed": [],
            "missing_evidence": ["manual coverage evidence still needed"],
            "surfaces": [],
        }
        for cid in SCORE_CATEGORIES
    }
    open_findings = [f for f in findings if f.get("status") not in RESOLVED_STATUSES]

    def set_state(cid: str, status: str, evidence: List[str], missing: List[str], surfaces: List[str]) -> None:
        category_state[cid] = {
            "status": status,
            "evidence_reviewed": evidence,
            "missing_evidence": missing,
            "surfaces": surfaces,
        }

    c3_findings = [f for f in open_findings if f.get("category") == "C3"]
    if c3_findings:
        set_state("C3", "Finding", [f["id"] for f in c3_findings], [], ["S08"])
    else:
        # A regex scanner finding nothing is absence of evidence, not evidence
        # of safe secret handling, so this stays Unknown rather than Pass.
        set_state(
            "C3",
            "Unknown",
            ["scan found no open secret/runtime-config findings (absence of evidence only)"],
            ["manual secret-handling and runtime-config review still needed"],
            ["S08"],
        )

    tests = scan_data.get("tests") if isinstance(scan_data.get("tests"), list) else []
    if tests:
        set_state(
            "C5",
            "Unknown",
            [f"detected test candidate: {item}" for item in tests[:10]],
            ["focused test execution receipt still needed; file presence does not prove tests pass"],
            ["S11"],
        )
    else:
        set_state("C5", "Finding", [], ["no automated tests detected by scan"], ["S11"])

    ci = scan_data.get("ci") if isinstance(scan_data.get("ci"), list) else []
    if ci:
        set_state(
            "C6",
            "Unknown",
            [f"detected CI configuration candidate: {item}" for item in ci[:10]],
            ["CI parse and successful-run receipt still needed; file presence does not prove the workflow is valid"],
            ["S12"],
        )
    else:
        set_state("C6", "Finding", [], ["no CI workflow detected by scan"], ["S12"])

    return category_state


def score_from_inputs(
    findings_data: Any,
    coverage_data: Any = _NO_COVERAGE,
    evidence_root: Optional[Path] = None,
    claim: Optional[str] = None,
) -> dict:
    require_findings_artifact(findings_data)
    findings = normalize_findings(findings_data)
    counts = {sev: 0 for sev in ("P0", "P1", "P2", "P3")}
    unresolved = [f for f in findings if f.get("status") not in RESOLVED_STATUSES]
    for f in unresolved:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    if coverage_data is not _NO_COVERAGE:
        coverage_errors = _coverage_validation_errors(coverage_data)
        if coverage_errors:
            raise CliError(
                "invalid coverage artifact: " + "; ".join(coverage_errors)
                + "; fill coverage.json with evidence, then re-run score"
            )
        coverage_by_category, coverage_complete = category_coverage(coverage_data, evidence_root)
        score_mode = "coverage-backed"
    elif isinstance(findings_data, dict) and findings_data.get("schema") == SCAN_SCHEMA_ID:
        coverage_by_category = inferred_coverage_from_scan(findings_data, findings)
        coverage_complete = False
        score_mode = "scan-derived-estimate"
    else:
        coverage_by_category, coverage_complete = category_coverage(None)
        score_mode = "finding-only-estimate"
    per_category: List[dict] = []
    raw_total = 0.0
    coverage_findings_scored: List[str] = []

    for cid, (name, weight) in SCORE_CATEGORIES.items():
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(float(weight))
            or float(weight) < 0
        ):
            raise CliError(f"invalid scoring weight for {cid}: {weight!r}")
        category_findings = [f for f in unresolved if f.get("category") == cid]
        unresolved_ids = {f.get("id") for f in unresolved}
        for coverage_finding in coverage_by_category[cid].get("coverage_findings", []):
            linked = set(coverage_finding.get("linked_finding_ids") or [])
            live_linked = linked.intersection(unresolved_ids)
            if not live_linked:
                category_findings.append(coverage_finding)
                coverage_findings_scored.append(coverage_finding["id"])
                coverage_state = coverage_by_category[cid]
                coverage_state["has_unknown"] = True
                coverage_state["missing_evidence"].append(
                    f"{coverage_finding['id']} has no linked unresolved finding; coverage Finding remains independently blocked"
                )
        coverage_state = coverage_by_category[cid]
        penalties: List[dict] = []
        awarded = float(weight)

        status = coverage_state["status"]
        if coverage_state.get("has_unknown") or status == "Unknown":
            missing = coverage_state["missing_evidence"] or ["evidence missing for this category"]
            if cid in CRITICAL_CATEGORIES:
                awarded = 0.0
                penalties.append({"reason": "critical coverage unknown", "points": weight, "missing_evidence": missing})
            else:
                reduction = weight * 0.50
                awarded -= reduction
                penalties.append({"reason": "coverage unknown", "points": round(reduction, 2), "missing_evidence": missing})
        elif status == "MissingCoverage":
            penalties.append({"reason": "coverage artifact not supplied", "points": 0, "missing_evidence": coverage_state["missing_evidence"]})

        for f in category_findings:
            fraction = SEVERITY_PENALTIES.get(f["severity"], 0.10)
            if (
                isinstance(fraction, bool)
                or not isinstance(fraction, (int, float))
                or not math.isfinite(float(fraction))
                or float(fraction) < 0
            ):
                raise CliError(f"invalid severity penalty for {f['severity']}: {fraction!r}")
            points = weight * fraction
            awarded -= points
            penalties.append({
                "finding_id": f["id"],
                "severity": f["severity"],
                "reason": f["finding"],
                "points": round(points, 2),
            })

        awarded = max(0.0, min(float(weight), awarded))
        raw_total += awarded
        per_category.append({
            "id": cid,
            "category": name,
            "weight": weight,
            "coverage_status": status,
            "evidence_reviewed": coverage_state["evidence_reviewed"],
            "verified_evidence": coverage_state.get("verified_evidence", []),
            "claim_bound_evidence": coverage_state.get("claim_bound_evidence", []),
            "missing_evidence": coverage_state["missing_evidence"],
            "penalties": penalties,
            "awarded": round(awarded, 2),
        })

    raw_score = round(raw_total)
    caps: List[dict] = []
    cap_value = 100
    if counts["P0"]:
        cap_value = min(cap_value, 49)
        caps.append({"cap": 49, "reason": "unresolved P0 finding"})
    if counts["P1"]:
        cap_value = min(cap_value, 74)
        caps.append({"cap": 74, "reason": "unresolved P1 finding"})

    critical_gap = False
    high_score_gap = False
    # Evidence caps apply in every score mode: an estimate without coverage
    # evidence must never report a launch-ready number.
    for cid, state in coverage_by_category.items():
        if (state.get("has_unknown") or state["status"] == "MissingCoverage") and cid in CRITICAL_CATEGORIES:
            critical_gap = True
        if (state.get("has_unknown") or state["status"] == "MissingCoverage") and cid in HIGH_SCORE_GATE_CATEGORIES:
            high_score_gap = True
    if critical_gap:
        cap_value = min(cap_value, 84)
        caps.append({"cap": 84, "reason": "missing evidence in a critical category"})
    if high_score_gap:
        cap_value = min(cap_value, 90)
        caps.append({"cap": 90, "reason": "score above 90 requires evidence for tests, secrets, deploy/rollback, observability, auth, and data boundaries"})

    score = min(raw_score, cap_value)
    any_gap = any(
        state.get("has_unknown") or state["status"] in {"Unknown", "MissingCoverage"}
        for state in coverage_by_category.values()
    )
    if score_mode != "coverage-backed":
        confidence = "low"
    elif coverage_complete and not critical_gap and not any_gap:
        confidence = "high"
    elif coverage_complete and not critical_gap:
        confidence = "medium"
    else:
        confidence = "low"

    result = {
        "tool": TOOL_NAME,
        "schema": SCORE_SCHEMA_ID,
        "generated_at": now_iso(),
        "score": int(score),
        "raw_score": int(raw_score),
        "score_mode": score_mode,
        "confidence": confidence,
        "counts": counts,
        "caps_applied": caps,
        "per_category": per_category,
        "findings_scored": sorted(set([f["id"] for f in unresolved] + coverage_findings_scored)),
        "coverage_complete": coverage_complete,
        "manual_evidence_needed": missing_manual_evidence(coverage_by_category),
        "workflow_dispositions": [
            {
                "finding_id": finding["id"],
                "status": finding["status"],
                "residual_risk": "closed" if finding["status"] in RESOLVED_STATUSES else "open",
            }
            for finding in findings
            if finding.get("status") in WORKFLOW_DISPOSITIONS
        ],
    }
    if claim is not None:
        claim_text = str(claim).strip()
        if not claim_text:
            raise CliError("--claim must not be empty")
        result["claim"] = claim_text
        for category in result["per_category"]:
            bound = set(category.get("claim_bound_evidence") or [])
            all_evidence = sorted(set(category.get("evidence_reviewed") or []) | set(category.get("verified_evidence") or []))
            category["claim_binding"] = [
                {
                    "evidence": evidence,
                    "claim_bound": evidence in bound,
                    "basis": "explicit coverage claim_bound_evidence entry" if evidence in bound else "no explicit claim binding; challenge runner not executed",
                }
                for evidence in all_evidence
            ]
    return result


def backlog_from_findings(findings_data: Any) -> dict:
    require_findings_artifact(findings_data)
    findings = normalize_findings(findings_data)
    backlog = []
    for f in findings:
        status = f.get("status", "open")
        item = {
            "finding_id": f["id"],
            "severity": f["severity"],
            "category": f["category"],
            "fix_summary": f.get("recommended_fix") or default_fix_for(f["finding"], f["category"]),
            "why_this_order": order_reason(f),
            "verification": verification_for(f),
            "rollback": rollback_for(f),
            "learning_value": learning_for(f),
            "status": status,
        }
        backlog.append(item)
    backlog.sort(key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), item["category"], item["finding_id"]))
    first = first_batch(backlog)
    batch_ids = [item["finding_id"] for item in first]
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-backlog/1",
        "generated_at": now_iso(),
        "remediation_backlog": backlog,
        # This selection is deterministic, but it does not analyze safety,
        # dependencies, coupling, or blast radius. Keep the old field as a
        # compatibility alias while naming the contract honestly.
        "highest_severity_batch": batch_ids,
        "first_approval_batch": batch_ids,
        "batch_basis": {
            "name": "highest_severity_batch",
            "selection": "up to three unresolved findings at the highest current severity",
            "safety_analysis": "not performed",
        },
    }


def next_from_findings(findings_data: Any) -> dict:
    require_findings_artifact(findings_data)
    backlog = backlog_from_findings(findings_data)["remediation_backlog"]
    batch = first_batch(backlog)
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-next-batch/1",
        "generated_at": now_iso(),
        # The legacy field remains for consumers of next-batch/1. This is a
        # highest-severity slice, not a safety or dependency judgment.
        "highest_severity_batch": batch,
        "next_approval_batch": batch,
        "next_highest_severity_batch": batch,
        "finding_ids": [item["finding_id"] for item in batch],
        "batch_basis": {
            "name": "highest_severity_batch",
            "selection": "up to three unresolved findings at the highest current severity",
            "safety_analysis": "not performed",
        },
    }


def diff_findings(old_data: Any, new_data: Any) -> dict:
    """Compare two findings artifacts (scan output, report, or finding list).

    Stable rule IDs make this meaningful: the same risk keeps the same ID
    across runs, so added/resolved is a real delta, not ID-shuffle noise.
    """
    require_findings_artifact(old_data)
    require_findings_artifact(new_data)
    old_findings = {f["id"]: f for f in normalize_findings(old_data)}
    new_findings = {f["id"]: f for f in normalize_findings(new_data)}
    added_ids = sorted(set(new_findings) - set(old_findings))
    removed_ids = sorted(set(old_findings) - set(new_findings))
    persisting_ids = sorted(set(old_findings) & set(new_findings))

    def is_open(finding: dict) -> bool:
        return finding.get("status") not in RESOLVED_STATUSES

    status_changes: List[dict] = []
    severity_changes: List[dict] = []
    resolved_status_ids: List[str] = []
    unchanged_ids: List[str] = []
    for fid in persisting_ids:
        old_finding = old_findings[fid]
        new_finding = new_findings[fid]
        old_status = old_finding.get("status", "open")
        new_status = new_finding.get("status", "open")
        old_severity = old_finding.get("severity", "P3")
        new_severity = new_finding.get("severity", "P3")
        if old_status != new_status:
            status_changes.append({
                "id": fid,
                "old_status": old_status,
                "new_status": new_status,
            })
        if old_severity != new_severity:
            severity_changes.append({
                "id": fid,
                "old_severity": old_severity,
                "new_severity": new_severity,
            })
        if old_status == new_status and old_severity == new_severity:
            unchanged_ids.append(fid)
        if is_open(old_finding) and not is_open(new_finding):
            resolved_status_ids.append(fid)

    # A finding can resolve without disappearing from the artifact. Include
    # those transitions in the existing resolved collection so consumers do
    # not have to infer closure from counts or status_changes.
    resolved_ids = sorted(set(removed_ids) | set(resolved_status_ids))

    regression_events: List[dict] = []

    def add_regression(event: dict) -> None:
        key = (event["id"], event["type"])
        if not any((existing["id"], existing["type"]) == key for existing in regression_events):
            regression_events.append(event)

    for fid in added_ids:
        finding = new_findings[fid]
        if is_open(finding) and finding["severity"] in {"P0", "P1"}:
            add_regression({
                "id": fid,
                "type": "newly_open",
                "severity": finding["severity"],
            })
    for fid in persisting_ids:
        old_finding = old_findings[fid]
        new_finding = new_findings[fid]
        if not is_open(old_finding) and is_open(new_finding) and new_finding["severity"] in {"P0", "P1"}:
            add_regression({
                "id": fid,
                "type": "reopened",
                "severity": new_finding["severity"],
            })
        if (
            is_open(new_finding)
            and new_finding["severity"] in {"P0", "P1"}
            and SEVERITY_ORDER.get(new_finding["severity"], 9) < SEVERITY_ORDER.get(old_finding["severity"], 9)
        ):
            add_regression({
                "id": fid,
                "type": "severity_escalated",
                "old_severity": old_finding["severity"],
                "new_severity": new_finding["severity"],
            })

    evidence_changes: List[dict] = []
    for fid in persisting_ids:
        old_evidence = set(old_findings[fid].get("evidence") or [])
        new_evidence = set(new_findings[fid].get("evidence") or [])
        if old_evidence != new_evidence:
            evidence_changes.append({
                "id": fid,
                "evidence_added": sorted(new_evidence - old_evidence),
                "evidence_resolved": sorted(old_evidence - new_evidence),
            })

    def open_counts(findings: Dict[str, dict]) -> Dict[str, int]:
        counts = {sev: 0 for sev in ("P0", "P1", "P2", "P3")}
        for f in findings.values():
            if f.get("status") not in RESOLVED_STATUSES:
                counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        return counts

    old_counts = open_counts(old_findings)
    new_counts = open_counts(new_findings)
    count_regression = any(new_counts[sev] > old_counts[sev] for sev in ("P0", "P1"))
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-diff/1",
        "generated_at": now_iso(),
        "added": [new_findings[fid] for fid in added_ids],
        "resolved": [new_findings[fid] if fid in resolved_status_ids else old_findings[fid] for fid in resolved_ids],
        "unchanged": unchanged_ids,
        "status_changes": status_changes,
        "severity_changes": severity_changes,
        "evidence_changes": evidence_changes,
        "old_counts": old_counts,
        "new_counts": new_counts,
        "count_regression": count_regression,
        "regressions": regression_events,
        "regression": count_regression or bool(regression_events),
    }


def first_batch(backlog: List[dict]) -> List[dict]:
    open_items = [b for b in backlog if b.get("status") not in RESOLVED_STATUSES]
    if not open_items:
        return []
    first_severity = open_items[0]["severity"]
    return [b for b in open_items if b["severity"] == first_severity][:3]


def order_reason(finding: dict) -> str:
    severity = finding["severity"]
    if severity == "P0":
        return "P0 risks can expose users, data, money, or secrets; handle before lower-risk polish."
    if severity == "P1":
        return "P1 risks can block a responsible launch and are usually fixable in small batches."
    if severity == "P2":
        return "P2 risks harden the launch path after immediate blockers are contained."
    return "P3 work improves maintainability and learning once higher-risk issues are handled."


def verification_for(finding: dict) -> str:
    category = finding.get("category")
    if category == "C3":
        return "Run the scanner, gitleaks or equivalent secret scan, and confirm no real values are printed or tracked."
    if category == "C5":
        return "Run the new focused test plus the existing test suite."
    if category == "C6":
        return "Run CI locally where possible and verify the workflow passes remotely."
    return "Run the smallest command or manual check that proves the specific risk changed."


def rollback_for(finding: dict) -> str:
    if finding.get("category") == "C3":
        return "Revert config-file changes only after confirming no secret value is restored."
    return "Revert the small patch or restore the previous config from version control."


def learning_for(finding: dict) -> str:
    category = finding.get("category")
    if category == "C3":
        return "Environment configuration, secret handling, and release safety."
    if category == "C5":
        return "Risk-based testing and regression gates."
    if category == "C6":
        return "CI/CD, deploy safety, and rollback discipline."
    return "How this production surface fails and how to prove the fix."


def describe_capabilities() -> dict:
    version = read_manifest_version()
    commands = [
        ("describe", "Emit this machine-readable capability manifest.", {}, CAPABILITIES_SCHEMA_ID),
        ("scan", "Detect stack signals and deterministic local findings.", {"project": "path", "deep": "optional boolean"}, SCAN_SCHEMA_ID),
        ("diagnostic", "Alias for scan; use it when docs or agents ask to run a diagnostic.", {"project": "path", "deep": "optional boolean"}, SCAN_SCHEMA_ID),
        ("coverage --emit", "Write the 20-surface coverage skeleton by default, or print JSON with --format json.", {"project": "optional string"}, COVERAGE_SCHEMA_ID),
        ("coverage --check", "Validate coverage completeness.", {"file": "coverage json path"}, "checkyourself-coverage-check/1"),
        ("receipt", "Issue one verifier-hashed receipt only for a registered, surface-specific verification artifact.", {"reference": "registered artifact path", "surface_id": "canonical surface ID", "source_revision": "revision", "command": "command recorded at issuance", "claim": "claim", "result": "observed result", "source_state": "source/environment state", "subject_digest": "optional content hash assertion"}, RECEIPT_SCHEMA_ID),
        ("score", "Compute a deterministic Production Reality Score from findings and optional verifier-checked coverage; optionally record a completion claim without executing a challenge runner.", {"findings": "json path", "coverage": "optional json path", "claim": "optional accepted completion claim", "history": "optional path"}, SCORE_SCHEMA_ID),
        ("backlog", "Rank remediation backlog and return a highest-severity batch; safety analysis is not performed.", {"findings": "json path"}, "checkyourself-backlog/1"),
        ("next", "Return the next highest-severity unresolved approval batch; safety analysis is not performed.", {"findings": "json path"}, "checkyourself-next-batch/1"),
        ("diff", "Compare two findings artifacts, report identity-aware transitions, and gate newly open, reopened, or escalated P0/P1 findings.", {"old": "json path", "new": "json path"}, "checkyourself-diff/1"),
        ("validate", "Validate an artifact against a bundled JSON schema subset.", {"kind": "schema kind", "file": "json path"}, "checkyourself-validation/1"),
        ("schema", "Print a bundled schema by name.", {"name": "schema name"}, "json-schema"),
        ("init", "Create starter generated coverage/context files without overwriting by default.", {"project": "path"}, "checkyourself-init/1"),
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
            {"id": sid, "surface": surface, "category": category}
            for sid, surface, category in COVERAGE_SURFACES
        ],
        "verification_artifact_registry": VERIFICATION_ARTIFACT_REGISTRY,
        "scoring": {
            "categories": [
                {"id": cid, "category": name, "weight": weight}
                for cid, (name, weight) in SCORE_CATEGORIES.items()
            ],
            "severity_penalties": SEVERITY_PENALTIES,
            "caps": [
                {"cap": 49, "condition": "any unresolved P0"},
                {"cap": 74, "condition": "any unresolved P1"},
                {"cap": 84, "condition": "missing evidence in C1/C2/C3 (applies in every score mode)"},
                {"cap": 90, "condition": "score above 90 without evidence for key launch gates (applies in every score mode)"},
            ],
            "score_modes": [
                {"mode": "coverage-backed", "trigger": "a coverage artifact was supplied", "max_confidence": "high"},
                {"mode": "scan-derived-estimate", "trigger": "findings input is a checkyourself-scan/1 object and no coverage supplied", "max_confidence": "low"},
                {"mode": "finding-only-estimate", "trigger": "plain findings without scan context or coverage", "max_confidence": "low"},
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


def _ensure_finite_json(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number is not valid JSON")
    if isinstance(value, dict):
        for item in value.values():
            _ensure_finite_json(item)
    elif isinstance(value, list):
        for item in value:
            _ensure_finite_json(item)


def strict_json_loads(body: str) -> Any:
    """Parse standard JSON only; Python otherwise accepts NaN and Infinity."""
    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite number {token} is not valid JSON")

    # A UTF-8 BOM is metadata about the byte stream, not part of the JSON
    # document. Accept it at the boundary so receipts from BOM-aware editors
    # remain usable; a BOM anywhere else is still invalid JSON.
    if body.startswith("\ufeff"):
        body = body[1:]
    value = json.loads(body, parse_constant=reject_constant)
    _ensure_finite_json(value)
    return value


def load_json_arg(path: str) -> Any:
    if path == "-":
        body = sys.stdin.read()
    else:
        p = Path(path)
        if not p.exists():
            raise CliError(f"JSON file not found: {path}")
        try:
            body = p.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise CliError(f"could not read JSON in {path}: {exc}") from exc
    try:
        return strict_json_loads(body)
    except (ValueError, UnicodeError) as exc:
        raise CliError(f"invalid JSON in {path}: {exc}") from exc


def json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    return type(value).__name__


def type_matches(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(type_matches(value, item) for item in expected)
    actual = json_type_name(value)
    return actual == expected or (expected == "number" and actual == "integer")


_SCHEMA_ANNOTATION_KEYWORDS = {
    "$schema", "$id", "$comment", "title", "description", "default",
    "examples", "deprecated", "readOnly", "writeOnly",
}
_SCHEMA_VALIDATION_KEYWORDS = {
    "type", "enum", "const", "oneOf", "anyOf", "allOf", "not", "required",
    "properties", "additionalProperties", "items", "minimum", "maximum",
    "exclusiveMinimum", "exclusiveMaximum", "minItems", "maxItems",
    "uniqueItems", "minLength", "maxLength", "pattern",
}


def _schema_definition_errors(schema: Any, path: str = "$") -> List[str]:
    """Find unsupported keywords anywhere in a schema before validating data."""
    if schema is True or schema is False:
        return []
    if not isinstance(schema, dict):
        return [f"{path}: schema must be an object or boolean"]
    errors: List[str] = []
    unsupported = sorted(
        set(schema) - _SCHEMA_ANNOTATION_KEYWORDS - _SCHEMA_VALIDATION_KEYWORDS
    )
    if unsupported:
        errors.append(f"{path}: unsupported schema keyword(s): {', '.join(unsupported)}")
    for keyword in ("oneOf", "anyOf", "allOf"):
        branches = schema.get(keyword)
        if branches is not None and isinstance(branches, list):
            for index, branch in enumerate(branches):
                errors.extend(_schema_definition_errors(branch, f"{path}.{keyword}[{index}]"))
    if "not" in schema:
        errors.extend(_schema_definition_errors(schema["not"], f"{path}.not"))
    props = schema.get("properties")
    if isinstance(props, dict):
        for key, subschema in props.items():
            errors.extend(_schema_definition_errors(subschema, f"{path}.properties.{key}"))
    for keyword in ("additionalProperties", "items"):
        subschema = schema.get(keyword)
        if isinstance(subschema, dict):
            errors.extend(_schema_definition_errors(subschema, f"{path}.{keyword}"))
    return errors


def validate_json_schema(
    data: Any, schema: Any, path: str = "$", _check_schema: bool = True
) -> List[str]:
    """Validate the bundled schema subset without silently ignoring keywords.

    The CLI intentionally stays standard-library-only.  Every validation keyword
    supported here has executable semantics; an unknown keyword is an error so a
    schema cannot claim a constraint that this validator quietly skips.
    """
    errors: List[str] = []
    if _check_schema:
        errors.extend(_schema_definition_errors(schema, path))
    if isinstance(data, float) and not math.isfinite(data):
        return errors + [f"{path}: non-finite number is not valid JSON"]
    if schema is True:
        return errors
    if schema is False:
        return [f"{path}: schema is false"]
    if not isinstance(schema, dict):
        return [f"{path}: schema must be an object or boolean"]

    for keyword, relation in (("oneOf", "exactly one"), ("anyOf", "at least one")):
        if keyword not in schema:
            continue
        branches = schema[keyword]
        if not isinstance(branches, list) or not branches:
            errors.append(f"{path}: {keyword} must be a non-empty array")
            continue
        branch_errors = [validate_json_schema(data, branch, path, False) for branch in branches]
        matches = sum(not branch_error for branch_error in branch_errors)
        valid = matches == 1 if keyword == "oneOf" else matches >= 1
        if not valid:
            errors.append(f"{path}: {keyword} must match {relation} schema (matched {matches})")

    if "allOf" in schema:
        branches = schema["allOf"]
        if not isinstance(branches, list):
            errors.append(f"{path}: allOf must be an array")
        else:
            for branch in branches:
                errors.extend(validate_json_schema(data, branch, path, False))

    if "not" in schema and not validate_json_schema(data, schema["not"], path, False):
        errors.append(f"{path}: value must not match the not schema")

    if "type" in schema and not type_matches(data, schema["type"]):
        errors.append(f"{path}: expected {schema['type']}, got {json_type_name(data)}")
        return errors
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: value {data!r} not in enum {schema['enum']!r}")
    if "const" in schema and data != schema["const"]:
        errors.append(f"{path}: value {data!r} does not equal const {schema['const']!r}")

    if isinstance(data, dict):
        required = schema.get("required", [])
        if not isinstance(required, list) or not all(isinstance(key, str) for key in required):
            errors.append(f"{path}: required must be an array of strings")
            required = []
        for key in required:
            if key not in data:
                errors.append(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        if not isinstance(props, dict):
            errors.append(f"{path}: properties must be an object")
            props = {}
        for key, subschema in props.items():
            if key in data:
                errors.extend(validate_json_schema(data[key], subschema, f"{path}.{key}", False))
        additional = schema.get("additionalProperties", True)
        if additional not in (True, False) and not isinstance(additional, dict):
            errors.append(f"{path}: additionalProperties must be boolean or an object")
            additional = False
        for key, value in data.items():
            if key in props or additional is True:
                continue
            if additional is False:
                errors.append(f"{path}: unexpected key {key!r}")
            else:
                errors.extend(validate_json_schema(value, additional, f"{path}.{key}", False))

    if isinstance(data, list):
        items = schema.get("items")
        if items is not None and not isinstance(items, (dict, bool)):
            errors.append(f"{path}: items must be an object or boolean")
        elif isinstance(items, (dict, bool)):
            for i, item in enumerate(data):
                errors.extend(validate_json_schema(item, items, f"{path}[{i}]", False))
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append(f"{path}: array has {len(data)} items, below minimum {schema['minItems']}")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errors.append(f"{path}: array has {len(data)} items, above maximum {schema['maxItems']}")
        if schema.get("uniqueItems"):
            try:
                unique = len({json.dumps(item, sort_keys=True) for item in data}) == len(data)
            except (TypeError, ValueError):
                unique = False
            if not unique:
                errors.append(f"{path}: array items must be unique")

    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"{path}: string length is below minimum {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(f"{path}: string length is above maximum {schema['maxLength']}")
        if "pattern" in schema:
            try:
                matches = re.search(schema["pattern"], data) is not None
            except (re.error, TypeError):
                errors.append(f"{path}: invalid schema pattern")
                matches = True
            if not matches:
                errors.append(f"{path}: value does not match pattern {schema['pattern']!r}")

    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} is below minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} is above maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: {data} is not above exclusive minimum {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and data >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: {data} is not below exclusive maximum {schema['exclusiveMaximum']}")
    return errors


def semantic_receipt_errors(receipt: Any) -> List[str]:
    """Validate receipt integrity that JSON shape alone cannot establish."""
    if not isinstance(receipt, dict):
        return ["receipt must be an object"]
    errors: List[str] = []
    missing = _receipt_text_fields(receipt)
    if missing:
        errors.append("receipt is missing verifier binding fields: " + ", ".join(missing))
    if receipt.get("issuer") != RECEIPT_ISSUER:
        errors.append(f"receipt issuer must be {RECEIPT_ISSUER}")
    receipt_hash = receipt.get("receipt_sha256")
    if isinstance(receipt_hash, str) and re.fullmatch(r"[0-9a-fA-F]{64}", receipt_hash):
        if receipt_hash.lower() != _receipt_binding_digest(receipt).lower():
            errors.append("receipt_sha256 does not cover the bound fields")
    sha256 = receipt.get("sha256")
    subject_digest = receipt.get("subject_digest")
    if (
        isinstance(sha256, str)
        and re.fullmatch(r"[0-9a-fA-F]{64}", sha256)
        and isinstance(subject_digest, str)
        and re.fullmatch(r"[0-9a-fA-F]{64}", subject_digest)
        and sha256.lower() != subject_digest.lower()
    ):
        errors.append("subject_digest must match the registered verification artifact")
    return errors


def validate_artifact(kind: str, data: Any) -> dict:
    schema = load_schema(kind)
    schema_errors = validate_json_schema(data, schema)
    semantic_errors: List[str] = []
    if kind == "report" and not schema_errors:
        semantic_errors = semantic_report_errors(data)
    elif kind == "receipt" and not schema_errors:
        semantic_errors = semantic_receipt_errors(data)
    errors = schema_errors + semantic_errors
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-validation/1",
        "kind": kind,
        "schema_valid": not schema_errors,
        "semantic_valid": not semantic_errors,
        "valid": not errors,
        "errors": errors,
        "semantic_errors": semantic_errors,
    }


def _report_cap_values(caps: Any) -> set[int]:
    values: set[int] = set()
    if not isinstance(caps, list):
        return values
    for cap in caps:
        if isinstance(cap, dict) and isinstance(cap.get("cap"), (int, float)) and not isinstance(cap.get("cap"), bool):
            values.add(int(cap["cap"]))
        elif isinstance(cap, str):
            for value in re.findall(r"\b(49|74|84|90)\b", cap):
                values.add(int(value))
    return values


def semantic_report_errors(report: dict) -> List[str]:
    """Check report conclusions against their own findings and evidence state."""
    errors: List[str] = []
    findings = normalize_findings({"findings": report.get("findings", [])})
    unresolved = [finding for finding in findings if finding.get("status") not in RESOLVED_STATUSES]
    score = report.get("score")
    caps = _report_cap_values(report.get("score_caps"))
    if isinstance(score, int) and not isinstance(score, bool):
        if any(finding.get("severity") == "P0" for finding in unresolved) and score > 49:
            errors.append("report score exceeds the unresolved P0 cap of 49")
        if any(finding.get("severity") == "P1" for finding in unresolved) and score > 74:
            errors.append("report score exceeds the unresolved P1 cap of 74")
    if any(finding.get("severity") == "P0" for finding in unresolved) and 49 not in caps:
        errors.append("report score_caps does not retain the unresolved P0 cap")
    if any(finding.get("severity") == "P1" for finding in unresolved) and 74 not in caps:
        errors.append("report score_caps does not retain the unresolved P1 cap")

    coverage = report.get("coverage") if isinstance(report.get("coverage"), list) else []
    coverage_unknown = False
    for index, row in enumerate(coverage):
        if not isinstance(row, dict):
            continue
        missing = row.get("missing_evidence") or []
        if row.get("checked") is False or missing:
            coverage_unknown = True
        if row.get("checked") is True and not row.get("evidence_reviewed"):
            coverage_unknown = True
    if report.get("confidence") == "high" and (coverage_unknown or len(coverage) < len(SCORE_CATEGORIES)):
        errors.append("high confidence requires complete, checked report coverage with no missing evidence")

    breakdown = report.get("score_breakdown")
    if isinstance(breakdown, list) and breakdown and all(
        isinstance(item, dict) and isinstance(item.get("awarded"), (int, float))
        for item in breakdown
    ):
        ids = {str(item.get("id")) for item in breakdown if item.get("id")}
        if ids >= set(SCORE_CATEGORIES):
            recomputed = round(sum(float(item["awarded"]) for item in breakdown))
            cap = min(caps) if caps else 100
            expected = min(recomputed, cap)
            if isinstance(score, int) and score != expected:
                errors.append(f"report score {score} does not match score_breakdown/caps recomputation {expected}")

    backlog = report.get("remediation_backlog") if isinstance(report.get("remediation_backlog"), list) else []
    backlog_ids = {str(item.get("finding_id")) for item in backlog if isinstance(item, dict) and item.get("finding_id")}
    missing_backlog = sorted(str(finding["id"]) for finding in findings if finding["id"] not in backlog_ids)
    if missing_backlog:
        errors.append("report backlog is missing findings: " + ", ".join(missing_backlog))
    return errors


def parse_report(body: str) -> dict:
    """Parse and validate one complete Production Reality Report."""
    try:
        report = strict_json_loads(body)
    except (ValueError, UnicodeError) as exc:
        raise CliError(f"invalid report JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise CliError("invalid report artifact: report must be a JSON object")
    errors = validate_json_schema(report, load_schema("report"))
    if errors:
        raise CliError("invalid report artifact: " + "; ".join(errors))
    semantic_errors = semantic_report_errors(report)
    if semantic_errors:
        raise CliError("invalid report semantics: " + "; ".join(semantic_errors))
    return report


def regenerate_report(report: dict) -> str:
    """Validate and render a report in canonical, byte-stable JSON form."""
    if not isinstance(report, dict):
        raise CliError("invalid report artifact: report must be a JSON object")
    errors = validate_json_schema(report, load_schema("report"))
    if errors:
        raise CliError("invalid report artifact: " + "; ".join(errors))
    semantic_errors = semantic_report_errors(report)
    if semantic_errors:
        raise CliError("invalid report semantics: " + "; ".join(semantic_errors))
    try:
        return json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise CliError(f"could not regenerate report: {exc}") from exc


def init_project(project: Path, force: bool = False) -> dict:
    project = project.resolve()
    if not project.is_dir():
        raise CliError(f"project root not found: {project}")
    created: List[str] = []
    skipped: List[str] = []
    coverage_path = project / "CHECKYOURSELF_COVERAGE.generated.json"
    context_path = project / "CHECKYOURSELF_PROJECT_CONTEXT.generated.md"
    targets = [
        (coverage_path, json.dumps(coverage_emit(str(project)), indent=2) + "\n"),
        (context_path, render_markdown(project, scan(project))),
    ]
    for path, body in targets:
        if path.exists() and not force:
            skipped.append(str(path))
            continue
        safe_write_text(path, body)
        created.append(str(path))
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-init/1",
        "project": str(project),
        "created": created,
        "skipped": skipped,
    }


def safe_write_text(path: Path, body: str) -> None:
    """Write a generated file, refusing to write through a symlink.

    Generated files land inside scanned (potentially untrusted) directories;
    a pre-planted symlink at the expected name could redirect the write.
    """
    candidate = path
    while True:
        # macOS exposes temporary directories through root-level aliases such
        # as /var and /tmp. They are outside the caller's writable subtree;
        # reject symlinks introduced below those OS-managed aliases.
        if candidate.is_symlink() and candidate.parent != Path(candidate.anchor):
            raise CliError(f"refusing to write through symlink: {path}")
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    temp_fd: Optional[int] = None
    temp_path: Optional[Path] = None
    try:
        temp_fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        temp_path = Path(temp_name)
        with os.fdopen(temp_fd, "w", encoding="utf-8", newline="") as handle:
            temp_fd = None
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_fd is not None:
            os.close(temp_fd)
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def write_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=False, allow_nan=False))


def write_text_result(data: dict) -> None:
    schema = data.get("schema", "")
    if schema == SCAN_SCHEMA_ID:
        c = data["counts"]
        print(f"Scanned {data['files_scanned']} files. Findings — P0: {c['P0']}, P1: {c['P1']}, P2: {c['P2']}, P3: {c['P3']}")
        limits = data.get("scan_limits") or {}
        if limits.get("incomplete"):
            print("  WARNING: scan incomplete; skipped, unreadable, oversized, or truncated inputs may hide findings.")
        if limits.get("truncated"):
            print(f"  WARNING: scan truncated at {limits.get('max_files')} files; "
                  f"{limits.get('files_beyond_limit')} files were not scanned. Rerun with --max-files.")
        for f in data["findings"]:
            print(f"  [{f['severity']}] {f['id']} {f['finding']}")
        print("Next: run the full CheckYourself diagnostic, then use score/backlog/next for deterministic receipts.")
    elif schema == SCORE_SCHEMA_ID:
        print(f"Score: {data['score']} ({data['confidence']} confidence, raw {data['raw_score']})")
        for cap in data["caps_applied"]:
            print(f"  cap {cap['cap']}: {cap['reason']}")
    elif schema in {"checkyourself-backlog/1", "checkyourself-next-batch/1"}:
        if schema == "checkyourself-next-batch/1":
            ids = data.get("finding_ids") or []
        else:
            ids = data.get("highest_severity_batch") or data.get("first_approval_batch") or []
        print("Next batch: " + (", ".join(ids) if ids else "none"))
    else:
        write_json(data)


def resolve_history_path(findings_path: str, requested: Optional[str]) -> Optional[Path]:
    if requested == "none":
        return None
    if requested == "":
        if findings_path == "-":
            return Path.cwd() / DEFAULT_SCORE_HISTORY_PATH
        return Path(findings_path).resolve().parent / DEFAULT_SCORE_HISTORY_PATH
    if requested:
        return Path(requested)
    # Scoring is read-only by default. Persist a score history only when the
    # caller explicitly supplies --history.
    return None


def append_score_history(path: Optional[Path], result: dict, note: str = "") -> None:
    if path is None:
        return
    entry = {
        "timestamp": result["generated_at"],
        "score": result["score"],
        "raw_score": result["raw_score"],
        "confidence": result["confidence"],
        "score_mode": result.get("score_mode"),
        "counts": result["counts"],
        "findings": result["findings_scored"],
        "note": note,
    }
    history: List[dict] = []
    if path.exists():
        try:
            parsed = strict_json_loads(path.read_text(encoding="utf-8"))
            if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
                raise ValueError("score history must be a JSON array of objects")
            history = parsed
        except (ValueError, UnicodeError):
            # Never silently destroy the audit trail: preserve the corrupt
            # file and warn before starting a fresh history.
            backup = path.with_name(path.name + ".corrupt.bak")
            try:
                path.replace(backup)
                print(f"warning: score history was corrupt; preserved at {backup}", file=sys.stderr)
            except OSError:
                print("warning: score history was corrupt and could not be backed up", file=sys.stderr)
            history = []
    history.append(entry)
    safe_write_text(path, json.dumps(history, indent=2, allow_nan=False) + "\n")


def command_scan(args: argparse.Namespace) -> int:
    root = Path(args.project).resolve()
    if not root.is_dir():
        raise CliError(f"project root not found: {root}")
    data = scan(root, deep=getattr(args, "deep", False), max_files=getattr(args, "max_files", DEFAULT_MAX_FILES))
    json_stdout = args.format == "json" or args.json == "-" or (args.no_write and args.json is not None)

    if not args.no_write and args.out is not None:
        out = Path(args.out)
        if not out.is_absolute():
            out = Path.cwd() / out
        safe_write_text(out, render_markdown(root, data))
        if not args.quiet and not json_stdout:
            print(f"Wrote context: {out}")

    if not args.no_write and args.json is not None and args.json != "-":
        jout = Path(args.json)
        if not jout.is_absolute():
            jout = Path.cwd() / jout
        safe_write_text(jout, json.dumps(data, indent=2, allow_nan=False) + "\n")
        if not args.quiet and not json_stdout:
            print(f"Wrote JSON:    {jout}")

    if json_stdout:
        write_json(data)
    elif not args.quiet:
        write_text_result(data)

    if args.ci and data["counts"].get("P0", 0) > 0:
        return 1
    return 0


def command_describe(args: argparse.Namespace) -> int:
    data = describe_capabilities()
    if args.format == "json":
        write_json(data)
    else:
        print(f"CheckYourself {data['version']} commands:")
        for command in data["commands"]:
            print(f"- {command['name']}: {command['summary']}")
    return 0


def command_schema(args: argparse.Namespace) -> int:
    write_json(load_schema(args.name))
    return 0


def command_coverage(args: argparse.Namespace) -> int:
    if args.check:
        data = load_json_arg(args.check)
        evidence_root = Path.cwd() if args.check == "-" else Path(args.check).resolve().parent
        result = coverage_check(data, evidence_root)
        if args.format == "json":
            write_json(result)
        else:
            print("Coverage complete" if result["complete"] else "Coverage incomplete")
            for error in result["errors"]:
                print(f"- {error}")
            for warning in result["warnings"]:
                print(f"- warning: {warning}")
        return 0 if result["complete"] else 1
    data = coverage_emit(args.project or "")
    out_path = args.out
    if not out_path and args.format == "text":
        out_path = DEFAULT_COVERAGE_PATH
    if out_path:
        safe_write_text(Path(out_path), json.dumps(data, indent=2, allow_nan=False) + "\n")
    if args.format == "json":
        write_json(data)
    else:
        print(f"Wrote coverage skeleton: {out_path}")
        print("Fill coverage.json with evidence, then re-run score.")
    return 0


def command_receipt(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise CliError(f"receipt evidence root not found: {root}")
    receipt = issue_receipt(
        args.reference,
        root,
        surface_id=args.surface_id,
        source_revision=args.source_revision,
        command=args.command,
        claim=args.claim,
        result=args.result,
        source_state=args.source_state,
        subject_digest=args.subject_digest,
    )
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = Path.cwd() / out
        safe_write_text(out, json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    if args.format == "json":
        write_json(receipt)
    else:
        if args.out:
            print(f"Wrote verifier receipt: {args.out}")
        else:
            print(json.dumps(receipt, indent=2, allow_nan=False))
    return 0


def command_score(args: argparse.Namespace) -> int:
    findings_data = load_json_arg(args.findings)
    if args.coverage is not None:
        coverage_root = Path.cwd() if args.coverage == "-" else Path(args.coverage).resolve().parent
        result = score_from_inputs(
            findings_data,
            load_json_arg(args.coverage),
            evidence_root=coverage_root,
            claim=args.claim,
        )
    else:
        result = score_from_inputs(findings_data, claim=args.claim)
    history_path = resolve_history_path(args.findings, args.history)
    append_score_history(history_path, result, args.note)
    if args.format == "json":
        write_json(result)
    else:
        write_text_result(result)
        if history_path is not None:
            print(f"History: {history_path}")
    return 0


def command_backlog(args: argparse.Namespace) -> int:
    data = load_json_arg(args.findings)
    result = backlog_from_findings(data)
    if args.format == "json":
        write_json(result)
    else:
        write_text_result(result)
    return 0


def command_next(args: argparse.Namespace) -> int:
    data = load_json_arg(args.findings)
    result = next_from_findings(data)
    if args.format == "json":
        write_json(result)
    else:
        write_text_result(result)
    return 0


def command_diff(args: argparse.Namespace) -> int:
    result = diff_findings(load_json_arg(args.old), load_json_arg(args.new))
    if args.format == "json":
        write_json(result)
    else:
        added = result["added"]
        resolved = result["resolved"]
        print(f"Added: {len(added)}, Resolved: {len(resolved)}, Unchanged: {len(result['unchanged'])}")
        for f in added:
            print(f"  + [{f['severity']}] {f['id']} {f['finding']}")
        for f in resolved:
            print(f"  - [{f['severity']}] {f['id']} {f['finding']}")
        for event in result["regressions"]:
            print(f"  ! [{event['type']}] {event['id']}")
        if result["count_regression"]:
            print("  ! [count_increased] open P0/P1 count increased against the baseline.")
    if args.ci and result["regression"]:
        return 1
    return 0


def command_validate(args: argparse.Namespace) -> int:
    data = load_json_arg(args.file)
    result = validate_artifact(args.kind, data)
    if args.format == "json":
        write_json(result)
    else:
        print("Valid" if result["valid"] else "Invalid")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["valid"] else 1


def command_init(args: argparse.Namespace) -> int:
    result = init_project(Path(args.project), force=args.force)
    if args.format == "json":
        write_json(result)
    else:
        for path in result["created"]:
            print(f"Created: {path}")
        for path in result["skipped"]:
            print(f"Skipped existing: {path}")
    return 0


def mcp_tools() -> List[dict]:
    schema_names = sorted(schema_registry().keys())

    def read_only_annotations(title: str) -> dict:
        return {
            "title": title,
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }

    def object_schema(properties: dict, required: Optional[List[str]] = None) -> dict:
        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return schema

    def description(*parts: str) -> str:
        safety = (
            "Requires no authentication. It reads local inputs only, does not make network calls, "
            "does not modify local files, and has no external rate limits."
        )
        return " ".join([*parts, safety])

    def findings_schema(action: str) -> dict:
        return {
            "type": ["object", "array"],
            "description": (
                "Scan result object, CheckYourself report object, object with findings/remediation_backlog, "
                f"or a plain list of finding objects to {action}."
            ),
        }

    return [
        {
            "name": "describe",
            "title": "Describe CheckYourself",
            "description": description(
                "Return CheckYourself's machine-readable capability manifest: CLI commands, MCP transport, schema names, "
                "scoring weights, score caps, coverage surfaces, exit codes, and public-repository scope guardrails. "
                "This is a read-only discovery tool and does not scan a project."
            ),
            "inputSchema": object_schema({}),
            "annotations": read_only_annotations("Describe CheckYourself"),
            "outputSchema": {"type": "object", "description": "Capability manifest using schema checkyourself-capabilities/1."},
        },
        {
            "name": "scan",
            "title": "Scan Project",
            "description": description(
                "Inspect a local project directory for deterministic production-readiness signals: stack, scripts, CI, tests, "
                "environment files, obvious secret/config risks, generated findings, counts, and public-repo claim guardrails. "
                "MCP mode returns JSON only; it does not write generated files or apply fixes."
            ),
            "inputSchema": object_schema({
                "project": {
                    "type": "string",
                    "description": "Project root path to inspect, confined to CHECKYOURSELF_SCAN_ROOT (default: the MCP server process current directory).",
                },
                "deep": {
                    "type": "boolean",
                    "description": "Run slower validation checks for detected surfaces, such as mutable GitHub Action references. Defaults to false.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum files to scan before truncating (default 6000). The result reports skipped inputs and incompleteness in scan_limits.",
                },
            }),
            "annotations": read_only_annotations("Scan Project"),
            "outputSchema": {"type": "object", "description": "Scan result using schema checkyourself-scan/1."},
        },
        {
            "name": "coverage_emit",
            "title": "Emit Coverage Skeleton",
            "description": description(
                "Return the 20-surface CheckYourself coverage skeleton that an agent fills with manual evidence, missing-evidence notes, "
                "and not-applicable reasons before coverage-backed scoring. In MCP mode this only returns the skeleton object; it does not create a file."
            ),
            "inputSchema": object_schema({
                "project": {
                    "type": "string",
                    "description": "Optional project label or path to include in the returned coverage skeleton.",
                },
            }),
            "annotations": read_only_annotations("Emit Coverage Skeleton"),
            "outputSchema": {"type": "object", "description": "Coverage skeleton using schema checkyourself-coverage/1."},
        },
        {
            "name": "coverage_check",
            "title": "Check Coverage",
            "description": description(
                "Validate an inline CheckYourself coverage object for required surfaces, valid statuses, reviewed evidence, "
                "missing-evidence notes, and not-applicable reasons. Returns errors and warnings; it does not calculate a score."
            ),
            "inputSchema": object_schema({
                "coverage": {
                    "type": "object",
                    "description": "Coverage object produced by coverage_emit and filled with evidence statuses.",
                },
            }, ["coverage"]),
            "annotations": read_only_annotations("Check Coverage"),
            "outputSchema": {"type": "object", "description": "Coverage completeness result using schema checkyourself-coverage-check/1."},
        },
        {
            "name": "receipt_issue",
            "title": "Issue Verifier Receipt",
            "description": description(
                "Issue one verifier-hashed receipt only for an existing, registered surface-specific verification artifact under the configured MCP scan root. "
                "The result is returned inline and is not written to disk."
            ),
            "inputSchema": object_schema({
                "reference": {"type": "string", "description": "In-root registered verification artifact path to hash."},
                "surface_id": {"type": "string", "description": "Canonical coverage surface ID."},
                "source_revision": {"type": "string", "description": "Source revision examined."},
                "source_state": {"type": "string", "description": "Source/environment state examined."},
                "command": {"type": "string", "description": "Command recorded at issuance."},
                "claim": {"type": "string", "description": "One claim proved by the receipt."},
                "result": {"type": "string", "description": "Observed result recorded at issuance."},
                "subject_digest": {"type": "string", "description": "Optional content hash assertion for the registered verification artifact."},
            }, ["reference", "surface_id", "source_revision", "source_state", "command", "claim", "result"]),
            "annotations": read_only_annotations("Issue Verifier Receipt"),
            "outputSchema": {"type": "object", "description": "Verifier receipt using schema checkyourself-receipt/1."},
        },
        {
            "name": "score",
            "title": "Score Findings",
            "description": description(
                "Compute a deterministic Production Reality Score from inline findings and optional coverage evidence. "
                "Returns score, raw score, confidence, score mode, severity counts, caps applied, per-category penalties, "
                "and manual evidence still needed. MCP mode does not write score history."
            ),
            "inputSchema": object_schema({
                "findings": findings_schema("normalize and score"),
                "coverage": {
                    "type": ["object", "null"],
                    "description": "Optional filled coverage object. Provide this for coverage-backed scoring; omit for scan-derived or finding-only estimates.",
                },
                "claim": {
                    "type": "string",
                    "description": "Optional accepted completion claim. This records the claim but does not execute an independent challenge runner.",
                },
            }, ["findings"]),
            "annotations": read_only_annotations("Score Findings"),
            "outputSchema": {"type": "object", "description": "Score result using schema checkyourself-score/1."},
        },
        {
            "name": "backlog",
            "title": "Rank Backlog",
            "description": description(
                "Normalize inline findings and return the complete remediation backlog sorted by severity, category, and finding ID. "
                "The highest_severity_batch is a deterministic severity slice; safety and dependency analysis are not performed. "
                "Each item includes fix summary, order rationale, verification, rollback idea, learning value, and status. "
                "This recommends work only; it does not modify files or mark findings resolved."
            ),
            "inputSchema": object_schema({
                "findings": findings_schema("convert into a remediation backlog"),
            }, ["findings"]),
            "annotations": read_only_annotations("Rank Backlog"),
            "outputSchema": {"type": "object", "description": "Backlog result using schema checkyourself-backlog/1."},
        },
        {
            "name": "next",
            "title": "Next Approval Batch",
            "description": description(
                "Return the next highest-severity unresolved approval batch from inline findings by reusing the backlog ranking rules. "
                "The batch contains at most the first three unresolved findings at the highest current severity; safety and dependency analysis are not performed. "
                "This is a planning tool only and does not perform fixes."
            ),
            "inputSchema": object_schema({
                "findings": findings_schema("batch into the next approval group"),
            }, ["findings"]),
            "annotations": read_only_annotations("Next Approval Batch"),
            "outputSchema": {"type": "object", "description": "Next-batch result using schema checkyourself-next-batch/1."},
        },
        {
            "name": "diff",
            "title": "Diff Findings",
            "description": description(
                "Compare two inline findings artifacts (scan results, reports, or finding lists) and return added, "
                "resolved, unchanged, status and severity transitions, evidence-level changes, severity count deltas, and "
                "a regression flag that is true for newly open, reopened, or escalated P0/P1 findings or increased counts. "
                "Use this to gate changes against a baseline."
            ),
            "inputSchema": object_schema({
                "old": findings_schema("treat as the baseline"),
                "new": findings_schema("treat as the current state"),
            }, ["old", "new"]),
            "annotations": read_only_annotations("Diff Findings"),
            "outputSchema": {"type": "object", "description": "Diff result using schema checkyourself-diff/1."},
        },
        {
            "name": "validate",
            "title": "Validate Artifact",
            "description": description(
                "Validate an inline JSON artifact against one bundled CheckYourself schema subset and return validation errors. "
                "Supported kinds include scan, coverage, score, backlog, next, diff, report, dashboard, dashboard-data, learning-plan, and capabilities."
            ),
            "inputSchema": object_schema({
                "kind": {
                    "type": "string",
                    "enum": schema_names,
                    "description": "Bundled schema kind to validate against.",
                },
                "artifact": {
                    "type": "object",
                    "description": "Inline JSON object to validate. MCP mode does not read a file path for this tool.",
                },
            }, ["kind", "artifact"]),
            "annotations": read_only_annotations("Validate Artifact"),
            "outputSchema": {"type": "object", "description": "Validation result using schema checkyourself-validation/1."},
        },
        {
            "name": "schema",
            "title": "Get Schema",
            "description": description(
                "Return a bundled CheckYourself JSON schema by name so an agent can inspect expected fields before producing or validating artifacts. "
                "This reads the repository's schema file and returns it; it does not validate an artifact."
            ),
            "inputSchema": object_schema({
                "name": {
                    "type": "string",
                    "enum": schema_names,
                    "description": "Schema name to return.",
                },
            }, ["name"]),
            "annotations": read_only_annotations("Get Schema"),
            "outputSchema": {"type": "object", "description": "The requested bundled JSON schema."},
        },
    ]


def mcp_scan_root() -> Path:
    return Path(os.environ.get("CHECKYOURSELF_SCAN_ROOT") or os.getcwd()).resolve()


def resolve_mcp_scan_path(requested: str) -> Path:
    """Confine MCP-initiated scans to a configured root.

    The MCP server is driven by agents with attacker-influenceable arguments,
    so an absolute path like /etc or ~/.aws must not be scannable unless the
    operator deliberately widened the boundary via CHECKYOURSELF_SCAN_ROOT.
    """
    base = mcp_scan_root()
    candidate = Path(requested) if requested else base
    if not candidate.is_absolute():
        candidate = base / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise CliError(
            f"scan path {resolved} is outside the allowed scan root {base}. "
            "Set CHECKYOURSELF_SCAN_ROOT to widen the boundary deliberately.",
            code=2,
        )
    if not resolved.is_dir():
        raise CliError(f"project root not found: {resolved}", code=2)
    return resolved


def call_mcp_tool(name: str, arguments: dict) -> dict:
    if name == "describe":
        return describe_capabilities()
    if name == "scan":
        project = resolve_mcp_scan_path(str(arguments.get("project") or ""))
        max_files = int(arguments.get("max_files") or DEFAULT_MAX_FILES)
        return scan(project, deep=bool(arguments.get("deep")), max_files=max_files)
    if name == "coverage_emit":
        return coverage_emit(str(arguments.get("project") or ""))
    if name == "coverage_check":
        return coverage_check(arguments.get("coverage") or {}, mcp_scan_root())
    if name == "receipt_issue":
        return issue_receipt(
            str(arguments.get("reference") or ""),
            mcp_scan_root(),
            surface_id=str(arguments.get("surface_id") or ""),
            source_revision=str(arguments.get("source_revision") or ""),
            source_state=str(arguments.get("source_state") or ""),
            command=str(arguments.get("command") or ""),
            claim=str(arguments.get("claim") or ""),
            result=str(arguments.get("result") or ""),
            subject_digest=arguments.get("subject_digest"),
        )
    if name == "score":
        findings = arguments.get("findings") or {}
        if "coverage" in arguments:
            return score_from_inputs(
                findings,
                arguments["coverage"],
                evidence_root=mcp_scan_root(),
                claim=arguments.get("claim"),
            )
        return score_from_inputs(findings, claim=arguments.get("claim"))
    if name == "backlog":
        return backlog_from_findings(arguments.get("findings") or {})
    if name == "next":
        return next_from_findings(arguments.get("findings") or {})
    if name == "diff":
        return diff_findings(arguments.get("old") or {}, arguments.get("new") or {})
    if name == "validate":
        return validate_artifact(str(arguments.get("kind")), arguments.get("artifact"))
    if name == "schema":
        return load_schema(str(arguments.get("name")))
    raise CliError(f"unknown MCP tool: {name}")


def mcp_success(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def mcp_error(request_id: Any, code: int, message: str, data: Optional[dict] = None) -> dict:
    error: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def mcp_tool_result(data: dict, is_error: bool = False) -> dict:
    text = json.dumps(data, indent=2, allow_nan=False)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": data,
        "isError": is_error,
    }


def handle_mcp_message(message: dict) -> Optional[dict]:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if method == "initialize":
        requested = str(params.get("protocolVersion") or MCP_PROTOCOL_VERSION)
        protocol = requested if requested in SUPPORTED_MCP_PROTOCOLS else MCP_PROTOCOL_VERSION
        return mcp_success(request_id, {
            "protocolVersion": protocol,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {
                "name": "checkyourself",
                "title": "CheckYourself",
                "version": read_manifest_version(),
                "description": "Local-first production-readiness diagnostic tools.",
            },
            "instructions": (
                "Use CheckYourself read-only first. Scan, fill coverage with evidence, "
                "score, rank backlog, ask before fixes. For public repository claims, "
                "name exact owner namespaces, repository counts, verification timestamps, "
                "live evidence surfaces, and fork exclusions before saying all or 100%."
            ),
        })
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return mcp_success(request_id, {})
    if method == "tools/list":
        return mcp_success(request_id, {"tools": mcp_tools()})
    if method == "tools/call":
        name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return mcp_error(request_id, -32602, "tools/call arguments must be an object")
        tools_by_name = {tool["name"]: tool for tool in mcp_tools()}
        if name not in tools_by_name:
            return mcp_error(request_id, -32602, f"unknown tool: {name}. Known tools: {', '.join(sorted(tools_by_name))}")
        input_schema = tools_by_name[name].get("inputSchema") or {}
        allowed = set((input_schema.get("properties") or {}).keys())
        unknown = sorted(set(arguments) - allowed)
        if unknown:
            # Silently ignoring a misspelled argument (e.g. `path` instead of
            # `project`) made the tool scan the wrong directory and report
            # success. Reject unknown keys loudly instead.
            return mcp_error(
                request_id, -32602,
                f"unknown argument(s) for {name}: {', '.join(unknown)}. "
                f"Allowed: {', '.join(sorted(allowed)) or 'none'}",
            )
        missing = sorted(set(input_schema.get("required") or []) - set(arguments))
        if missing:
            return mcp_error(request_id, -32602, f"missing required argument(s) for {name}: {', '.join(missing)}")
        type_errors = validate_json_schema(arguments, input_schema)
        if type_errors:
            return mcp_error(
                request_id, -32602,
                f"invalid argument value(s) for {name}: {'; '.join(type_errors)}",
            )
        try:
            data = call_mcp_tool(name, arguments)
            return mcp_success(request_id, mcp_tool_result(data))
        except CliError as exc:
            return mcp_success(request_id, mcp_tool_result({"error": str(exc), "code": exc.code}, is_error=True))
        except Exception as exc:  # pragma: no cover - defensive protocol boundary.
            return mcp_success(request_id, mcp_tool_result({"error": str(exc)}, is_error=True))
    if request_id is None:
        return None
    return mcp_error(request_id, -32601, f"method not found: {method}")


def run_mcp_server() -> int:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = strict_json_loads(raw)
        except (ValueError, UnicodeError) as exc:
            response = mcp_error(None, -32700, f"parse error: {exc}")
        else:
            if not isinstance(message, dict):
                # JSON-RPC batch arrays would otherwise crash on .get().
                sys.stdout.write(json.dumps(mcp_error(None, -32600, "batch requests are not supported; send one JSON-RPC object per line"), separators=(",", ":"), allow_nan=False) + "\n")
                sys.stdout.flush()
                continue
            try:
                response = handle_mcp_message(message)
            except Exception as exc:  # pragma: no cover - defensive protocol boundary.
                traceback.print_exc(file=sys.stderr)
                response = mcp_error(message.get("id"), -32603, str(exc))
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":"), allow_nan=False) + "\n")
            sys.stdout.flush()
    return 0


def add_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project", nargs="?", default=".", help="Project root to scan (default: .)")
    parser.add_argument("--out",
                        help="Write Markdown context to this path (scans are stdout-only by default)")
    parser.add_argument("--json", nargs="?", const="CHECKYOURSELF_SCAN.generated.json", default=None,
                        help="Also write a JSON summary (default path: CHECKYOURSELF_SCAN.generated.json). Use - for stdout.")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="Console output format. Use json for machine-readable stdout.")
    parser.add_argument("--ci", action="store_true",
                        help="Exit non-zero if any P0 finding is detected.")
    parser.add_argument("--deep", action="store_true",
                        help="Run slower validation checks for detected surfaces, such as mutable CI actions and dependency-update coverage.")
    parser.add_argument("--no-write", action="store_true", help="Print the summary only; write no files.")
    parser.add_argument("--quiet", action="store_true", help="Suppress the console summary.")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES,
                        help=f"Maximum files to scan before truncating (default {DEFAULT_MAX_FILES}). Truncation is disclosed in scan_limits.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="checkyourself",
        description="Local deterministic interface for CheckYourself diagnostics.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("describe", help="Emit the machine-readable capability manifest.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_describe)

    p = sub.add_parser("scan", help="Scan a project and emit deterministic local findings.")
    add_scan_args(p)
    p.set_defaults(func=command_scan)

    p = sub.add_parser("diagnostic", help="Alias for scan; emits deterministic evidence for the manual diagnostic workflow.")
    add_scan_args(p)
    p.set_defaults(func=command_scan)

    p = sub.add_parser("schema", help="Print a bundled schema by name.")
    p.add_argument("name", choices=sorted(schema_registry().keys()))
    p.set_defaults(func=command_schema)

    p = sub.add_parser("coverage", help="Emit or check the 20-surface coverage matrix.")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--emit", action="store_true", help="Emit the coverage skeleton (default).")
    group.add_argument("--check", help="Validate a filled coverage JSON file.")
    p.add_argument("--project", default="", help="Optional project label for emitted coverage.")
    p.add_argument("--out", help="Write emitted coverage JSON to this path.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_coverage)

    p = sub.add_parser("receipt", help="Issue one verifier-hashed receipt for a registered surface artifact.")
    p.add_argument("--reference", required=True, help="In-root registered verification artifact path to hash.")
    p.add_argument("--surface-id", required=True, choices=[sid for sid, _surface, _category in COVERAGE_SURFACES], help="Canonical coverage surface this receipt proves.")
    p.add_argument("--source-revision", required=True, help="Source revision examined when the receipt was issued.")
    p.add_argument("--source-state", required=True, help="Source/environment state examined when the receipt was issued.")
    p.add_argument("--command", required=True, help="Command recorded at issuance.")
    p.add_argument("--claim", required=True, help="One claim proved by this receipt.")
    p.add_argument("--result", required=True, help="Observed result recorded at issuance.")
    p.add_argument("--subject-digest", help="Optional content hash assertion for the registered verification artifact.")
    p.add_argument("--root", default=".", help="Evidence root containing the referenced artifact (default: current directory).")
    p.add_argument("--out", help="Write the receipt JSON to this path.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_receipt)

    p = sub.add_parser("score", help="Compute deterministic Production Reality Score.")
    p.add_argument("--findings", required=True, help="JSON file containing findings, scan output, or report.")
    p.add_argument("--coverage", help="Optional coverage JSON file.")
    p.add_argument("--history", nargs="?", const="",
                   help="Write score history to this path (or beside findings when supplied without a path; disabled by default).")
    p.add_argument("--no-history", dest="history", action="store_const", const="none",
                   help="Do not append score history.")
    p.add_argument("--note", default="", help="Optional note stored with the score history entry.")
    p.add_argument("--claim", help="Optional accepted completion claim to record; evidence remains unbound unless coverage marks it explicitly.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_score)

    p = sub.add_parser("backlog", help="Rank the complete remediation backlog.")
    p.add_argument("--findings", required=True, help="JSON file containing findings, scan output, or report.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_backlog)

    p = sub.add_parser("next", help="Return the next highest-severity unresolved approval batch; safety analysis is not performed.")
    p.add_argument("--findings", required=True, help="JSON file containing findings, scan output, or report.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_next)

    p = sub.add_parser("diff", help="Compare two findings artifacts and report added/resolved/regressed findings.")
    p.add_argument("--old", required=True, help="Baseline findings JSON path, or - for stdin.")
    p.add_argument("--new", required=True, help="Current findings JSON path, or - for stdin.")
    p.add_argument("--ci", action="store_true", help="Exit non-zero for a new/reopened/escalated open P0/P1 finding or an increased open P0/P1 count.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_diff)

    p = sub.add_parser("validate", help="Validate a JSON artifact against a bundled schema.")
    p.add_argument("--kind", required=True, choices=sorted(schema_registry().keys()))
    p.add_argument("file", help="JSON artifact path, or - for stdin.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_validate)

    p = sub.add_parser("init", help="Create starter generated CheckYourself files in a target project.")
    p.add_argument("project", nargs="?", default=".")
    p.add_argument("--force", action="store_true", help="Overwrite existing generated files.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_init)

    p = sub.add_parser("mcp", help="Run the stdio MCP server.")
    p.set_defaults(func=lambda _args: run_mcp_server())
    return parser


def legacy_scan_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="checkyourself",
        description="Optional local scan & scaffold for CheckYourself.",
    )
    add_scan_args(parser)
    args = parser.parse_args(list(argv))
    return command_scan(args)


def main(argv: Optional[List[str]] = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    commands = {"describe", "scan", "diagnostic", "schema", "coverage", "receipt", "score", "backlog", "next", "diff", "validate", "init", "mcp"}
    try:
        if raw and raw[0] in {"-h", "--help"}:
            build_parser().print_help()
            return 0
        if raw and raw[0] not in commands and not raw[0].startswith("-") and not Path(raw[0]).exists():
            # A misspelled command would otherwise be treated as a project
            # path, silently scanning nothing useful.
            import difflib
            close = difflib.get_close_matches(raw[0], sorted(commands), n=1)
            hint = f" Did you mean: {close[0]}?" if close else ""
            raise CliError(f"unknown command or path: {raw[0]}.{hint}")
        if not raw or raw[0] not in commands:
            return legacy_scan_main(raw)
        parser = build_parser()
        args = parser.parse_args(raw)
        return args.func(args)
    except CliError as exc:
        json_requested = any(
            token == "--format=json"
            or (token == "--format" and index + 1 < len(raw) and raw[index + 1] == "json")
            for index, token in enumerate(raw)
        )
        if json_requested:
            # A shell creates `> output.json` before this process starts. Keep
            # that file parseable when a JSON-mode command fails validation.
            write_json({"error": str(exc), "code": exc.code})
        print(f"error: {exc}", file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
