"""Canonical constants, regex detectors, surface maps, and scoring tables."""

from __future__ import annotations

from pathlib import Path
import re


TOOL_NAME = "checkyourself-cli"

SCAN_SCHEMA_ID = "checkyourself-scan/1"

COVERAGE_SCHEMA_ID = "checkyourself-coverage/1"

SCORE_SCHEMA_ID = "checkyourself-score/1"

CAPABILITIES_SCHEMA_ID = "checkyourself-capabilities/1"

RECEIPT_SCHEMA_ID = "checkyourself-receipt/1"

CHALLENGE_SCHEMA_ID = "checkyourself-challenges/1"

CHALLENGE_RESULT_SCHEMA_ID = "checkyourself-challenge/1"

RECEIPT_ISSUER = "checkyourself-verifier/1"

MCP_PROTOCOL_VERSION = "2025-11-25"

SUPPORTED_MCP_PROTOCOLS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]

PUBLIC_REPO_SCOPE_GUARDRAILS = [
    "Name the exact GitHub owner namespace(s) before claiming public repository coverage.",
    "Report the repository count and verification timestamp for each owner namespace.",
    "State whether forks, archived repositories, and externally owned repositories were excluded.",
    "Do not infer ownership from linked repositories, examples, forks, or upstream references.",
    "List the live evidence surfaces checked, including findings, open PRs, dependency alerts, and branch status.",
    "For dependency or security closure, verify the default-branch alert state after merge; local scans and PR checks a"
    "re not enough.",
    "For a 100% status claim, require scanner findings, default-branch CI, dependency/security alerts, and git branch s"
    "tate to all agree.",
]

ROOT = Path(__file__).resolve().parents[2]

SCHEMA_DIR = ROOT / "schemas"

DEFAULT_COVERAGE_PATH = "CHECKYOURSELF_COVERAGE.generated.json"

DEFAULT_SCORE_HISTORY_PATH = ".checkyourself-score-history.json"

DEFAULT_CHALLENGES_PATH = ".checkyourself/challenges.json"

DEFAULT_CHALLENGE_OUTPUT_DIR = ".checkyourself/challenge-runs"

DEFAULT_LOCAL_INTEGRITY_BINDING_PATH = ".checkyourself/local-integrity-binding.key"

LOCAL_INTEGRITY_KEY_BYTES = 32

CONFIG_NAMES = (".checkyourself.yml", ".checkyourself.yaml", ".checkyourself.json")

IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    ".turbo",
    ".cache",
    "target",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".svelte-kit",
    "out",
    ".output",
    "vendor",
}

TEXT_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".rb",
    ".go",
    ".java",
    ".cs",
    ".php",
    ".env",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".sh",
    ".rs",
    ".md",
    ".txt",
    ".tf",
    ".tfvars",
    ".properties",
    ".ini",
    ".cfg",
    ".conf",
    ".xml",
    ".vue",
    ".svelte",
    ".kt",
    ".swift",
    ".dart",
    ".gradle",
}

CODE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".rb",
    ".go",
    ".java",
    ".cs",
    ".php",
    ".vue",
    ".svelte",
    ".kt",
    ".swift",
    ".dart",
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

TEST_PATH_MARKERS = (
    "test",
    "tests",
    "spec",
    "specs",
    "__tests__",
    "fixture",
    "fixtures",
    "mock",
    "mocks",
    "example",
    "examples",
    "sample",
    "samples",
    "doc",
    "docs",
    "__mocks__",
    "e2e",
    "stories",
)

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
    "next": "Next.js",
    "react": "React",
    "vue": "Vue",
    "svelte": "Svelte",
    "@angular/core": "Angular",
    "express": "Express",
    "fastify": "Fastify",
    "hono": "Hono",
    "@nestjs/core": "NestJS",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "@supabase/supabase-js": "Supabase client",
    "supabase": "Supabase",
    "prisma": "Prisma",
    "drizzle-orm": "Drizzle ORM",
    "mongoose": "MongoDB/Mongoose",
    "pg": "Postgres client",
    "psycopg2": "Postgres client",
    "mysql2": "MySQL client",
    "sqlite3": "SQLite",
    "better-sqlite3": "SQLite",
    "next-auth": "NextAuth/Auth.js",
    "@auth/core": "Auth.js",
    "@clerk/nextjs": "Clerk",
    "firebase": "Firebase",
    "jsonwebtoken": "JWT",
    "passport": "Passport",
    "stripe": "Stripe/payments",
    "openai": "OpenAI API",
    "@anthropic-ai/sdk": "Anthropic SDK",
    "anthropic": "Anthropic SDK",
    "langchain": "LangChain",
    "llamaindex": "LlamaIndex",
    "@pinecone-database/pinecone": "Pinecone",
    "chromadb": "ChromaDB",
    "weaviate": "Weaviate",
    "jest": "Jest",
    "vitest": "Vitest",
    "playwright": "Playwright",
    "cypress": "Cypress",
    "pytest": "pytest",
}

