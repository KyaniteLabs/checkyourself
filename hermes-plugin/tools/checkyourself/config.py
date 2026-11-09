"""Loading and validation of .checkyourself.yml/.json configuration and suppressions."""

from __future__ import annotations

from pathlib import Path
import fnmatch
import re
from typing import Any, List, Optional, Tuple
from .constants import CONFIG_NAMES, COVERAGE_SURFACES, DEFAULT_VERIFICATION_ARTIFACT_REGISTRY
from .jsonlite import strict_json_loads
from .util import parse_scalar


def parse_minimal_yaml_suppressions(text: str) -> List[dict]:
    suppressions: List[dict] = []
    current: Optional[dict] = None
    current_item_indent: Optional[int] = None
    current_list_key: Optional[str] = None
    in_suppress = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("suppress:"):
            value = stripped.split(":", 1)[1].strip()
            if value not in {"", "[]"}:
                raise ValueError("suppress must be a YAML list")
            in_suppress = True
            continue
        if in_suppress and not raw_line[:1].isspace() and not stripped.startswith("- "):
            # A new zero-indent top-level key ends the suppress block.
            if current:
                suppressions.append(current)
                current = None
            current_list_key = None
            in_suppress = False
        if not in_suppress:
            continue
        if stripped.startswith("- "):
            indent = len(raw_line) - len(raw_line.lstrip())
            if (
                current is not None
                and current_list_key
                and current_item_indent is not None
                and indent > current_item_indent
            ):
                current[current_list_key].append(parse_scalar(stripped[2:].strip()))
                continue
            if current:
                suppressions.append(current)
            current = {}
            current_item_indent = indent
            current_list_key = None
            stripped = stripped[2:].strip()
            if stripped and ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key.strip()] = parse_scalar(value)
            elif stripped:
                raise ValueError("suppression list items must be mappings")
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            current[key] = [] if not value.strip() else parse_scalar(value)
            current_list_key = key if not value.strip() else None

    if current:
        suppressions.append(current)
    return suppressions


def validate_suppressions_config(data: Any, name: str) -> dict:
    if not isinstance(data, dict):
        return {"suppress": [], "config_error": f"{name} must contain a JSON/YAML object"}
    suppressions = data.get("suppress", [])
    if not isinstance(suppressions, list):
        return {"suppress": [], "config_error": f"{name} suppress must be a list"}
    for index, suppression in enumerate(suppressions):
        if not isinstance(suppression, dict):
            return {"suppress": [], "config_error": f"{name} suppression {index} must be an object"}
        for key in ("id", "reason", "reviewed_by", "reviewed_at"):
            if key in suppression and not isinstance(suppression[key], str):
                return {"suppress": [], "config_error": f"{name} suppression {index} field {key} must be a string"}
        for key in ("files", "paths"):
            if key not in suppression:
                continue
            value = suppression[key]
            if isinstance(value, str):
                continue
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                return {
                    "suppress": [],
                    "config_error": f"{name} suppression {index} field {key} must be a string or list of strings",
                }
        has_id = isinstance(suppression.get("id"), str) and bool(suppression["id"].strip())
        has_path = any(
            (isinstance(suppression.get(key), str) and bool(suppression[key].strip()))
            or (isinstance(suppression.get(key), list) and bool(suppression[key]))
            for key in ("files", "paths")
        )
        if not has_id and not has_path:
            return {"suppress": [], "config_error": f"{name} suppression {index} needs id, files, or paths"}
    return {"suppress": suppressions}


def _copy_verification_registry(registry: dict) -> dict:
    return {
        sid: {
            "path_roots": list(contract["path_roots"]),
            "path_patterns": list(contract["path_patterns"]),
            "expected_kind": contract["expected_kind"],
            "required_fields": list(contract["required_fields"]),
            "required_values": dict(contract.get("required_values") or {}),
        }
        for sid, contract in registry.items()
    }


def _registry_list(value: Any, field: str, name: str, sid: str) -> Tuple[Optional[List[str]], Optional[str]]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        return None, f"{name} verification registry {sid} field {field} must be a non-empty string list"
    return [item.strip() for item in value], None


def validate_verification_registry_config(data: Any, name: str) -> Tuple[dict, Optional[str]]:
    """Validate and normalize explicit per-surface artifact contracts."""
    defaults = _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY)
    if not isinstance(data, dict):
        return defaults, None
    configured = data.get("verification_artifact_registry")
    if configured is None:
        return defaults, None
    if not isinstance(configured, dict):
        return defaults, f"{name} verification_artifact_registry must be an object"

    registry = _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY)
    canonical_ids = {sid for sid, _surface, _category in COVERAGE_SURFACES}
    for sid, raw_contract in configured.items():
        if sid not in canonical_ids:
            return defaults, f"{name} verification registry has unknown surface: {sid!r}"
        if not isinstance(raw_contract, dict):
            return defaults, f"{name} verification registry {sid} must be an object"

        # Accept the shorter aliases so an explicit config can stay readable,
        # while exposing one stable normalized shape to the verifier.
        contract = dict(registry[sid])
        aliases = {
            "path_roots": ("path_roots", "roots", "allowed_roots"),
            "path_patterns": ("path_patterns", "patterns", "allowed_patterns"),
        }
        for target, keys in aliases.items():
            for key in keys:
                if key in raw_contract:
                    values, error = _registry_list(raw_contract[key], target, name, sid)
                    if error:
                        return defaults, error
                    contract[target] = values or []
                    break
        if "expected_kind" in raw_contract:
            if not isinstance(raw_contract["expected_kind"], str) or not raw_contract["expected_kind"].strip():
                return defaults, f"{name} verification registry {sid} field expected_kind must be a non-empty string"
            contract["expected_kind"] = raw_contract["expected_kind"].strip()
        if "required_fields" in raw_contract:
            values, error = _registry_list(raw_contract["required_fields"], "required_fields", name, sid)
            if error:
                return defaults, error
            contract["required_fields"] = values or []
        if "required_values" in raw_contract:
            values = raw_contract["required_values"]
            if not isinstance(values, dict) or not all(
                isinstance(key, str) and key.strip() and isinstance(value, (str, int, float, bool))
                for key, value in values.items()
            ):
                return (
                    defaults,
                    f"{name} verification registry {sid} field required_values must be an object of scalar values",
                )
            contract["required_values"] = dict(values)

        for root in contract["path_roots"]:
            root_path = Path(root)
            if root_path.is_absolute() or ".." in root_path.parts:
                return defaults, f"{name} verification registry {sid} path_roots must stay inside the evidence root"
        for pattern in contract["path_patterns"]:
            if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                return defaults, f"{name} verification registry {sid} path_patterns must stay inside the surface root"

        required_fields = list(dict.fromkeys(contract["required_fields"] + ["surface_id", "kind"]))
        required_values = dict(contract.get("required_values") or {})
        required_values["surface_id"] = sid
        required_values.setdefault("kind", contract["expected_kind"])
        contract["required_fields"] = required_fields
        contract["required_values"] = required_values
        registry[sid] = contract
    return registry, None


