"""Verifier receipt issuance and executed-receipt verification."""

from __future__ import annotations

from pathlib import Path
import fnmatch
import hashlib
import hmac
import json
import re
from typing import Any, List, Optional, Tuple
from .challenge_config import _challenge_config_digest, load_challenge_config
from .challenge_run import (
    _challenge_result,
    _executed_receipt_binding_digest,
    _executed_receipt_hmac,
    _load_local_integrity_binding_key,
    _run_challenge,
    current_tree_hash,
    semantic_output_digest,
)
from .config import _copy_verification_registry, load_checkyourself_config, validate_verification_registry_config
from .constants import (
    COVERAGE_SURFACES,
    DEFAULT_VERIFICATION_ARTIFACT_REGISTRY,
    EVIDENCE_PATH_RE,
    LOCAL_INTEGRITY_HMAC_FIELD,
    RECEIPT_BINDING_FIELDS,
    RECEIPT_ISSUER,
)
from .errors import CliError
from .jsonlite import strict_json_loads
from .util import now_iso


def _evidence_reference(value: Any) -> Optional[str]:
    """Extract a conservative relative file reference from an assertion."""
    if not isinstance(value, str):
        return None
    matches = list(EVIDENCE_PATH_RE.finditer(value))
    if not matches:
        return None
    return matches[-1].group("path").replace("\\", "/")


def _evidence_root(root: Optional[Path]) -> Path:
    return (root or Path.cwd()).resolve()


def _resolve_evidence_reference(reference: Any, root: Optional[Path]) -> Tuple[Optional[Path], str]:
    extracted = _evidence_reference(reference)
    if not extracted:
        return None, "reference does not contain a file path"
    base = _evidence_root(root)
    candidate = Path(extracted)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(base)
    except (OSError, RuntimeError, ValueError):
        return None, f"reference is outside evidence root {base}"
    if not resolved.is_file():
        return None, "referenced artifact does not exist"
    try:
        content = resolved.read_bytes()
    except (OSError, UnicodeError) as exc:
        return None, f"referenced artifact could not be read: {exc}"
    if not content:
        return None, "referenced artifact is empty"
    return resolved, ""


def _verification_registry_for_root(
    root: Optional[Path], explicit_registry: Optional[dict] = None
) -> Tuple[dict, Optional[str]]:
    if explicit_registry is not None:
        return validate_verification_registry_config(
            {"verification_artifact_registry": explicit_registry},
            "explicit registry",
        )
    config = load_checkyourself_config(_evidence_root(root))
    registry = config.get("verification_artifact_registry")
    if not isinstance(registry, dict):
        registry = _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY)
    return registry, config.get("verification_registry_error")


def _verification_artifact_error(
    artifact: Path,
    root: Optional[Path],
    surface_id: str,
    explicit_registry: Optional[dict] = None,
) -> Optional[str]:
    registry, registry_error = _verification_registry_for_root(root, explicit_registry)
    if registry_error:
        return f"verification artifact registry is invalid: {registry_error}"
    contract = registry.get(surface_id)
    if not isinstance(contract, dict):
        return f"surface {surface_id} has no registered verification artifact contract"
    base = _evidence_root(root)
    try:
        relative = artifact.relative_to(base).as_posix()
    except ValueError:
        return f"artifact is outside evidence root {base}"

    path_match = False
    for root_pattern in contract.get("path_roots", []):
        clean_root = str(root_pattern).strip().strip("/")
        if not clean_root:
            continue
        prefix = clean_root + "/"
        if relative.startswith(prefix):
            within_root = relative[len(prefix) :]
            if within_root and any(
                fnmatch.fnmatch(within_root, pattern) or fnmatch.fnmatch(Path(within_root).name, pattern)
                for pattern in contract.get("path_patterns", [])
            ):
                path_match = True
                break
    if not path_match:
        roots = ", ".join(str(item) for item in contract.get("path_roots", []))
        patterns = ", ".join(str(item) for item in contract.get("path_patterns", []))
        return f"artifact path {relative!r} is not registered for {surface_id} (roots: {roots}; patterns: {patterns})"

    try:
        record = strict_json_loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        return f"artifact {relative!r} is not a valid JSON verification record: {exc}"
    if not isinstance(record, dict):
        return f"artifact {relative!r} must contain a JSON object verification record"
    expected_kind = contract.get("expected_kind")
    if record.get("kind") != expected_kind:
        return f"artifact {relative!r} has kind {record.get('kind')!r}; expected {expected_kind!r}"
    for field in contract.get("required_fields", []):
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"artifact {relative!r} is missing required verification field {field!r}"
    for field, expected in (contract.get("required_values") or {}).items():
        if record.get(field) != expected:
            return f"artifact {relative!r} field {field!r} must equal {expected!r}"
    return None


