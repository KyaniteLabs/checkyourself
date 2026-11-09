"""The 20-surface coverage skeleton and its completeness checker."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, List, Optional, Tuple
from .constants import COVERAGE_SCHEMA_ID, COVERAGE_SURFACES, TOOL_NAME, VALID_COVERAGE_STATUSES
from .receipts import _evidence_root, _resolve_evidence_reference, _verify_receipts
from .util import now_iso


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
        "failed_receipts": [],
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
            failed_receipts=result["failed_receipts"],
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
            failed_receipts=result["failed_receipts"],
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
            errors.append(f"{prefix} surface {raw_surface!r} does not match {sid} ({expected_surface!r})")

        if isinstance(raw_category, str) and raw_category.strip() and raw_category != expected_category:
            errors.append(f"{prefix} category {raw_category!r} does not match {sid} ({expected_category!r})")

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
                not isinstance(item.get(field), list) or not all(isinstance(entry, dict) for entry in item.get(field))
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
