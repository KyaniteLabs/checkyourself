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
import json
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


TOOL_NAME = "checkyourself-cli"
SCAN_SCHEMA_ID = "checkyourself-scan/1"
COVERAGE_SCHEMA_ID = "checkyourself-coverage/1"
SCORE_SCHEMA_ID = "checkyourself-score/1"
CAPABILITIES_SCHEMA_ID = "checkyourself-capabilities/1"
MCP_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_MCP_PROTOCOLS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]

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
}

SECRET_NAME_RE = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|private[_-]?key|client[_-]?secret|access[_-]?key)",
    re.I,
)
SECRET_VALUE_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|private[_-]?key|access[_-]?key)\s*[:=]\s*['\"]?"
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
RESOLVED_STATUSES = {"fixed", "accepted-risk", "deferred", "not-applicable", "suppressed"}

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
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_text(path: Path, max_chars: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


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
    in_suppress = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped == "suppress:":
            in_suppress = True
            continue
        if not in_suppress:
            continue
        if stripped.startswith("- "):
            if current:
                suppressions.append(current)
            current = {}
            stripped = stripped[2:].strip()
            if stripped and ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key.strip()] = parse_scalar(value)
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = parse_scalar(value)

    if current:
        suppressions.append(current)
    return suppressions


def load_checkyourself_config(root: Path) -> dict:
    for name in CONFIG_NAMES:
        path = root / name
        if not path.exists():
            continue
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {"suppress": []}
            except json.JSONDecodeError:
                return {"suppress": [], "config_error": f"{name} could not be parsed as JSON"}
        return {"suppress": parse_minimal_yaml_suppressions(path.read_text(encoding="utf-8"))}
    return {"suppress": []}


def evidence_path(evidence: str) -> str:
    first = evidence.split(" (", 1)[0]
    if ":" in first:
        path, maybe_line = first.rsplit(":", 1)
        if maybe_line.isdigit():
            return path
    return first


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
            if suppression_matches(finding, suppression):
                finding["status"] = "suppressed"
                finding["suppression"] = {
                    "reason": str(suppression.get("reason") or "reviewed suppression"),
                    "reviewed_by": str(suppression.get("reviewed_by") or ""),
                    "reviewed_at": str(suppression.get("reviewed_at") or ""),
                }
                break
    return findings


def iter_files(root: Path, limit: int = 6000) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in IGNORED_DIRS and (not d.startswith(".") or d == ".github")
        ]
        for name in sorted(filenames):
            if len(files) >= limit:
                return files
            p = Path(dirpath) / name
            try:
                if p.stat().st_size > 2_000_000:
                    continue
            except OSError:
                continue
            files.append(p)
    return files


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
        except json.JSONDecodeError:
            signals.append("package.json exists but could not be parsed")

    py_manifests = ["pyproject.toml", "requirements.txt", "Pipfile"]
    py_text = "\n".join(read_text(root / f) for f in py_manifests if (root / f).exists()).lower()
    for dep, label in DEPENDENCY_HINTS.items():
        if dep.lower() in py_text:
            deps_found.setdefault(label, []).append(dep)

    return sorted(signals), scripts, deps_found


def gitignore_entries(root: Path) -> str:
    gi = root / ".gitignore"
    return read_text(gi).lower() if gi.exists() else ""


def scan_env_and_secrets(root: Path, files: List[Path]) -> Tuple[List[str], List[str], List[str], List[str]]:
    env_files: List[str] = []
    real_env_files: List[str] = []
    suspicious_high: List[str] = []
    suspicious_low: List[str] = []
    for p in files:
        rp = rel(root, p)
        name = p.name.lower()
        is_example = name in ENV_EXAMPLE_NAMES
        if name == ".env" or (name.startswith(".env.") and not is_example) or name.endswith(".env"):
            real_env_files.append(rp)
            env_files.append(rp)
        elif is_example:
            env_files.append(rp)
        if p.suffix.lower() in TEXT_EXTENSIONS or name.startswith(".env"):
            text = read_text(p, max_chars=60_000)
            high_seen = False
            low_seen = False
            for line_no, line in enumerate(text.splitlines(), start=1):
                shaped = any(r.search(line) for r in SECRET_SHAPE_RES)
                value_match = SECRET_VALUE_RE.search(line)
                name_match = SECRET_NAME_RE.search(line)
                if shaped:
                    suspicious_high.append(secret_evidence(
                        rp,
                        line_no,
                        "high-confidence credential shape",
                        "credential_shape",
                        "high",
                        line,
                    ))
                    high_seen = True
                elif value_match and name_match:
                    suspicious_low.append(secret_evidence(
                        rp,
                        line_no,
                        "possible secret-like assignment",
                        "secret_name_and_assignment",
                        "low",
                        line,
                    ))
                    low_seen = True
                if high_seen and low_seen:
                    break
    return (
        sorted(set(env_files)),
        sorted(set(real_env_files)),
        sorted(set(suspicious_high))[:50],
        sorted(set(suspicious_low))[:50],
    )


