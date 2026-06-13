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
    in_suppress = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped == "suppress:":
            in_suppress = True
            continue
        if in_suppress and not raw_line[:1].isspace() and not stripped.startswith("- "):
            # A new zero-indent top-level key ends the suppress block.
            if current:
                suppressions.append(current)
                current = None
            in_suppress = False
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
            if suppression_matches(finding, suppression):
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
        "files_unreadable": 0,
    }
    for dirpath, dirnames, filenames in os.walk(root):
        parent = Path(dirpath)
        # Sorting dirnames keeps walk order deterministic across filesystems.
        dirnames[:] = sorted(d for d in dirnames if keep_dir(parent, d))
        for name in sorted(filenames):
            p = parent / name
            if p.is_symlink():
                stats["symlinks_skipped"] += 1
                continue
            try:
                real = p.resolve(strict=True)
                real.relative_to(root)
                if real.stat().st_size > 2_000_000:
                    continue
            except ValueError:
                # Resolves outside the scanned tree (e.g. via a parent link).
                stats["symlinks_skipped"] += 1
                continue
            except OSError:
                stats["files_unreadable"] += 1
                continue
            if len(files) >= limit:
                stats["truncated"] = True
                stats["files_beyond_limit"] += 1
                continue
            files.append(p)
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


def is_env_example_name(name: str) -> bool:
    lower = name.lower()
    return lower in ENV_EXAMPLE_NAMES or (
        lower.startswith(".env")
        and lower.endswith((".example", ".sample", ".template"))
    )


def classify_env_file(name: str) -> Optional[str]:
    """Classify a file name as an 'example' env file, a 'real' one, or neither."""
    lower = name.lower()
    if is_env_example_name(lower):
        return "example"
    if lower.endswith(".env") and any(t in lower for t in ("example", "sample", "template")):
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


SOURCEMAP_CONFIG_NAMES = {
    "next.config.js", "next.config.mjs", "next.config.ts",
    "webpack.config.js", "webpack.config.ts",
}


