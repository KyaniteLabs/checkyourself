"""Backlog ranking, next-batch selection, and findings diffing."""

from __future__ import annotations

from typing import Any, Dict, List
from .constants import RESOLVED_STATUSES, SEVERITY_ORDER, TOOL_NAME
from .scoring import default_fix_for, normalize_findings, require_findings_artifact
from .util import now_iso


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
            status_changes.append(
                {
                    "id": fid,
                    "old_status": old_status,
                    "new_status": new_status,
                }
            )
        if old_severity != new_severity:
            severity_changes.append(
                {
                    "id": fid,
                    "old_severity": old_severity,
                    "new_severity": new_severity,
                }
            )
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
            add_regression(
                {
                    "id": fid,
                    "type": "newly_open",
                    "severity": finding["severity"],
                }
            )
    for fid in persisting_ids:
        old_finding = old_findings[fid]
        new_finding = new_findings[fid]
        if not is_open(old_finding) and is_open(new_finding) and new_finding["severity"] in {"P0", "P1"}:
            add_regression(
                {
                    "id": fid,
                    "type": "reopened",
                    "severity": new_finding["severity"],
                }
            )
        if (
            is_open(new_finding)
            and new_finding["severity"] in {"P0", "P1"}
            and SEVERITY_ORDER.get(new_finding["severity"], 9) < SEVERITY_ORDER.get(old_finding["severity"], 9)
        ):
            add_regression(
                {
                    "id": fid,
                    "type": "severity_escalated",
                    "old_severity": old_finding["severity"],
                    "new_severity": new_finding["severity"],
                }
            )

    evidence_changes: List[dict] = []
    for fid in persisting_ids:
        old_evidence = set(old_findings[fid].get("evidence") or [])
        new_evidence = set(new_findings[fid].get("evidence") or [])
        if old_evidence != new_evidence:
            evidence_changes.append(
                {
                    "id": fid,
                    "evidence_added": sorted(new_evidence - old_evidence),
                    "evidence_resolved": sorted(old_evidence - new_evidence),
                }
            )

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