def find_tests(root: Path, files: List[Path]) -> List[str]:
    tests: List[str] = []
    for p in files:
        rp = rel(root, p)
        lower = rp.lower()
        if any(x in lower for x in ("test", "spec", "__tests__", "playwright", "cypress")):
            if p.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".java", ".rb", ".rs"}:
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


def run_deep_checks(root: Path, ci: List[str], gitignore: str) -> List[Finding]:
    findings: List[Finding] = []
    mutable_actions: List[str] = []
    action_re = re.compile(r"uses:\s*['\"]?([^@\s'\"]+)@([^@\s'\"]+)", re.I)
    pinned_sha_re = re.compile(r"^[0-9a-f]{40}$", re.I)

    for workflow in ci:
        if not workflow.startswith(".github/workflows/"):
            continue
        path = root / workflow
        for line_no, line in enumerate(read_text(path).splitlines(), start=1):
            match = action_re.search(line)
            if not match:
                continue
            action, ref = match.groups()
            if not pinned_sha_re.match(ref):
                mutable_actions.append(
                    f"{workflow}:{line_no} (uses {action}@{ref}; pin to a full commit SHA)"
                )

    if mutable_actions:
        findings.append(Finding(
            "CY-000",
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
            "CY-000",
            "P3",
            "No dependency update automation detected",
            "CI exists, but no Dependabot or Renovate configuration was found. Dependency risk can silently age.",
            [".github/dependabot.yml or renovate.json not found"],
            category="C6",
            recommended_fix="Add Dependabot or Renovate for the detected package ecosystems.",
        ))

    missing_gitignore = [pattern for pattern in (".env", "*.pem", "*.key") if pattern.lower() not in gitignore]
    if missing_gitignore:
        findings.append(Finding(
            "CY-000",
            "P3",
            "Sensitive file patterns missing from .gitignore",
            "Common local secret file patterns are not explicitly ignored.",
            [f"missing gitignore pattern: {pattern}" for pattern in missing_gitignore],
            category="C3",
            recommended_fix="Add local secret file patterns to `.gitignore` and verify no matching files were previously committed.",
        ))

    return findings


def path_hints(root: Path, files: List[Path]) -> Dict[str, List[str]]:
    hints: Dict[str, List[str]] = {}
    for p in files:
        rp = rel(root, p)
        lower = rp.lower()
        for needle, label in RISK_PATH_HINTS:
            if needle in lower:
                hints.setdefault(label, []).append(rp)
    return {k: sorted(set(v))[:40] for k, v in sorted(hints.items())}


