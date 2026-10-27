"""Production Reality Report rendering, parsing, and semantic checks."""

from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Any, Iterable, List
from .constants import RESOLVED_STATUSES, SCORE_CATEGORIES
from .describe import load_schema
from .errors import CliError
from .jsonlite import strict_json_loads, validate_json_schema
from .scoring import normalize_findings


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
        add(
            f"- WARNING: scan truncated at {limits.get('max_files')} files; "
            f"{limits.get('files_beyond_limit')} files were not scanned. "
            "Findings may be incomplete — rerun with a higher --max-files."
        )
    if limits.get("symlinks_skipped"):
        add(f"- Note: {limits['symlinks_skipped']} symlinked path(s) were skipped and not scanned.")
    if limits.get("files_unreadable"):
        add(f"- Note: {limits['files_unreadable']} file(s) could not be read and were not scanned.")
    add("")
    add("## Scope guardrails")
    add("")
    add(
        "- Before claiming an entire GitHub namespace is clean, name the exact owner namespace, repository count, verif"
        "ication timestamp, and live evidence surfaces checked."
    )
    add(
        "- Leave forks, externally owned repositories, and upstream references out of scope unless the user explicitly "
        "includes them."
    )
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
    if (
        isinstance(breakdown, list)
        and breakdown
        and all(isinstance(item, dict) and isinstance(item.get("awarded"), (int, float)) for item in breakdown)
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