def _config_with_registry(data: Any, name: str) -> dict:
    suppressions = validate_suppressions_config(data, name)
    registry, registry_error = validate_verification_registry_config(data, name)
    result = {
        "suppress": suppressions.get("suppress", []),
        "verification_artifact_registry": registry,
    }
    if suppressions.get("config_error"):
        result["config_error"] = suppressions["config_error"]
    if registry_error:
        result["verification_registry_error"] = registry_error
        result["config_error"] = "; ".join(item for item in (result.get("config_error"), registry_error) if item)
    return result


def load_checkyourself_config(root: Path) -> dict:
    for name in CONFIG_NAMES:
        path = root / name
        if not path.exists():
            continue
        if path.suffix == ".json":
            try:
                data = strict_json_loads(path.read_text(encoding="utf-8"))
                return _config_with_registry(data, name)
            except (ValueError, OSError, UnicodeError):
                return {
                    "suppress": [],
                    "verification_artifact_registry": _copy_verification_registry(
                        DEFAULT_VERIFICATION_ARTIFACT_REGISTRY
                    ),
                    "verification_registry_error": f"{name} could not be parsed as JSON",
                    "config_error": f"{name} could not be parsed as JSON",
                }
        try:
            # The minimal YAML parser intentionally remains suppression-only.
            # JSON is the explicit configuration format for registry overrides.
            return _config_with_registry(
                {"suppress": parse_minimal_yaml_suppressions(path.read_text(encoding="utf-8"))},
                name,
            )
        except (OSError, UnicodeError, ValueError) as exc:
            return {
                "suppress": [],
                "verification_artifact_registry": _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY),
                "verification_registry_error": f"{name} is invalid: {exc}",
                "config_error": f"{name} is invalid: {exc}",
            }
    return {
        "suppress": [],
        "verification_artifact_registry": _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY),
    }


def evidence_path(evidence: str) -> str:
    first = evidence.split(" (", 1)[0]
    match = re.match(r"^(.+):(\d+)$", first)
    return match.group(1) if match else first


def suppression_matches(finding: dict, suppression: dict) -> bool:
    sid = str(suppression.get("id") or "").strip()
    files = suppression.get("files") or suppression.get("paths") or []
    if not sid and not files:
        return False
    if sid and sid not in {str(finding.get("id")), str(finding.get("finding")), str(finding.get("title"))}:
        return False
    if isinstance(files, str):
        files = [files]
    if files:
        paths = [evidence_path(str(item)) for item in finding.get("evidence") or []]
        if not any(fnmatch.fnmatch(path, pattern) or path == pattern for path in paths for pattern in files):
            return False
    return True


def apply_suppressions(findings: List[dict], suppressions: List[dict]) -> List[dict]:
    for finding in findings:
        for suppression in suppressions:
            sid = str(suppression.get("id") or "").strip()
            files = suppression.get("files") or suppression.get("paths") or []
            if isinstance(files, str):
                files = [files]
            if sid and sid not in {str(finding.get("id")), str(finding.get("finding")), str(finding.get("title"))}:
                continue
            evidence = [str(item) for item in finding.get("evidence") or []]
            if files:
                matched = [
                    item
                    for item in evidence
                    if any(
                        fnmatch.fnmatch(evidence_path(item), pattern) or evidence_path(item) == pattern
                        for pattern in files
                    )
                ]
                if not matched:
                    continue
                finding["evidence"] = [item for item in evidence if item not in matched]
                finding.setdefault("suppressed_evidence", []).extend(
                    {
                        "evidence": item,
                        "reason": str(suppression.get("reason") or "reviewed suppression"),
                        "reviewed_by": str(suppression.get("reviewed_by") or ""),
                        "reviewed_at": str(suppression.get("reviewed_at") or ""),
                    }
                    for item in matched
                )
                if finding["evidence"]:
                    continue
            elif not suppression_matches(finding, suppression):
                continue
            if not files or not finding.get("evidence"):
                finding["status"] = "suppressed"
                finding["suppression"] = {
                    "reason": str(suppression.get("reason") or "reviewed suppression"),
                    "reviewed_by": str(suppression.get("reviewed_by") or ""),
                    "reviewed_at": str(suppression.get("reviewed_at") or ""),
                }
                break
    return findings