def tree_sample(root: Path, max_lines: int = 140) -> List[str]:
    lines: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        cur = Path(dirpath)
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
    real_env_files: List[str],
    env_files: List[str],
    suspicious_high: List[str],
    suspicious_low: List[str],
    tests: List[str],
    ci: List[str],
    gitignore: str,
    deps_found: Dict[str, List[str]],
    deep_findings: Optional[List[Finding]] = None,
) -> List[Finding]:
    findings: List[Finding] = []
    n = 0

    def nid() -> str:
        nonlocal n
        n += 1
        return f"CY-{n:03d}"

    if suspicious_high:
        findings.append(Finding(
            nid(), "P0", "High-confidence credential shape in source",
            "One or more files contain a credential-shaped value. "
            "Rotate anything real, move it to environment variables, and confirm it is gitignored.",
            suspicious_high,
            category="C3",
            recommended_fix="Rotate anything real, remove it from source, load it from environment variables, and confirm history exposure.",
        ))

    if suspicious_low:
        findings.append(Finding(
            nid(), "P2", "Possible secret-like field without credential shape",
            "A file contains a secret-like assignment, but no known credential shape was found. "
            "Review it before renaming fields or accepting it as benign.",
            suspicious_low,
            category="C3",
            recommended_fix="Verify whether the value is a credential. If it is benign, add a reviewed `.checkyourself.yml` suppression; if real, move it to environment variables.",
        ))

    env_ignored = ".env" in gitignore
    if real_env_files and not env_ignored:
        findings.append(Finding(
            nid(), "P0", "A real .env file may be committed",
            "A non-example .env file exists and `.env` is not in .gitignore. "
            "If this is tracked by git, secrets are in your history. Gitignore it and rotate.",
            real_env_files,
            category="C3",
            recommended_fix="Add `.env` patterns to `.gitignore`, remove tracked env files, and rotate exposed values.",
        ))
    elif real_env_files:
        findings.append(Finding(
            nid(), "P2", "Local .env present (verify it is not tracked)",
            "A non-example .env exists; `.env` is in .gitignore, but confirm it was never committed earlier.",
            real_env_files,
            category="C3",
            recommended_fix="Run git history/secret checks and keep only redacted `.env.example` files in the repo.",
        ))

    has_example = any(Path(e).name.lower() in ENV_EXAMPLE_NAMES for e in env_files)
    if real_env_files and not has_example:
        findings.append(Finding(
            nid(), "P1", "No .env.example for required configuration",
            "The app uses environment variables but ships no .env.example. New contributors and "
            "deploys can miss required config. Add a documented example with no real values.",
            real_env_files,
            category="C3",
            recommended_fix="Add `.env.example` with variable names, safe placeholders, and setup notes.",
        ))

    if not tests:
        findings.append(Finding(
            nid(), "P1", "No automated tests detected",
            "No test files were found. At minimum, add tests around auth, money, and data-loss paths.",
            [],
            category="C5",
            recommended_fix="Add the smallest regression tests around the highest-risk user paths.",
        ))

    if not ci:
        findings.append(Finding(
            nid(), "P2", "No CI pipeline detected",
            "No CI configuration found. A CI gate catches regressions before they reach users.",
            [],
            category="C6",
            recommended_fix="Add a minimal CI workflow that installs, builds, tests, and runs secret checks.",
        ))

    if "Stripe/payments" in deps_found and not tests:
        findings.append(Finding(
            nid(), "P1", "Payments present but no tests",
            "A payments dependency was detected with no tests. Payment flows are high-blast-radius; "
            "add negative and webhook tests.",
            [],
            category="C4",
            recommended_fix="Add payment success, failure, idempotency, and webhook signature tests.",
        ))

    for finding in deep_findings or []:
        n += 1
        finding.id = f"CY-{n:03d}"
        findings.append(finding)

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.id))
    return findings


def scan(root: Path, deep: bool = False) -> dict:
    root = root.resolve()
    files = iter_files(root)
    stack_signals, scripts, deps_found = detect_stack(root)
    env_files, real_env_files, suspicious_high, suspicious_low = scan_env_and_secrets(root, files)
    tests = find_tests(root, files)
    ci = find_ci(root)
    hints = path_hints(root, files)
    gitignore = gitignore_entries(root)
    deep_results = run_deep_checks(root, ci, gitignore) if deep else []
    findings = build_findings(
        real_env_files,
        env_files,
        suspicious_high,
        suspicious_low,
        tests,
        ci,
        gitignore,
        deps_found,
        deep_results,
    )
    config = load_checkyourself_config(root)
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
        "stack_signals": stack_signals,
        "dependencies": {k: sorted(set(v)) for k, v in sorted(deps_found.items())},
        "scripts": scripts,
        "env_files": env_files,
        "tests": tests,
        "ci": ci,
        "risk_surfaces": hints,
        "findings": finding_dicts,
        "counts": counts,
        "suppression_count": suppression_count,
        "tree": tree_sample(root),
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
    add("produce the complete remediation backlog and the safest first approval batch, and generate")
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
                "missing_evidence": [],
                "not_applicable_reason": "",
            }
            for sid, surface, category in COVERAGE_SURFACES
        ],
    }