RISK_PATH_HINTS = [
    ("api", "API routes or handlers"),
    ("routes", "Routes"),
    ("middleware", "Middleware"),
    ("auth", "Authentication/authorization"),
    ("login", "Authentication"),
    ("admin", "Admin surface"),
    ("upload", "File upload"),
    ("payment", "Payments"),
    ("stripe", "Payments"),
    ("webhook", "Webhooks"),
    ("sql", "Raw SQL or migrations"),
    ("migration", "Database migrations"),
    ("rag", "RAG/AI"),
    ("embedding", "Embeddings/vector search"),
    ("agent", "AI agents"),
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

# These contracts are verifier-owned. A project can choose the command and the
# expected values, but it cannot remove the minimum substance needed for an
# executed challenge to count as evidence. Keep the contract shape explicit for
# every canonical surface so a new surface cannot silently fall back to
# exit-zero-only credit.
CHALLENGE_SEMANTIC_CONTRACTS = {
    "S01": {"minimum_output_tokens": 3},
    "S02": {"minimum_output_tokens": 3},
    "S03": {"minimum_output_tokens": 3},
    "S04": {"minimum_output_tokens": 3},
    "S05": {"minimum_output_tokens": 3},
    "S06": {"minimum_output_tokens": 3},
    "S07": {"minimum_output_tokens": 3},
    "S08": {"minimum_output_tokens": 3},
    "S09": {"minimum_output_tokens": 3},
    "S10": {"minimum_output_tokens": 3},
    "S11": {
        "minimum_output_tokens": 3,
        "requires_test_runner": True,
        "requires_test_count": True,
    },
    "S12": {"minimum_output_tokens": 3, "requires_artifact": True},
    "S13": {"minimum_output_tokens": 3, "requires_artifact": True},
    "S14": {"minimum_output_tokens": 3, "requires_artifact": True},
    "S15": {"minimum_output_tokens": 3},
    "S16": {"minimum_output_tokens": 3},
    "S17": {"minimum_output_tokens": 3},
    "S18": {"minimum_output_tokens": 3},
    "S19": {
        "minimum_output_tokens": 3,
        "required_output_kind": "json",
        "required_json_fields": ("status", "findings"),
    },
    "S20": {"minimum_output_tokens": 3},
}

TEST_RUNNER_MARKERS = (
    "pytest",
    "unittest",
    "jest",
    "vitest",
    "mocha",
    "ava",
    "go test",
    "node --test",
    "cargo test",
    "rspec",
    "phpunit",
    "dotnet test",
    "mvn test",
    "gradle test",
)

TEST_COUNT_RE = re.compile(r"(?im)\b\d+\s+(?:passed|failed|skipped|xfailed|xpassed|tests?)\b")

VACUOUS_REGEX_FIXTURES = ("", "echo", "echo-only", "ok", "success")

LOCAL_INTEGRITY_HMAC_FIELD = "local_integrity_hmac"

# Re-execution compares the meaning of captured output, not incidental process
# bytes. Keep these patterns narrow: only values that are expected to change
# between identical runs are normalized. Content edits must still change the
# semantic digest.
_DURATION_RE = re.compile(r"\bin\s+\d+(?:\.\d+)?\s*(?:ms|s)\b", re.IGNORECASE)

_CLOCK_DURATION_RE = re.compile(r"\b\d+:\d{2}:\d{2}(?:\.\d+)?\b")

_ISO_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})\b"
)

_TEMP_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(?:/private)?/(?:tmp|var/folders)(?:/[^\s\"'<>]+)*")

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

EXECUTED_RECEIPT_BINDING_FIELDS = (
    "receipt_type",
    "surface_id",
    "command",
    "cwd",
    "exit_code",
    "captured_output",
    "captured_output_digest",
    "semantic_output_digest",
    "source_revision",
    "timestamp",
    "timed_out",
    "status",
    "execution_error",
    "challenge_config_digest",
    "run_id",
)

LEGACY_EXECUTED_RECEIPT_BINDING_FIELDS = tuple(
    field for field in EXECUTED_RECEIPT_BINDING_FIELDS if field != "semantic_output_digest"
)

_NO_COVERAGE = object()

EVIDENCE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<path>(?:[A-Za-z0-9_./~\\-]+/)?[A-Za-z0-9_.~-]+\.[A-Za-z0-9_-]+)(?::\d+(?::\d+)?)?"
)