def scan_file_contents(root: Path, files: List[Path]) -> Dict[str, List[str]]:
    """Single content pass over every scannable file, feeding all detectors.

    Secrets are scanned everywhere, including tests and docs, because real
    credentials get committed in both. The heuristic detectors (debug flags,
    CORS, sinks, default credentials) skip test/doc/fixture paths to keep the
    false-positive rate low.
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
    }
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

        if suffix not in TEXT_EXTENSIONS and not name.startswith(".env") and kind is None:
            continue
        text = read_text(p, max_chars=60_000)
        if not text or looks_binary(text):
            continue

        # Match markers against whole path segments (and segment stems like
        # `app.test.ts`) so `docker-compose.yml` is not mistaken for a doc path.
        path_segments = [s.lower() for s in Path(rp).parts]
        in_test_path = any(
            seg == marker or seg.startswith(marker + ".") or marker == seg.split(".")[-1]
            for seg in path_segments
            for marker in TEST_PATH_MARKERS
        )
        is_code = suffix in CODE_EXTENSIONS
        is_config = suffix in CONFIG_EXTENSIONS or kind is not None

        for line_no, line in enumerate(text.splitlines(), start=1):
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
                    results["suspicious_low"].append(secret_evidence(
                        rp, line_no, "possible secret-like assignment",
                        "secret_name_and_assignment", "low", line,
                    ))

            if in_test_path:
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
                        results["dangerous_sinks"].append(f"{rp}:{line_no} ({label}; {compact_context(line)})")
                        break
            if name in SOURCEMAP_CONFIG_NAMES and any(r.search(line) for r in SOURCEMAP_RES):
                results["sourcemap_configs"].append(f"{rp}:{line_no} ({compact_context(line)})")

    return {key: sorted(set(values))[:50] for key, values in results.items()}


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

    missing_gitignore = [pattern for pattern in (".env", "*.pem", "*.key") if pattern.lower() not in gitignore]
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
    gitignore: str,
    deps_found: Dict[str, List[str]],
    missing_lockfile: bool = False,
    deep_findings: Optional[List[Finding]] = None,
) -> List[Finding]:
    """Build scan findings with stable, semantic rule IDs.

    IDs are part of the public contract: suppressions, diffs, and CI gates key
    off them, so they must stay identical run-to-run and release-to-release.
    """
    findings: List[Finding] = []
    real_env_files = content["real_env_files"]
    env_files = content["env_files"]

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

    env_ignored = ".env" in gitignore
    if real_env_files and not env_ignored:
        findings.append(Finding(
            "CY-ENV-001", "P0", "A real .env file may be committed",
            "A non-example .env file exists and `.env` is not in .gitignore. "
            "If this is tracked by git, secrets are in your history. Gitignore it and rotate.",
            real_env_files,
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

    has_example = any(Path(e).name.lower() in ENV_EXAMPLE_NAMES for e in env_files)
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
    content = scan_file_contents(root, files)
    tests = find_tests(root, files)
    ci = find_ci(root)
    hints = path_hints(root, files)
    gitignore = gitignore_entries(root)
    deep_results = run_deep_checks(root, ci, gitignore) if deep else []
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
        "scan_limits": scan_limits,
        "stack_signals": stack_signals,
        "dependencies": {k: sorted(set(v)) for k, v in sorted(deps_found.items())},
        "scripts": scripts,
        "env_files": content["env_files"],
        "tests": tests,
        "ci": ci,
        "risk_surfaces": hints,
        "findings": finding_dicts,
        "counts": counts,
        "suppression_count": suppression_count,
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
    # Key strictly on the surface name: falling back to category collapsed
    # multiple surfaces onto one key and over-reported missing rows.
    by_name = {str(item.get("surface")): item for item in surfaces if isinstance(item, dict) and item.get("surface")}
    valid_statuses = {"Pass", "Finding", "Unknown", "NotApplicable"}
    pathlike_re = re.compile(r"[\w./\\-]+\.\w+|:\d+")

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
    """Fold surface-level coverage into per-category scoring state.

    Anti-gaming rules: a surface omitted from the artifact counts as Unknown
    (never as full credit), Pass without evidence downgrades to Unknown, and
    NotApplicable without a reason downgrades to Unknown. Omitting or
    hand-waving a surface must never score better than honestly reporting it.
    """
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

    name_to_id = {surface: sid for sid, surface, _category in COVERAGE_SURFACES}
    id_to_category = {sid: category for sid, _surface, category in COVERAGE_SURFACES}
    scored_surface_ids = {sid for sid, _surface, category in COVERAGE_SURFACES if category in SCORE_CATEGORIES}

    category_state = {
        cid: {"status": None, "evidence_reviewed": [], "missing_evidence": [], "surfaces": []}
        for cid in SCORE_CATEGORIES
    }
    status_rank = {"Finding": 4, "Unknown": 3, "Pass": 2, "NotApplicable": 1}
    present_ids = set()

    for item in surfaces:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or name_to_id.get(str(item.get("surface") or ""), ""))
        category = str(item.get("category") or id_to_category.get(sid, ""))
        if category not in SCORE_CATEGORIES:
            if sid:
                present_ids.add(sid)
            continue
        if sid:
            present_ids.add(sid)
        state = category_state[category]
        status = item.get("status") or "Unknown"
        evidence = [str(x) for x in item.get("evidence_reviewed") or []]
        if status == "Pass" and not evidence:
            status = "Unknown"
            state["missing_evidence"].append(f"{sid or 'surface'} marked Pass without evidence_reviewed")
        if status == "NotApplicable" and not str(item.get("not_applicable_reason") or "").strip():
            status = "Unknown"
            state["missing_evidence"].append(f"{sid or 'surface'} marked NotApplicable without a reason")
        if state["status"] is None or status_rank.get(status, 3) > status_rank.get(state["status"], 0):
            state["status"] = status
        state["surfaces"].append(sid or str(item.get("surface") or category))
        state["evidence_reviewed"].extend(evidence)
        state["missing_evidence"].extend(str(x) for x in item.get("missing_evidence") or [])

    for sid in sorted(scored_surface_ids - present_ids):
        category = id_to_category[sid]
        state = category_state[category]
        state["missing_evidence"].append(f"surface {sid} missing from coverage artifact")
        if state["status"] is None or status_rank.get("Unknown", 3) > status_rank.get(state["status"], 0):
            state["status"] = "Unknown"

    for state in category_state.values():
        if state["status"] is None:
            state["status"] = "MissingCoverage"
            state["missing_evidence"].append("no coverage entries supplied for this category")
        state["evidence_reviewed"] = sorted(set(state["evidence_reviewed"]))
        state["missing_evidence"] = sorted(set(state["missing_evidence"]))

    required_ids = {sid for sid, _surface, _category in COVERAGE_SURFACES}
    complete = required_ids <= present_ids
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
    # Evidence caps apply in every score mode: an estimate without coverage
    # evidence must never report a launch-ready number.
    for cid, state in coverage_by_category.items():
        if state["status"] in {"Unknown", "MissingCoverage"} and cid in CRITICAL_CATEGORIES:
            critical_gap = True
        if state["status"] in {"Unknown", "MissingCoverage"} and cid in HIGH_SCORE_GATE_CATEGORIES:
            high_score_gap = True
    if critical_gap:
        cap_value = min(cap_value, 84)
        caps.append({"cap": 84, "reason": "missing evidence in a critical category"})
    if high_score_gap:
        cap_value = min(cap_value, 90)
        caps.append({"cap": 90, "reason": "score above 90 requires evidence for tests, secrets, deploy/rollback, observability, auth, and data boundaries"})

    score = min(raw_score, cap_value)
    any_gap = any(
        state["status"] in {"Unknown", "MissingCoverage"}
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
        "manual_evidence_needed": missing_manual_evidence(coverage_by_category),
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


def diff_findings(old_data: Any, new_data: Any) -> dict:
    """Compare two findings artifacts (scan output, report, or finding list).

    Stable rule IDs make this meaningful: the same risk keeps the same ID
    across runs, so added/resolved is a real delta, not ID-shuffle noise.
    """
    old_findings = {f["id"]: f for f in normalize_findings(old_data)}
    new_findings = {f["id"]: f for f in normalize_findings(new_data)}
    added_ids = sorted(set(new_findings) - set(old_findings))
    resolved_ids = sorted(set(old_findings) - set(new_findings))
    persisting_ids = sorted(set(old_findings) & set(new_findings))

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
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-diff/1",
        "generated_at": now_iso(),
        "added": [new_findings[fid] for fid in added_ids],
        "resolved": [old_findings[fid] for fid in resolved_ids],
        "unchanged": persisting_ids,
        "evidence_changes": evidence_changes,
        "old_counts": old_counts,
        "new_counts": new_counts,
        "regression": any(new_counts[sev] > old_counts[sev] for sev in ("P0", "P1")),
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
        ("diff", "Compare two findings artifacts and report added, resolved, and regressed findings.", {"old": "json path", "new": "json path"}, "checkyourself-diff/1"),
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
        data = json.loads(manifest.read_text(encoding="utf-8"))
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
    if path.is_symlink():
        raise CliError(f"refusing to write through symlink: {path}")
    path.write_text(body, encoding="utf-8")


def write_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=False))


def write_text_result(data: dict) -> None:
    schema = data.get("schema", "")
    if schema == SCAN_SCHEMA_ID:
        c = data["counts"]
        print(f"Scanned {data['files_scanned']} files. Findings — P0: {c['P0']}, P1: {c['P1']}, P2: {c['P2']}, P3: {c['P3']}")
        limits = data.get("scan_limits") or {}
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
        # Piped findings should not silently litter the CWD with a history
        # file; stdin scoring writes history only when --history is explicit.
        return None
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
    safe_write_text(path, json.dumps(history, indent=2) + "\n")


def command_scan(args: argparse.Namespace) -> int:
    root = Path(args.project).resolve()
    if not root.is_dir():
        raise CliError(f"project root not found: {root}")
    data = scan(root, deep=getattr(args, "deep", False), max_files=getattr(args, "max_files", DEFAULT_MAX_FILES))
    json_stdout = args.format == "json" or args.json == "-" or (args.no_write and args.json is not None)

    if not args.no_write:
        out = Path(args.out)
        if not out.is_absolute():
            out = Path.cwd() / out
        safe_write_text(out, render_markdown(root, data))
        if not args.quiet and not json_stdout:
            print(f"Wrote context: {out}")
        if args.json is not None and args.json != "-":
            jout = Path(args.json)
            if not jout.is_absolute():
                jout = Path.cwd() / jout
            safe_write_text(jout, json.dumps(data, indent=2) + "\n")
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
        safe_write_text(Path(out_path), json.dumps(data, indent=2) + "\n")
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
        if result["regression"]:
            print("REGRESSION: open P0/P1 count increased against the baseline.")
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
                    "description": "Maximum files to scan before truncating (default 6000). The result reports truncation in scan_limits.",
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
                    "type": "object",
                    "description": "Optional filled coverage object. Provide this for coverage-backed scoring; omit for scan-derived or finding-only estimates.",
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
                "Return the next safest unresolved approval batch from inline findings by reusing the backlog ranking rules. "
                "The batch contains at most the first three unresolved findings at the highest current severity. "
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
                "resolved, and unchanged findings, evidence-level changes, severity count deltas, and a regression flag "
                "that is true when open P0/P1 counts increased. Use this to gate changes against a baseline."
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
        return coverage_check(arguments.get("coverage") or {})
    if name == "score":
        return score_from_inputs(arguments.get("findings") or {}, arguments.get("coverage"))
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
            if not isinstance(message, dict):
                # JSON-RPC batch arrays would otherwise crash on .get().
                sys.stdout.write(json.dumps(mcp_error(None, -32600, "batch requests are not supported; send one JSON-RPC object per line"), separators=(",", ":")) + "\n")
                sys.stdout.flush()
                continue
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

    p = sub.add_parser("diff", help="Compare two findings artifacts and report added/resolved/regressed findings.")
    p.add_argument("--old", required=True, help="Baseline findings JSON path, or - for stdin.")
    p.add_argument("--new", required=True, help="Current findings JSON path, or - for stdin.")
    p.add_argument("--ci", action="store_true", help="Exit non-zero when open P0/P1 counts increased.")
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
    commands = {"describe", "scan", "diagnostic", "schema", "coverage", "score", "backlog", "next", "diff", "validate", "init", "mcp"}
    try:
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
        print(f"error: {exc}", file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