def coverage_check(data: dict) -> dict:
    errors: List[str] = []
    warnings: List[str] = []
    surfaces = data.get("surfaces") or data.get("coverage") or []
    if not isinstance(surfaces, list):
        raise CliError("coverage artifact must contain a surfaces array")

    by_id = {str(item.get("id")): item for item in surfaces if isinstance(item, dict) and item.get("id")}
    by_name = {str(item.get("surface") or item.get("category")): item for item in surfaces if isinstance(item, dict)}
    valid_statuses = {"Pass", "Finding", "Unknown", "NotApplicable"}

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
        if status == "Unknown" and not missing:
            warnings.append(f"{sid} is Unknown but missing_evidence is empty")
        if status == "NotApplicable" and not item.get("not_applicable_reason"):
            errors.append(f"{sid} is NotApplicable but has no not_applicable_reason")

    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-coverage-check/1",
        "complete": not errors,
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
        category = str(raw.get("category") or infer_category(title + " " + detail))
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


def category_coverage(coverage_data: Optional[dict]) -> Tuple[Dict[str, dict], bool]:
    category_state: Dict[str, dict] = {
        cid: {
            "status": "MissingCoverage",
            "evidence_reviewed": [],
            "missing_evidence": ["coverage artifact was not supplied"],
            "surfaces": [],
        }
        for cid in SCORE_CATEGORIES
    }
    if not coverage_data:
        return category_state, False

    surfaces = coverage_data.get("surfaces") or coverage_data.get("coverage") or []
    if not isinstance(surfaces, list):
        return category_state, False

    category_state = {
        cid: {"status": "NotApplicable", "evidence_reviewed": [], "missing_evidence": [], "surfaces": []}
        for cid in SCORE_CATEGORIES
    }
    represented = set()
    status_rank = {"Finding": 3, "Unknown": 2, "Pass": 1, "NotApplicable": 0}

    for item in surfaces:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "")
        if category not in SCORE_CATEGORIES:
            continue
        represented.add(str(item.get("id") or item.get("surface") or category))
        state = category_state[category]
        status = item.get("status") or "Unknown"
        current = state["status"]
        if status_rank.get(status, 2) > status_rank.get(current, 0):
            state["status"] = status
        state["surfaces"].append(str(item.get("id") or item.get("surface") or category))
        state["evidence_reviewed"].extend(str(x) for x in item.get("evidence_reviewed") or [])
        state["missing_evidence"].extend(str(x) for x in item.get("missing_evidence") or [])

    complete = len({sid for sid, _, _ in COVERAGE_SURFACES}) <= len(
        {str(item.get("id")) for item in surfaces if isinstance(item, dict) and item.get("id")}
    )
    for state in category_state.values():
        state["evidence_reviewed"] = sorted(set(state["evidence_reviewed"]))
        state["missing_evidence"] = sorted(set(state["missing_evidence"]))
    return category_state, complete


def missing_manual_evidence(coverage_by_category: Dict[str, dict]) -> List[dict]:
    needed: List[dict] = []
    for cid, (name, _weight) in SCORE_CATEGORIES.items():
        state = coverage_by_category[cid]
        if state["status"] in {"MissingCoverage", "Unknown"}:
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
        set_state("C3", "Pass", ["scan found no open secret/runtime-config findings"], [], ["S08"])

    tests = scan_data.get("tests") if isinstance(scan_data.get("tests"), list) else []
    if tests:
        set_state("C5", "Pass", [f"detected test evidence: {item}" for item in tests[:10]], [], ["S11"])
    else:
        set_state("C5", "Finding", [], ["no automated tests detected by scan"], ["S11"])

    ci = scan_data.get("ci") if isinstance(scan_data.get("ci"), list) else []
    if ci:
        set_state("C6", "Pass", [f"detected CI evidence: {item}" for item in ci[:10]], [], ["S12"])
    else:
        set_state("C6", "Finding", [], ["no CI workflow detected by scan"], ["S12"])

    return category_state


