"""Building the deterministic scan artifact from inventory and detector output."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
from .config import apply_suppressions, load_checkyourself_config
from .constants import (
    LLM_DEPENDENCY_LABELS,
    LOCKFILE_NAMES,
    PUBLIC_REPO_SCOPE_GUARDRAILS,
    SCAN_SCHEMA_ID,
    SEVERITY_ORDER,
    TOOL_NAME,
)
from .detectors import run_deep_checks, scan_file_contents
from .models import Finding
from .scanning import (
    DEFAULT_MAX_FILES,
    detect_stack,
    find_ci,
    find_tests,
    gitignore_entries,
    gitignore_ignores_path,
    is_env_example_name,
    iter_files,
    path_hints,
    tree_sample,
)
from .util import now_iso


def _env_commitment_findings(real_env_files: List[str], gitignore: List[str]) -> List[Finding]:
    """The committed/untracked .env findings (CY-ENV-001/002), split out of build_findings."""
    unignored_env_files = [path for path in real_env_files if not gitignore_ignores_path(gitignore, path)]
    if unignored_env_files:
        return [
            Finding(
                "CY-ENV-001",
                "P0",
                "A real .env file may be committed",
                "A non-example .env file exists and `.env` is not in .gitignore. "
                "If this is tracked by git, secrets are in your history. Gitignore it and rotate.",
                unignored_env_files,
                category="C3",
                recommended_fix="Add `.env` patterns to `.gitignore`, remove tracked env files, and rotate exposed "
                "values.",
            )
        ]
    if real_env_files:
        return [
            Finding(
                "CY-ENV-002",
                "P2",
                "Local .env present (verify it is not tracked)",
                "A non-example .env exists; `.env` is in .gitignore, but confirm it was never committed earlier.",
                real_env_files,
                category="C3",
                recommended_fix="Run git history/secret checks and keep only redacted "
                "`.env.example` files in the repo.",
            )
        ]
    return []


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
        findings.append(
            Finding(
                "CY-CONFIG-003",
                "P2",
                "Invalid CheckYourself suppression configuration",
                "The optional suppression configuration could not be validated, so no suppressions were applied. "
                "Fix the configuration before relying on a clean scan.",
                [config_error],
                category="C3",
                recommended_fix="Correct the suppression file shape and rerun the scan; invalid configuration must neve"
                "r hide findings.",
            )
        )

    if content["suspicious_high"]:
        findings.append(
            Finding(
                "CY-SECRET-001",
                "P0",
                "High-confidence credential shape in source",
                "One or more files contain a credential-shaped value. "
                "Rotate anything real, move it to environment variables, and confirm it is gitignored.",
                content["suspicious_high"],
                category="C3",
                recommended_fix="Rotate anything real, remove it from source, load it from environment variables, and c"
                "onfirm history exposure.",
            )
        )

    if content["suspicious_low"]:
        findings.append(
            Finding(
                "CY-SECRET-002",
                "P2",
                "Possible secret-like field without credential shape",
                "A file contains a secret-like assignment, but no known credential shape was found. "
                "Review it before renaming fields or accepting it as benign.",
                content["suspicious_low"],
                category="C3",
                recommended_fix="Verify whether the value is a credential. If it is benign, add a reviewed `.checkyours"
                "elf.yml` suppression; if real, move it to environment variables.",
            )
        )

    findings.extend(_env_commitment_findings(real_env_files, gitignore))

    has_example = any(is_env_example_name(Path(e).name) for e in env_files)
    if real_env_files and not has_example:
        findings.append(
            Finding(
                "CY-ENV-003",
                "P1",
                "No .env.example for required configuration",
                "The app uses environment variables but ships no .env.example. New contributors and "
                "deploys can miss required config. Add a documented example with no real values.",
                real_env_files,
                category="C3",
                recommended_fix="Add `.env.example` with variable names, safe placeholders, and setup notes.",
            )
        )

    if content["default_credentials"]:
        findings.append(
            Finding(
                "CY-CONFIG-002",
                "P1",
                "Default or weak credentials in committed configuration",
                "A committed file assigns a well-known default password or uses a default-credential "
                "connection string. Anyone who reads the repo can log in.",
                content["default_credentials"],
                category="C3",
                recommended_fix="Replace default credentials with strong generated values loaded from the environment, "
                "and rotate anything already deployed.",
            )
        )

    if content["debug_flags"]:
        findings.append(
            Finding(
                "CY-CONFIG-001",
                "P2",
                "Debug mode enabled in configuration",
                "A debug flag is switched on in committed configuration. If this reaches production it can "
                "leak stack traces, secrets, and internal state to users.",
                content["debug_flags"],
                category="C3",
                recommended_fix="Default debug to off, enable it only via local environment overrides, and verify produ"
                "ction config never sets it.",
            )
        )

    if content["cors_wildcards"]:
        findings.append(
            Finding(
                "CY-API-001",
                "P2",
                "CORS allows any origin",
                "A wildcard CORS origin was found. Combined with credentials or sensitive responses, "
                "any website can call your API on behalf of its visitors.",
                content["cors_wildcards"],
                category="C4",
                recommended_fix="Replace the wildcard with an explicit allowlist of trusted origins and never combine `"
                "*` with credentials.",
            )
        )

    if content["dangerous_sinks"]:
        findings.append(
            Finding(
                "CY-CODE-001",
                "P2",
                "Dangerous code pattern in application source",
                "The code uses a pattern that is unsafe with untrusted input, such as eval, unsafe "
                "deserialization, raw HTML injection, or disabled TLS verification.",
                content["dangerous_sinks"],
                category="C4",
                recommended_fix="Replace each flagged pattern with the safe equivalent, or document why the input can n"
                "ever be attacker-controlled.",
            )
        )

    if content["sourcemap_configs"]:
        findings.append(
            Finding(
                "CY-WEB-001",
                "P3",
                "Source maps enabled for production builds",
                "Production source maps ship your original source to every visitor, making "
                "reverse-engineering and secret-hunting easier.",
                content["sourcemap_configs"],
                category="C9",
                recommended_fix="Disable production source maps, or restrict them to your error-tracking service.",
            )
        )

    if missing_lockfile:
        findings.append(
            Finding(
                "CY-SUPPLY-002",
                "P2",
                "No dependency lockfile committed",
                "package.json exists but no lockfile was found. Every install can resolve different "
                "dependency versions, so builds are not reproducible and supply-chain risk is unpinned.",
                ["package.json present without package-lock.json, pnpm-lock.yaml, yarn.lock, or bun.lock"],
                category="C6",
                recommended_fix="Commit the lockfile for your package manager and use frozen-lockfile installs in CI.",
            )
        )

    if not tests:
        findings.append(
            Finding(
                "CY-TEST-001",
                "P1",
                "No automated tests detected",
                "No test files were found. At minimum, add tests around auth, money, and data-loss paths.",
                [],
                category="C5",
                recommended_fix="Add the smallest regression tests around the highest-risk user paths.",
            )
        )

    if not ci:
        findings.append(
            Finding(
                "CY-CI-001",
                "P2",
                "No CI pipeline detected",
                "No CI configuration found. A CI gate catches regressions before they reach users.",
                [],
                category="C6",
                recommended_fix="Add a minimal CI workflow that installs, builds, tests, and runs secret checks.",
            )
        )

    if "Stripe/payments" in deps_found and not tests:
        findings.append(
            Finding(
                "CY-PAY-001",
                "P1",
                "Payments present but no tests",
                "A payments dependency was detected with no tests. Payment flows are high-blast-radius; "
                "add negative and webhook tests.",
                [],
                category="C4",
                recommended_fix="Add payment success, failure, idempotency, and webhook signature tests.",
            )
        )

    llm_deps = sorted(set(deps_found) & LLM_DEPENDENCY_LABELS)
    if llm_deps and not tests:
        findings.append(
            Finding(
                "CY-AI-001",
                "P2",
                "LLM integration present but no tests",
                "An LLM dependency was detected with no tests. Untested AI paths fail in expensive ways: "
                "malformed outputs, runaway token spend, and prompt-injection regressions.",
                [f"LLM dependency detected: {label}" for label in llm_deps],
                category="C10",
                recommended_fix="Add tests for output validation, failure handling, and cost guards around every model "
                "call.",
            )
        )

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
    missing_lockfile = (root / "package.json").exists() and not any((root / name).exists() for name in LOCKFILE_NAMES)
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
