"""Content detectors: secrets, debug flags, CORS, sinks, and deep CI checks."""

from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Any, Dict, List, Optional, Sequence
from .constants import (
    CODE_EXTENSIONS,
    CONFIG_EXTENSIONS,
    CONTEXT_ONLY_PATH_MARKERS,
    CORS_WILDCARD_RES,
    DANGEROUS_SINK_RES,
    DEBUG_FLAG_RES,
    DEFAULT_CRED_RE,
    DEFAULT_CRED_URL_RE,
    EXTENSIONLESS_CONFIG_NAMES,
    SECRET_NAME_RE,
    SECRET_SHAPE_RES,
    SECRET_VALUE_RE,
    SOURCEMAP_RES,
    TEXT_EXTENSIONS,
)
from .models import Finding
from .scanning import classify_env_file, gitignore_ignores_path, is_placeholder_secret_value
from .util import compact_context, looks_binary, read_text, read_text_with_status, rel, secret_evidence


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
    window = "\n".join(lines[max(0, index - 14) : index + 1]).lower()
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
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "webpack.config.js",
    "webpack.config.ts",
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
        results["context_suppressions"].append(
            {
                "path": rp,
                "line": line_no,
                "detector": detector,
                "reason": reason,
            }
        )

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
                results["suspicious_high"].append(
                    secret_evidence(
                        rp,
                        line_no,
                        "high-confidence credential shape",
                        "credential_shape",
                        "high",
                        line,
                    )
                )
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
                        results["suspicious_low"].append(
                            secret_evidence(
                                rp,
                                line_no,
                                "possible secret-like assignment",
                                "secret_name_and_assignment",
                                "low",
                                line,
                            )
                        )

            if in_test_path:
                for sink_re, label in DANGEROUS_SINK_RES:
                    if sink_re.search(line):
                        suppress_context(
                            rp, line_no, label, path_reason or "heuristic detector skipped in review context"
                        )
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
                    mutable_actions.append(f"{workflow}:{line_no} (uses {action}@{ref}; pin to a full commit SHA)")
            if npm_install_re.search(line):
                npm_install_in_ci.append(f"{workflow}:{line_no} (use `npm ci` for reproducible installs)")

    if mutable_actions:
        findings.append(
            Finding(
                "CY-SUPPLY-001",
                "P2",
                "Mutable GitHub Action references",
                "One or more workflow steps use a version tag instead of an immutable commit SHA. "
                "A compromised or moved tag can change your CI behavior without a code diff.",
                mutable_actions[:50],
                category="C6",
                recommended_fix="Pin each third-party action to a full commit SHA and leave a version comment for reada"
                "bility.",
            )
        )

    if ci and not any(
        (root / path).exists() for path in (".github/dependabot.yml", ".github/dependabot.yaml", "renovate.json")
    ):
        findings.append(
            Finding(
                "CY-SUPPLY-003",
                "P3",
                "No dependency update automation detected",
                "CI exists, but no Dependabot or Renovate configuration was found. Dependency risk can silently age.",
                [".github/dependabot.yml or renovate.json not found"],
                category="C6",
                recommended_fix="Add Dependabot or Renovate for the detected package ecosystems.",
            )
        )

    if npm_install_in_ci:
        findings.append(
            Finding(
                "CY-SUPPLY-004",
                "P3",
                "CI installs dependencies without the lockfile contract",
                "A workflow runs `npm install` instead of `npm ci`. Installs can drift from the lockfile, "
                "so CI may pass with different dependency versions than production.",
                npm_install_in_ci[:50],
                category="C6",
                recommended_fix="Use `npm ci` (or the pnpm/yarn frozen-lockfile equivalent) in CI.",
            )
        )

    gitignore_targets = {".env": ".env", "*.pem": "secret.pem", "*.key": "secret.key"}
    missing_gitignore = [
        pattern for pattern, target in gitignore_targets.items() if not gitignore_ignores_path(gitignore, target)
    ]
    if missing_gitignore:
        findings.append(
            Finding(
                "CY-SECRET-003",
                "P3",
                "Sensitive file patterns missing from .gitignore",
                "Common local secret file patterns are not explicitly ignored.",
                [f"missing gitignore pattern: {pattern}" for pattern in missing_gitignore],
                category="C3",
                recommended_fix="Add local secret file patterns to `.gitignore` and verify no matching files were previ"
                "ously committed.",
            )
        )

    return findings