def score_from_inputs(findings_data: Any, coverage_data: Optional[dict] = None) -> dict:
    findings = normalize_findings(findings_data)
    counts = {sev: 0 for sev in ("P0", "P1", "P2", "P3")}
    unresolved = [f for f in findings if f.get("status") not in RESOLVED_STATUSES]
    for f in unresolved:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    if coverage_data is not None:
        coverage_by_category, coverage_complete = category_coverage(coverage_data)
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

    for cid, (name, weight) in SCORE_CATEGORIES.items():
        category_findings = [f for f in unresolved if f.get("category") == cid]
        coverage_state = coverage_by_category[cid]
        penalties: List[dict] = []
        awarded = float(weight)

        status = coverage_state["status"]
        if status == "Unknown":
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
    apply_missing_coverage_caps = coverage_data is not None
    for cid, state in coverage_by_category.items():
        if apply_missing_coverage_caps and state["status"] in {"Unknown", "MissingCoverage"} and cid in CRITICAL_CATEGORIES:
            critical_gap = True
        if apply_missing_coverage_caps and state["status"] in {"Unknown", "MissingCoverage"} and cid in HIGH_SCORE_GATE_CATEGORIES:
            high_score_gap = True
    if critical_gap:
        cap_value = min(cap_value, 84)
        caps.append({"cap": 84, "reason": "missing evidence in a critical category"})
    if high_score_gap:
        cap_value = min(cap_value, 90)
        caps.append({"cap": 90, "reason": "score above 90 requires evidence for tests, secrets, deploy/rollback, observability, auth, and data boundaries"})

    score = min(raw_score, cap_value)
    if score_mode != "coverage-backed":
        confidence = "low"
    elif coverage_complete and not critical_gap and not any(c["reason"].startswith("coverage") for c in caps):
        confidence = "high"
    elif coverage_complete and not critical_gap:
        confidence = "medium"
    else:
        confidence = "low"

    return {
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
        "findings_scored": [f["id"] for f in unresolved],
        "coverage_complete": coverage_complete,
        "manual_evidence_needed": [] if coverage_data is not None else missing_manual_evidence(coverage_by_category),
    }


def backlog_from_findings(findings_data: Any) -> dict:
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
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-backlog/1",
        "generated_at": now_iso(),
        "remediation_backlog": backlog,
        "first_approval_batch": [item["finding_id"] for item in first],
    }


def next_from_findings(findings_data: Any) -> dict:
    backlog = backlog_from_findings(findings_data)["remediation_backlog"]
    batch = first_batch(backlog)
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-next-batch/1",
        "generated_at": now_iso(),
        "next_approval_batch": batch,
        "finding_ids": [item["finding_id"] for item in batch],
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
        ("score", "Compute a deterministic Production Reality Score from findings and optional coverage, with score history.", {"findings": "json path", "coverage": "optional json path", "history": "optional path"}, SCORE_SCHEMA_ID),
        ("backlog", "Rank remediation backlog and first approval batch.", {"findings": "json path"}, "checkyourself-backlog/1"),
        ("next", "Return the next safest unresolved approval batch.", {"findings": "json path"}, "checkyourself-next-batch/1"),
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
        "coverage_surfaces": [
            {"id": sid, "surface": surface, "category": category}
            for sid, surface, category in COVERAGE_SURFACES
        ],
        "scoring": {
            "categories": [
                {"id": cid, "category": name, "weight": weight}
                for cid, (name, weight) in SCORE_CATEGORIES.items()
            ],
            "severity_penalties": SEVERITY_PENALTIES,
            "caps": [
                {"cap": 49, "condition": "any unresolved P0"},
                {"cap": 74, "condition": "any unresolved P1"},
                {"cap": 84, "condition": "missing evidence in C1/C2/C3"},
                {"cap": 90, "condition": "score above 90 without evidence for key launch gates"},
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
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return str(data.get("version") or "unknown")
    except Exception:
        return "unknown"


def schema_registry() -> Dict[str, str]:
    return {
        "report": "checkyourself-report.schema.json",
        "dashboard": "dashboard-data.schema.json",
        "dashboard-data": "dashboard-data.schema.json",
        "dashboard-html": "checkyourself-dashboard.schema.json",
        "learning-plan": "learning-plan.schema.json",
        "scan": "scan.schema.json",
        "coverage": "coverage.schema.json",
        "score": "score-result.schema.json",
        "backlog": "backlog.schema.json",
        "next": "next-batch.schema.json",
        "capabilities": "capabilities.schema.json",
    }


def load_schema(name: str) -> dict:
    registry = schema_registry()
    if name not in registry:
        raise CliError(f"unknown schema kind: {name}. Known: {', '.join(sorted(registry))}")
    path = SCHEMA_DIR / registry[name]
    if not path.exists():
        raise CliError(f"schema file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_arg(path: str) -> Any:
    if path == "-":
        body = sys.stdin.read()
    else:
        p = Path(path)
        if not p.exists():
            raise CliError(f"JSON file not found: {path}")
        body = p.read_text(encoding="utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
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


def validate_json_schema(data: Any, schema: dict, path: str = "$") -> List[str]:
    errors: List[str] = []
    if not isinstance(schema, dict):
        return errors
    if "type" in schema and not type_matches(data, schema["type"]):
        errors.append(f"{path}: expected {schema['type']}, got {json_type_name(data)}")
        return errors
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: value {data!r} not in enum {schema['enum']!r}")
    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        if isinstance(props, dict):
            for key, subschema in props.items():
                if key in data:
                    errors.extend(validate_json_schema(data[key], subschema, f"{path}.{key}"))
    if isinstance(data, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(data):
            errors.extend(validate_json_schema(item, schema["items"], f"{path}[{i}]"))
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} is below minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} is above maximum {schema['maximum']}")
    return errors


def validate_artifact(kind: str, data: Any) -> dict:
    schema = load_schema(kind)
    errors = validate_json_schema(data, schema)
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-validation/1",
        "kind": kind,
        "valid": not errors,
        "errors": errors,
    }


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
        path.write_text(body, encoding="utf-8")
        created.append(str(path))
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-init/1",
        "project": str(project),
        "created": created,
        "skipped": skipped,
    }


def write_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=False))


