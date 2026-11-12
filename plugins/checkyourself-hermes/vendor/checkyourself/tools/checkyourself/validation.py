"""Artifact validation combining schema and semantic checks."""

from __future__ import annotations

import re
from typing import Any, List
from .challenge_config import semantic_challenge_errors
from .constants import RECEIPT_ISSUER, TOOL_NAME
from .describe import load_schema
from .jsonlite import validate_json_schema
from .receipts import _receipt_binding_digest, _receipt_text_fields
from .report import semantic_report_errors


def semantic_receipt_errors(receipt: Any) -> List[str]:
    """Validate receipt integrity that JSON shape alone cannot establish."""
    if not isinstance(receipt, dict):
        return ["receipt must be an object"]
    errors: List[str] = []
    missing = _receipt_text_fields(receipt)
    if missing:
        errors.append("receipt is missing verifier binding fields: " + ", ".join(missing))
    if receipt.get("issuer") != RECEIPT_ISSUER:
        errors.append(f"receipt issuer must be {RECEIPT_ISSUER}")
    receipt_hash = receipt.get("receipt_sha256")
    if isinstance(receipt_hash, str) and re.fullmatch(r"[0-9a-fA-F]{64}", receipt_hash):
        if receipt_hash.lower() != _receipt_binding_digest(receipt).lower():
            errors.append("receipt_sha256 does not cover the bound fields")
    sha256 = receipt.get("sha256")
    subject_digest = receipt.get("subject_digest")
    if (
        isinstance(sha256, str)
        and re.fullmatch(r"[0-9a-fA-F]{64}", sha256)
        and isinstance(subject_digest, str)
        and re.fullmatch(r"[0-9a-fA-F]{64}", subject_digest)
        and sha256.lower() != subject_digest.lower()
    ):
        errors.append("subject_digest must match the registered verification artifact")
    return errors


def validate_artifact(kind: str, data: Any) -> dict:
    schema = load_schema(kind)
    schema_errors = validate_json_schema(data, schema)
    semantic_errors: List[str] = []
    if kind == "report" and not schema_errors:
        semantic_errors = semantic_report_errors(data)
    elif kind == "receipt" and not schema_errors:
        semantic_errors = semantic_receipt_errors(data)
    elif kind == "challenges" and not schema_errors:
        semantic_errors = semantic_challenge_errors(data)
    errors = schema_errors + semantic_errors
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-validation/1",
        "kind": kind,
        "schema_valid": not schema_errors,
        "semantic_valid": not semantic_errors,
        "valid": not errors,
        "errors": errors,
        "semantic_errors": semantic_errors,
    }