def _receipt_binding_digest(receipt: dict) -> str:
    """Hash the complete verifier-issued receipt binding, excluding its hash."""
    binding = {field: receipt.get(field) for field in RECEIPT_BINDING_FIELDS}
    encoded = json.dumps(
        binding,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_captured_output(reference: Any, root: Optional[Path]) -> Tuple[Optional[Path], str]:
    extracted = _evidence_reference(reference)
    if not extracted:
        return None, "captured output reference does not contain a file path"
    base = _evidence_root(root)
    candidate = Path(extracted)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(base)
    except (OSError, RuntimeError, ValueError):
        return None, f"captured output is outside evidence root {base}"
    if not resolved.is_file() or resolved.is_symlink():
        return None, "captured output file does not exist as a regular file"
    return resolved, ""


def _verify_executed_receipt(
    receipt: dict,
    root: Optional[Path],
    *,
    expected_surface_id: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Verify an executed receipt by re-running its committed challenge."""
    prefix = "executed receipt"
    if expected_surface_id is None or receipt.get("surface_id") != expected_surface_id:
        return None, None, f"{prefix}: surface binding does not match the coverage surface"
    receipt_id = receipt.get("receipt_sha256")
    if not isinstance(receipt_id, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", receipt_id):
        return None, None, f"{prefix}: receipt_sha256 must be a 64-character hexadecimal binding hash"
    if receipt_id.lower() != _executed_receipt_binding_digest(receipt).lower():
        return None, None, f"{prefix}: receipt_sha256 does not cover executed fields"
    run_id = receipt.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", run_id):
        return None, None, f"{prefix}: run_id is missing or invalid"
    binding_hmac = receipt.get(LOCAL_INTEGRITY_HMAC_FIELD)
    if not isinstance(binding_hmac, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", binding_hmac):
        return None, None, f"{prefix}: local integrity binding HMAC is missing or invalid"
    try:
        binding_key = _load_local_integrity_binding_key(_evidence_root(root), create=False)
    except CliError as exc:
        return None, None, f"{prefix}: local integrity binding key unavailable: {exc}"
    if not hmac.compare_digest(binding_hmac.lower(), _executed_receipt_hmac(receipt, binding_key).lower()):
        return None, None, f"{prefix}: local integrity binding HMAC does not cover executed fields"
    if receipt.get("status") not in {"PASS", "FAIL"}:
        return None, None, f"{prefix}: status must be PASS or FAIL"
    if not isinstance(receipt.get("command"), list) or not all(isinstance(part, str) for part in receipt["command"]):
        return None, None, f"{prefix}: command must be an argv list"
    if not isinstance(receipt.get("source_revision"), str) or not receipt["source_revision"].strip():
        return None, None, f"{prefix}: source_revision is missing"
    if not isinstance(receipt.get("timed_out"), bool):
        return None, None, f"{prefix}: timed_out must be boolean"
    output_path, reason = _resolve_captured_output(receipt.get("captured_output"), root)
    if output_path is None:
        return None, None, f"{prefix}: {reason}"
    try:
        raw_capture = output_path.read_bytes()
    except OSError as exc:
        return None, None, f"{prefix}: could not read captured output: {exc}"
    expected_digest = receipt.get("captured_output_digest")
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_digest):
        return None, None, f"{prefix}: captured_output_digest must be a 64-character hexadecimal hash"
    actual_digest = hashlib.sha256(raw_capture).hexdigest()
    if actual_digest.lower() != expected_digest.lower():
        return None, None, f"{prefix}: captured output digest does not match the stored file"
    try:
        capture = strict_json_loads(raw_capture.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        return None, None, f"{prefix}: captured output is not a valid capture record: {exc}"
    if (
        not isinstance(capture, dict)
        or not isinstance(capture.get("stdout"), str)
        or not isinstance(capture.get("stderr"), str)
    ):
        return None, None, f"{prefix}: captured output record must contain stdout and stderr strings"

    base = _evidence_root(root)
    stored_semantic_digest = receipt.get("semantic_output_digest")
    if stored_semantic_digest is not None and (
        not isinstance(stored_semantic_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", stored_semantic_digest)
    ):
        return None, None, f"{prefix}: semantic_output_digest must be a 64-character hexadecimal hash"
    derived_stored_semantic_digest = semantic_output_digest(
        receipt.get("exit_code"),
        capture["stdout"],
        capture["stderr"],
        receipt["command"],
        root=base,
    )
    if stored_semantic_digest is not None and (
        stored_semantic_digest.lower() != derived_stored_semantic_digest.lower()
    ):
        return None, None, f"{prefix}: semantic output digest does not match the stored capture"
    stored_semantic_digest = stored_semantic_digest or derived_stored_semantic_digest

    definitions, config_error = load_challenge_config(base)
    if config_error:
        return None, None, f"{prefix}: current challenge configuration is invalid: {config_error}"
    definition = definitions.get(expected_surface_id)
    if not isinstance(definition, dict):
        return None, None, f"{prefix}: current challenge definition is missing"
    if receipt.get("challenge_config_digest") != _challenge_config_digest(definition):
        return None, None, f"{prefix}: challenge definition changed since execution"
    if receipt.get("command") != list(definition.get("command") or []):
        return None, None, f"{prefix}: command does not match the committed challenge definition"
    if receipt.get("cwd") != str(definition.get("cwd") or "."):
        return None, None, f"{prefix}: cwd does not match the committed challenge definition"
    current_revision = current_tree_hash(base)
    if receipt.get("source_revision") != current_revision:
        return None, None, f"{prefix}: source revision no longer matches the current project tree"
    fresh = _run_challenge(base, definition, surface_id=expected_surface_id)
    if fresh["exit_code"] != receipt.get("exit_code"):
        return None, None, f"{prefix}: re-executed exit code does not match the receipt"
    if fresh["timed_out"] != receipt.get("timed_out"):
        return None, None, f"{prefix}: re-executed timeout state does not match the receipt"
    if fresh["execution_error"] != str(receipt.get("execution_error") or ""):
        return None, None, f"{prefix}: re-executed error state does not match the receipt"
    fresh_status, fresh_reasons = _challenge_result(
        definition,
        surface_id=expected_surface_id,
        exit_code=fresh["exit_code"],
        stdout=fresh["stdout"],
        stderr=fresh["stderr"],
        timed_out=fresh["timed_out"],
        execution_error=fresh["execution_error"],
        root=base,
    )
    if receipt.get("status") == "PASS" and fresh_status != "PASS":
        return None, None, f"{prefix}: re-executed challenge assertions failed: {'; '.join(fresh_reasons)}"
    if fresh["status"] != receipt.get("status"):
        return None, None, f"{prefix}: re-executed challenge status does not match the receipt"
    fresh_semantic_digest = semantic_output_digest(
        fresh["exit_code"],
        fresh["stdout"],
        fresh["stderr"],
        definition.get("command") or [],
        root=base,
    )
    if fresh_semantic_digest.lower() != stored_semantic_digest.lower():
        return None, None, f"{prefix}: re-executed output digest does not match the receipt (semantic digest mismatch)"
    if current_tree_hash(base) != current_revision:
        return None, None, f"{prefix}: re-execution changed the current project tree"
    derived_status, reasons = _challenge_result(
        definition,
        surface_id=expected_surface_id,
        exit_code=receipt.get("exit_code"),
        stdout=capture["stdout"],
        stderr=capture["stderr"],
        timed_out=receipt.get("timed_out", False),
        execution_error=str(receipt.get("execution_error") or ""),
        root=base,
    )
    if derived_status != receipt.get("status"):
        return None, None, f"{prefix}: stored status does not match captured output and assertions"
    try:
        relative = output_path.relative_to(base).as_posix()
    except ValueError:
        relative = str(output_path)
    if derived_status == "FAIL":
        return relative, "; ".join(reasons) or "executed challenge failed", None
    return relative, None, None


def _receipt_text_fields(receipt: dict) -> List[str]:
    return [
        field
        for field in (
            "reference",
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
        if not isinstance(receipt.get(field), str) or not receipt.get(field, "").strip()
    ]


def issue_receipt(
    reference: str,
    root: Optional[Path],
    *,
    surface_id: str,
    source_revision: str,
    command: str,
    claim: str,
    result: str,
    source_state: str,
    subject_digest: Optional[str] = None,
    registry: Optional[dict] = None,
) -> dict:
    """Issue one receipt bound to a registered verification artifact."""
    canonical_surfaces = {sid for sid, _surface, _category in COVERAGE_SURFACES}
    if surface_id not in canonical_surfaces:
        raise CliError(f"receipt surface_id must be one canonical coverage surface: {surface_id!r}")
    resolved, reason = _resolve_evidence_reference(reference, root)
    if resolved is None:
        raise CliError(f"receipt reference is invalid: {reason}")
    contract_error = _verification_artifact_error(resolved, root, surface_id, registry)
    if contract_error:
        raise CliError(f"receipt reference is not a registered verification artifact: {contract_error}")
    artifact_digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    if subject_digest is not None:
        if not isinstance(subject_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", subject_digest):
            raise CliError("receipt subject_digest must be a 64-character hexadecimal content hash")
        if subject_digest.lower() != artifact_digest.lower():
            raise CliError("receipt subject_digest must match the registered verification artifact")
    subject_digest = artifact_digest
    missing = {
        "source_revision": source_revision,
        "command": command,
        "claim": claim,
        "result": result,
        "source_state": source_state,
    }
    missing_fields = [field for field, value in missing.items() if not str(value or "").strip()]
    if missing_fields:
        raise CliError("receipt fields must not be empty: " + ", ".join(missing_fields))
    try:
        relative = resolved.relative_to(_evidence_root(root)).as_posix()
    except ValueError:
        relative = str(resolved)
    receipt = {
        "receipt_class": "UNVERIFIED",
        "reference": relative,
        "sha256": artifact_digest,
        "subject_digest": subject_digest,
        "surface_id": surface_id,
        "source_revision": str(source_revision).strip(),
        "command": str(command).strip(),
        "claim": str(claim).strip(),
        "origin": "checkyourself verifier receipt command",
        "source_state": str(source_state).strip(),
        "result": str(result).strip(),
        "issuer": RECEIPT_ISSUER,
        "issued_at": now_iso(),
    }
    receipt["receipt_sha256"] = _receipt_binding_digest(receipt)
    return receipt


def _verify_receipts(
    receipts: Any,
    root: Optional[Path],
    *,
    require_provenance: bool = True,
    expected_surface_id: Optional[str] = None,
    expected_claim: Optional[str] = None,
    used_receipt_ids: Optional[set[str]] = None,
    registry: Optional[dict] = None,
    failed_receipts: Optional[List[dict]] = None,
) -> Tuple[List[str], List[str]]:
    """Verify verifier-issued, surface-bound receipts without trusting prose."""
    if not isinstance(receipts, list) or not receipts:
        return [], ["no verifier-captured receipts supplied"]
    verified: List[str] = []
    errors: List[str] = []
    seen_receipt_ids = used_receipt_ids if used_receipt_ids is not None else set()
    for index, receipt in enumerate(receipts):
        prefix = f"receipt {index}"
        if not isinstance(receipt, dict):
            errors.append(f"{prefix} is not an object")
            continue
        if receipt.get("receipt_type") == "EXECUTED":
            receipt_id = receipt.get("receipt_sha256")
            if isinstance(receipt_id, str) and receipt_id.lower() in seen_receipt_ids:
                errors.append(f"{prefix}: receipt reuse is not allowed across surfaces or claims")
                continue
            relative, failure, executed_error = _verify_executed_receipt(
                receipt,
                root,
                expected_surface_id=expected_surface_id,
            )
            if executed_error:
                errors.append(f"{prefix}: {executed_error}")
                continue
            if relative is None:
                errors.append(f"{prefix}: executed receipt did not identify captured output")
                continue
            if receipt_id is not None:
                seen_receipt_ids.add(receipt_id.lower())
            if failure:
                if failed_receipts is not None:
                    failed_receipts.append(
                        {
                            "surface_id": receipt.get("surface_id"),
                            "reference": relative,
                            "reason": failure,
                        }
                    )
                errors.append(f"{prefix}: FAIL — {failure}")
                continue
            verified.append(relative)
            continue
        # Keep the compatibility receipt command, but make its trust boundary
        # explicit. Its fields still originate with the caller and cannot prove
        # that the verifier executed anything.
        errors.append(f"{prefix}: UNVERIFIED caller-issued receipt; run challenge to mint executed evidence")
        continue
        missing_fields = _receipt_text_fields(receipt)
        if missing_fields:
            errors.append(f"{prefix}: missing verifier binding fields: {', '.join(missing_fields)}")
            continue
        if receipt.get("issuer") != RECEIPT_ISSUER:
            errors.append(f"{prefix}: receipt was not issued by {RECEIPT_ISSUER}")
            continue
        receipt_id = receipt.get("receipt_sha256")
        if not isinstance(receipt_id, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", receipt_id):
            errors.append(f"{prefix}: receipt_sha256 must be a 64-character hexadecimal binding hash")
            continue
        if receipt_id.lower() in seen_receipt_ids:
            errors.append(f"{prefix}: receipt reuse is not allowed across surfaces or claims")
            continue
        if expected_surface_id is None:
            errors.append(f"{prefix}: verifier expected a canonical surface binding")
            continue
        if receipt.get("surface_id") != expected_surface_id:
            errors.append(
                f"{prefix}: surface binding {receipt.get('surface_id')!r} does not match {expected_surface_id}"
            )
            continue
        if expected_claim is not None and receipt.get("claim") != expected_claim:
            errors.append(f"{prefix}: claim binding does not match the coverage claim")
            continue
        if receipt_id.lower() != _receipt_binding_digest(receipt).lower():
            errors.append(f"{prefix}: receipt_sha256 does not cover its bound fields")
            continue
        reference = receipt.get("reference")
        resolved, reason = _resolve_evidence_reference(reference, root)
        if resolved is None:
            errors.append(f"{prefix}: {reason}")
            continue
        contract_error = _verification_artifact_error(resolved, root, expected_surface_id, registry)
        if contract_error:
            errors.append(f"{prefix}: {contract_error}")
            continue
        expected_hash = receipt.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash):
            errors.append(f"{prefix}: sha256 must be a 64-character hexadecimal content hash")
            continue
        subject_digest = receipt.get("subject_digest")
        if not isinstance(subject_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", subject_digest):
            errors.append(f"{prefix}: subject_digest must be a 64-character hexadecimal content hash")
            continue
        if subject_digest.lower() != expected_hash.lower():
            errors.append(f"{prefix}: subject_digest does not match the registered verification artifact")
            continue
        try:
            actual_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        except OSError as exc:
            errors.append(f"{prefix}: could not hash referenced artifact: {exc}")
            continue
        if actual_hash.lower() != expected_hash.lower():
            errors.append(f"{prefix}: content hash does not match referenced artifact")
            continue
        subject_key = f"subject:{subject_digest.lower()}"
        reference_key = f"artifact:{receipt.get('reference')}:{subject_digest.lower()}"
        if subject_key in seen_receipt_ids or reference_key in seen_receipt_ids:
            errors.append(f"{prefix}: receipt subject reuse is not allowed across surfaces or claims")
            continue
        if require_provenance:
            missing = [
                field for field in ("origin", "source_state", "result") if not str(receipt.get(field) or "").strip()
            ]
            if missing:
                errors.append(f"{prefix}: missing provenance fields: {', '.join(missing)}")
                continue
        try:
            relative = resolved.relative_to(_evidence_root(root)).as_posix()
        except ValueError:
            relative = str(resolved)
        verified.append(relative)
        seen_receipt_ids.add(receipt_id.lower())
        seen_receipt_ids.add(subject_key)
        seen_receipt_ids.add(reference_key)
    return sorted(set(verified)), errors