def write_text_result(data: dict) -> None:
    schema = data.get("schema", "")
    if schema == SCAN_SCHEMA_ID:
        c = data["counts"]
        print(f"Scanned {data['files_scanned']} files. Findings — P0: {c['P0']}, P1: {c['P1']}, P2: {c['P2']}, P3: {c['P3']}")
        for f in data["findings"]:
            print(f"  [{f['severity']}] {f['id']} {f['finding']}")
        print("Next: run the full CheckYourself diagnostic, then use score/backlog/next for deterministic receipts.")
    elif schema == SCORE_SCHEMA_ID:
        print(f"Score: {data['score']} ({data['confidence']} confidence, raw {data['raw_score']})")
        for cap in data["caps_applied"]:
            print(f"  cap {cap['cap']}: {cap['reason']}")
    elif schema in {"checkyourself-backlog/1", "checkyourself-next-batch/1"}:
        ids = data.get("first_approval_batch") or data.get("finding_ids") or []
        print("Next batch: " + (", ".join(ids) if ids else "none"))
    else:
        write_json(data)


def resolve_history_path(findings_path: str, requested: Optional[str]) -> Optional[Path]:
    if requested == "none":
        return None
    if requested:
        return Path(requested)
    if findings_path == "-":
        return Path.cwd() / DEFAULT_SCORE_HISTORY_PATH
    return Path(findings_path).resolve().parent / DEFAULT_SCORE_HISTORY_PATH


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
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(parsed, list):
                history = [item for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            history = []
    history.append(entry)
    path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def command_scan(args: argparse.Namespace) -> int:
    root = Path(args.project).resolve()
    if not root.is_dir():
        raise CliError(f"project root not found: {root}")
    data = scan(root, deep=getattr(args, "deep", False))
    json_stdout = args.format == "json" or args.json == "-" or (args.no_write and args.json is not None)

    if not args.no_write:
        out = Path(args.out)
        if not out.is_absolute():
            out = Path.cwd() / out
        out.write_text(render_markdown(root, data), encoding="utf-8")
        if not args.quiet and not json_stdout:
            print(f"Wrote context: {out}")
        if args.json is not None and args.json != "-":
            jout = Path(args.json)
            if not jout.is_absolute():
                jout = Path.cwd() / jout
            jout.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
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
        result = coverage_check(data)
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
        path = Path(out_path)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if args.format == "json":
        write_json(data)
    else:
        print(f"Wrote coverage skeleton: {out_path}")
    return 0


def command_score(args: argparse.Namespace) -> int:
    findings_data = load_json_arg(args.findings)
    coverage_data = load_json_arg(args.coverage) if args.coverage else None
    result = score_from_inputs(findings_data, coverage_data)
    history_path = resolve_history_path(args.findings, None if not args.history else args.history)
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
    return [
        {
            "name": "describe",
            "title": "Describe CheckYourself",
            "description": "Return the CheckYourself command, schema, scoring, and MCP capability manifest.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "scan",
            "title": "Scan Project",
            "description": "Run deterministic local discovery and obvious-risk checks against a project path.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Project root path. Defaults to current directory."},
                    "deep": {"type": "boolean", "description": "Run slower validation checks for detected surfaces."},
                },
            },
        },
        {
            "name": "coverage_emit",
            "title": "Emit Coverage Skeleton",
            "description": "Return the 20-surface coverage skeleton for an agent to fill with evidence.",
            "inputSchema": {"type": "object", "properties": {"project": {"type": "string"}}},
        },
        {
            "name": "coverage_check",
            "title": "Check Coverage",
            "description": "Check a coverage object for completeness and evidence requirements.",
            "inputSchema": {"type": "object", "properties": {"coverage": {"type": "object"}}, "required": ["coverage"]},
        },
        {
            "name": "score",
            "title": "Score Findings",
            "description": "Compute the deterministic Production Reality Score from findings and optional coverage.",
            "inputSchema": {
                "type": "object",
                "properties": {"findings": {"type": "object"}, "coverage": {"type": "object"}},
                "required": ["findings"],
            },
        },
        {
            "name": "backlog",
            "title": "Rank Backlog",
            "description": "Rank findings into a complete remediation backlog and first approval batch.",
            "inputSchema": {"type": "object", "properties": {"findings": {"type": "object"}}, "required": ["findings"]},
        },
        {
            "name": "next",
            "title": "Next Approval Batch",
            "description": "Return the next safest unresolved approval batch from findings.",
            "inputSchema": {"type": "object", "properties": {"findings": {"type": "object"}}, "required": ["findings"]},
        },
        {
            "name": "validate",
            "title": "Validate Artifact",
            "description": "Validate a JSON artifact against a bundled CheckYourself schema subset.",
            "inputSchema": {
                "type": "object",
                "properties": {"kind": {"type": "string"}, "artifact": {"type": "object"}},
                "required": ["kind", "artifact"],
            },
        },
        {
            "name": "schema",
            "title": "Get Schema",
            "description": "Return a bundled JSON schema by name.",
            "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        },
    ]


