#!/usr/bin/env python3
"""CheckYourself — optional local scan & scaffold CLI.

CheckYourself is primarily a model-agnostic system you load as an AI assistant's
operating context. This CLI is an *optional* head start: it does the cheap,
deterministic discovery locally — no tokens, no network, no data leaves your
machine — so your AI can spend its budget on judgment instead of grep.

What it does:
  - detects the stack (manifests, frameworks, hosting, ORM, AI/RAG, tests, CI);
  - flags obvious deterministic risks (possible hardcoded secrets, a committed
    .env, missing .env.example, no tests, no CI);
  - writes a pre-filled context Markdown file you can hand to your assistant;
  - optionally writes a machine-readable JSON summary;
  - returns a non-zero exit code under --ci when a high-severity issue is found,
    so it can act as a lightweight CI gate.

It never prints secret values, and it is not a replacement for the full
AI-driven CheckYourself diagnostic — it is the scaffold the diagnostic builds on.

Standard library only. Works anywhere Python 3.8+ runs.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

IGNORED_DIRS = {
    ".git", "node_modules", ".next", "dist", "build", "coverage", ".venv", "venv",
    "__pycache__", ".turbo", ".cache", "target", ".idea", ".vscode", ".pytest_cache",
    ".svelte-kit", "out", ".output", "vendor",
}

SECRET_NAME_RE = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|private[_-]?key|client[_-]?secret|access[_-]?key)",
    re.I,
)
SECRET_VALUE_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|private[_-]?key|access[_-]?key)\s*[:=]\s*['\"]?"
    r"([A-Za-z0-9_\-\./+=]{16,})"
)
# Well-known live-credential shapes (high confidence, value never printed).
SECRET_SHAPE_RES = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),            # OpenAI-style
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),     # Anthropic-style
    re.compile(r"AKIA[0-9A-Z]{16}"),               # AWS access key id
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),        # Google API key
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),           # GitHub PAT
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),   # Slack token
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


class Finding:
    def __init__(self, fid: str, severity: str, title: str, detail: str, evidence: List[str]):
        self.id = fid
        self.severity = severity
        self.title = title
        self.detail = detail
        self.evidence = evidence

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "evidence": self.evidence,
        }


def iter_files(root: Path, limit: int = 6000) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in IGNORED_DIRS and (not d.startswith(".") or d == ".github")
        ]
        for name in filenames:
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
                scripts = data["scripts"]
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

    return signals, scripts, deps_found


def gitignore_entries(root: Path) -> str:
    gi = root / ".gitignore"
    return read_text(gi).lower() if gi.exists() else ""


def scan_env_and_secrets(root: Path, files: List[Path]) -> Tuple[List[str], List[str], List[str]]:
    env_files: List[str] = []
    real_env_files: List[str] = []
    suspicious: List[str] = []
    for p in files:
        rp = rel(root, p)
        name = p.name.lower()
        is_example = name in ENV_EXAMPLE_NAMES
        if name == ".env" or (name.startswith(".env.") and not is_example) or name.endswith(".env"):
            real_env_files.append(rp)
            env_files.append(rp)
        elif is_example:
            env_files.append(rp)
        if p.suffix.lower() in {
            ".js", ".jsx", ".ts", ".tsx", ".py", ".rb", ".go", ".java", ".cs", ".php",
            ".env", ".yaml", ".yml", ".json", ".toml", ".sh", ".rs",
        } or name.startswith(".env"):
            text = read_text(p, max_chars=60_000)
            shaped = any(r.search(text) for r in SECRET_SHAPE_RES)
            generic = bool(SECRET_NAME_RE.search(text) and SECRET_VALUE_RE.search(text))
            if shaped or generic:
                tag = "high-confidence credential shape" if shaped else "possible hardcoded secret"
                suspicious.append(f"{rp} ({tag}; value omitted)")
    return sorted(set(env_files)), sorted(set(real_env_files)), suspicious[:50]


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
    return ci


def path_hints(root: Path, files: List[Path]) -> Dict[str, List[str]]:
    hints: Dict[str, List[str]] = {}
    for p in files:
        rp = rel(root, p)
        lower = rp.lower()
        for needle, label in RISK_PATH_HINTS:
            if needle in lower:
                hints.setdefault(label, []).append(rp)
    return {k: v[:40] for k, v in sorted(hints.items())}


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
    suspicious: List[str],
    tests: List[str],
    ci: List[str],
    gitignore: str,
    deps_found: Dict[str, List[str]],
) -> List[Finding]:
    findings: List[Finding] = []
    n = 0

    def nid() -> str:
        nonlocal n
        n += 1
        return f"CY-{n:03d}"

    if suspicious:
        findings.append(Finding(
            nid(), "P0", "Possible hardcoded secrets in source",
            "One or more files contain patterns that look like live credentials. "
            "Rotate anything real, move it to environment variables, and confirm it is gitignored.",
            suspicious,
        ))

    env_ignored = ".env" in gitignore
    if real_env_files and not env_ignored:
        findings.append(Finding(
            nid(), "P0", "A real .env file may be committed",
            "A non-example .env file exists and `.env` is not in .gitignore. "
            "If this is tracked by git, secrets are in your history. Gitignore it and rotate.",
            real_env_files,
        ))
    elif real_env_files:
        findings.append(Finding(
            nid(), "P2", "Local .env present (verify it is not tracked)",
            "A non-example .env exists; `.env` is in .gitignore, but confirm it was never committed earlier.",
            real_env_files,
        ))

    has_example = any(Path(e).name.lower() in ENV_EXAMPLE_NAMES for e in env_files)
    if real_env_files and not has_example:
        findings.append(Finding(
            nid(), "P1", "No .env.example for required configuration",
            "The app uses environment variables but ships no .env.example. New contributors and "
            "deploys can miss required config. Add a documented example with no real values.",
            real_env_files,
        ))

    if not tests:
        findings.append(Finding(
            nid(), "P1", "No automated tests detected",
            "No test files were found. At minimum, add tests around auth, money, and data-loss paths.",
            [],
        ))

    if not ci:
        findings.append(Finding(
            nid(), "P2", "No CI pipeline detected",
            "No CI configuration found. A CI gate catches regressions before they reach users.",
            [],
        ))

    if any(k in deps_found for k in ("Stripe/payments",)) and not tests:
        findings.append(Finding(
            nid(), "P1", "Payments present but no tests",
            "A payments dependency was detected with no tests. Payment flows are high-blast-radius; "
            "add negative and webhook tests.",
            [],
        ))

    findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 9))
    return findings


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
            add(f"### [{f['severity']}] {f['id']} — {f['title']}")
            add("")
            add(f["detail"])
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
        items = list(items)
        if items:
            for i in items:
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
    section(
        "Package scripts",
        (f"`{k}`: `{v}`" for k, v in data["scripts"].items()),
        "No package scripts detected.",
    )
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


def scan(root: Path) -> dict:
    files = iter_files(root)
    stack_signals, scripts, deps_found = detect_stack(root)
    env_files, real_env_files, suspicious = scan_env_and_secrets(root, files)
    tests = find_tests(root, files)
    ci = find_ci(root)
    hints = path_hints(root, files)
    gitignore = gitignore_entries(root)
    findings = build_findings(real_env_files, env_files, suspicious, tests, ci, gitignore, deps_found)

    counts = {sev: 0 for sev in ("P0", "P1", "P2", "P3")}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    return {
        "tool": "checkyourself-cli",
        "schema": "checkyourself-scan/1",
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "project": str(root),
        "files_scanned": len(files),
        "stack_signals": stack_signals,
        "dependencies": {k: sorted(set(v)) for k, v in sorted(deps_found.items())},
        "scripts": scripts,
        "env_files": env_files,
        "tests": tests,
        "ci": ci,
        "risk_surfaces": hints,
        "findings": [f.to_dict() for f in findings],
        "counts": counts,
        "tree": tree_sample(root),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="checkyourself",
        description="Optional local scan & scaffold for CheckYourself. Detects the stack, flags "
                    "obvious risks, and writes a pre-filled context file for your AI assistant.",
    )
    parser.add_argument("project", nargs="?", default=".", help="Project root to scan (default: .)")
    parser.add_argument("--out", default="CHECKYOURSELF_PROJECT_CONTEXT.generated.md",
                        help="Markdown context output path (default: CHECKYOURSELF_PROJECT_CONTEXT.generated.md)")
    parser.add_argument("--json", nargs="?", const="CHECKYOURSELF_SCAN.generated.json", default=None,
                        help="Also write a JSON summary (default path: CHECKYOURSELF_SCAN.generated.json)")
    parser.add_argument("--ci", action="store_true",
                        help="Exit non-zero if any P0 finding is detected (lightweight CI gate).")
    parser.add_argument("--no-write", action="store_true", help="Print the summary only; write no files.")
    parser.add_argument("--quiet", action="store_true", help="Suppress the console summary.")
    args = parser.parse_args(argv)

    root = Path(args.project).resolve()
    if not root.is_dir():
        print(f"error: project root not found: {root}", file=sys.stderr)
        return 2

    data = scan(root)

    if not args.no_write:
        out = Path(args.out)
        if not out.is_absolute():
            out = Path.cwd() / out
        out.write_text(render_markdown(root, data), encoding="utf-8")
        if not args.quiet:
            print(f"Wrote context: {out}")
        if args.json is not None:
            jout = Path(args.json)
            if not jout.is_absolute():
                jout = Path.cwd() / jout
            jout.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            if not args.quiet:
                print(f"Wrote JSON:    {jout}")

    if not args.quiet:
        c = data["counts"]
        print(f"Scanned {data['files_scanned']} files. "
              f"Findings — P0: {c['P0']}, P1: {c['P1']}, P2: {c['P2']}, P3: {c['P3']}")
        for f in data["findings"]:
            print(f"  [{f['severity']}] {f['id']} {f['title']}")
        print("Next: hand the generated context to your AI and run the full CheckYourself diagnostic.")

    if args.ci and data["counts"].get("P0", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
