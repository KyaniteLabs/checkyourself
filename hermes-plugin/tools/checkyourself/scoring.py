"""Production Reality Score inputs, coverage folding, and score computation."""

from __future__ import annotations

from pathlib import Path
import math
from typing import Any, Dict, List, Optional, Tuple
from .constants import (
    COVERAGE_SURFACES,
    CRITICAL_CATEGORIES,
    HIGH_SCORE_GATE_CATEGORIES,
    RESOLVED_STATUSES,
    SCAN_SCHEMA_ID,
    SCORE_CATEGORIES,
    SCORE_SCHEMA_ID,
    SEVERITY_ORDER,
    SEVERITY_PENALTIES,
    TOOL_NAME,
    WORKFLOW_DISPOSITIONS,
    _NO_COVERAGE,
)
from .coverage import _coverage_evidence_state, _coverage_validation_errors
from .errors import CliError
from .util import now_iso


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
        normalized.append(
            {
                "id": fid,
                "finding_id": fid,
                "severity": severity if severity in SEVERITY_ORDER else "P3",
                "category": category,
                "finding": title,
                "title": title,
                "plain_english_risk": detail,
                "detail": detail,
                "evidence": [str(e) for e in evidence],
                "recommended_fix": str(
                    raw.get("recommended_fix") or raw.get("fix_summary") or default_fix_for(title, category)
                ),
                "status": status,
            }
        )
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
            state["missing_evidence"].extend(f"{sid or 'surface'}: {warning}" for warning in evidence_state["warnings"])
        for failed in evidence_state.get("failed_receipts") or []:
            failed_id = f"CY-CHALLENGE-{sid or category}"
            state["coverage_findings"].append(
                {
                    "id": failed_id,
                    "finding_id": failed_id,
                    "severity": "P1",
                    "category": category,
                    "finding": f"Executed challenge failed for {sid or category}",
                    "plain_english_risk": str(failed.get("reason") or "The verifier-owned challenge failed."),
                    "status": "open",
                    "linked_finding_ids": [],
                }
            )
            state["has_unknown"] = True
            state["missing_evidence"].append(
                f"{sid or category}: executed challenge failed ({failed.get('reference') or 'capture'})"
            )
        if status == "Unknown":
            state["has_unknown"] = True
        if status == "Finding":
            state["coverage_findings"].append(
                {
                    "id": f"CY-COVERAGE-{sid or category}",
                    "finding_id": f"CY-COVERAGE-{sid or category}",
                    "severity": "P2",
                    "category": category,
                    "finding": f"Coverage finding requires review: {sid or category}",
                    "plain_english_risk": "The coverage reviewer recorded a gap on this production surface.",
                    "status": "open",
                    "linked_finding_ids": [str(x) for x in item.get("finding_ids") or []],
                }
            )
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
            needed.append(
                {
                    "category": cid,
                    "surface": name,
                    "needed": state["missing_evidence"] or ["manual coverage evidence"],
                }
            )
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
                "invalid coverage artifact: "
                + "; ".join(coverage_errors)
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
    challenge_failure_ids: set[str] = set()

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
                if str(coverage_finding.get("id") or "").startswith("CY-CHALLENGE-"):
                    challenge_failure_ids.add(str(coverage_finding["id"]))
                coverage_state = coverage_by_category[cid]
                coverage_state["has_unknown"] = True
                coverage_state["missing_evidence"].append(
                    f"{coverage_finding['id']} has no linked unresolved finding; "
                    "coverage Finding remains independently blocked"
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
                penalties.append(
                    {"reason": "coverage unknown", "points": round(reduction, 2), "missing_evidence": missing}
                )
        elif status == "MissingCoverage":
            penalties.append(
                {
                    "reason": "coverage artifact not supplied",
                    "points": 0,
                    "missing_evidence": coverage_state["missing_evidence"],
                }
            )

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
            penalties.append(
                {
                    "finding_id": f["id"],
                    "severity": f["severity"],
                    "reason": f["finding"],
                    "points": round(points, 2),
                }
            )

        awarded = max(0.0, min(float(weight), awarded))
        raw_total += awarded
        per_category.append(
            {
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
            }
        )

    raw_score = round(raw_total)
    caps: List[dict] = []
    cap_value = 100
    if counts["P0"]:
        cap_value = min(cap_value, 49)
        caps.append({"cap": 49, "reason": "unresolved P0 finding"})
    if counts["P1"]:
        cap_value = min(cap_value, 74)
        caps.append({"cap": 74, "reason": "unresolved P1 finding"})
    if challenge_failure_ids:
        counts["P1"] += len(challenge_failure_ids)
        if cap_value > 74:
            cap_value = 74
            caps.append({"cap": 74, "reason": "failing executed challenge"})

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
        caps.append(
            {
                "cap": 90,
                "reason": "score above 90 requires evidence for tests, secrets, deploy/rollback, observability, auth, a"
                "nd data boundaries",
            }
        )

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
            all_evidence = sorted(
                set(category.get("evidence_reviewed") or []) | set(category.get("verified_evidence") or [])
            )
            category["claim_binding"] = [
                {
                    "evidence": evidence,
                    "claim_bound": evidence in bound,
                    "basis": "explicit coverage claim_bound_evidence entry"
                    if evidence in bound
                    else "no explicit claim binding; challenge runner not executed",
                }
                for evidence in all_evidence
            ]
    return result