def call_mcp_tool(name: str, arguments: dict) -> dict:
    if name == "describe":
        return describe_capabilities()
    if name == "scan":
        return scan(Path(arguments.get("project") or "."), deep=bool(arguments.get("deep")))
    if name == "coverage_emit":
        return coverage_emit(str(arguments.get("project") or ""))
    if name == "coverage_check":
        return coverage_check(arguments.get("coverage") or {})
    if name == "score":
        return score_from_inputs(arguments.get("findings") or {}, arguments.get("coverage"))
    if name == "backlog":
        return backlog_from_findings(arguments.get("findings") or {})
    if name == "next":
        return next_from_findings(arguments.get("findings") or {})
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
    text = json.dumps(data, indent=2)
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
            "instructions": "Use CheckYourself read-only first. Scan, fill coverage with evidence, score, rank backlog, ask before fixes.",
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
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            response = mcp_error(None, -32700, f"parse error: {exc}")
        else:
            try:
                response = handle_mcp_message(message)
            except Exception as exc:  # pragma: no cover - defensive protocol boundary.
                traceback.print_exc(file=sys.stderr)
                response = mcp_error(message.get("id"), -32603, str(exc))
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


def add_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project", nargs="?", default=".", help="Project root to scan (default: .)")
    parser.add_argument("--out", default="CHECKYOURSELF_PROJECT_CONTEXT.generated.md",
                        help="Markdown context output path (default: CHECKYOURSELF_PROJECT_CONTEXT.generated.md)")
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

    p = sub.add_parser("score", help="Compute deterministic Production Reality Score.")
    p.add_argument("--findings", required=True, help="JSON file containing findings, scan output, or report.")
    p.add_argument("--coverage", help="Optional coverage JSON file.")
    p.add_argument("--history", nargs="?", const=DEFAULT_SCORE_HISTORY_PATH,
                   help="Write score history to this path. Defaults to .checkyourself-score-history.json beside the findings file.")
    p.add_argument("--no-history", dest="history", action="store_const", const="none",
                   help="Do not append score history.")
    p.add_argument("--note", default="", help="Optional note stored with the score history entry.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_score)

    p = sub.add_parser("backlog", help="Rank the complete remediation backlog.")
    p.add_argument("--findings", required=True, help="JSON file containing findings, scan output, or report.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_backlog)

    p = sub.add_parser("next", help="Return the next safest unresolved approval batch.")
    p.add_argument("--findings", required=True, help="JSON file containing findings, scan output, or report.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_next)

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
    commands = {"describe", "scan", "diagnostic", "schema", "coverage", "score", "backlog", "next", "validate", "init", "mcp"}
    try:
        if not raw or raw[0] not in commands:
            return legacy_scan_main(raw)
        parser = build_parser()
        args = parser.parse_args(raw)
        return args.func(args)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
