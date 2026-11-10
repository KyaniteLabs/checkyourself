"""Loading and validation of .checkyourself.yml/.json configuration, suppressions and resolutions."""

from __future__ import annotations

from pathlib import Path
import fnmatch
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from .constants import (
    CONFIG_NAMES,
    COVERAGE_SURFACES,
    DEFAULT_VERIFICATION_ARTIFACT_REGISTRY,
    RESOLVE_SCHEMA_ID,
    is_resolved_status,
)
from .jsonlite import strict_json_loads
from .errors import CliError
from .output import safe_write_text
from .util import parse_scalar


def _strip_yaml_comment(line: str) -> str:
    """Strip a YAML comment marker unless it sits inside a quoted scalar."""
    quote: Optional[str] = None
    escaped = False
    for index, char in enumerate(line):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\" and quote == '"':
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "#":
            return line[:index]
    return line


def parse_minimal_yaml_sections(text: str, section_names: Tuple[str, ...] = ("suppress",)) -> dict:
    """Parse the small list-of-mapping sections CheckYourself owns.

    The project config is deliberately not a general YAML implementation.  It
    understands top-level keys whose value is a list of mappings, which covers
    both reviewed suppressions and durable resolved dispositions.
    """
    sections: dict = {name: [] for name in section_names}
    current: Optional[dict] = None
    current_item_indent: Optional[int] = None
    current_list_key: Optional[str] = None
    active: Optional[str] = None

    def flush_current() -> None:
        nonlocal current
        if current is not None and active is not None:
            sections[active].append(current)
        current = None

    for raw_line in text.splitlines():
        line = _strip_yaml_comment(raw_line).rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if indent == 0 and not stripped.startswith("- "):
            # A new zero-indent top-level key ends the active list section.
            if active is not None:
                flush_current()
                current_list_key = None
                active = None
            if ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            key = key.strip()
            if key not in sections:
                continue
            if value.strip() not in {"", "[]"}:
                raise ValueError(f"{key} must be a YAML list")
            active = key
            continue

        if active is None:
            continue

        if stripped.startswith("- "):
            item_indent = indent
            if (
                current is not None
                and current_list_key
                and current_item_indent is not None
                and item_indent > current_item_indent
            ):
                current[current_list_key].append(parse_scalar(stripped[2:].strip()))
                continue
            flush_current()
            current = {}
            current_item_indent = item_indent
            current_list_key = None
            item = stripped[2:].strip()
            if item and ":" in item:
                key, value = item.split(":", 1)
                current[key.strip()] = parse_scalar(value)
            elif item:
                raise ValueError(f"{active} list items must be mappings")
            continue

        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            current[key] = [] if not value.strip() else parse_scalar(value)
            current_list_key = key if not value.strip() else None

    flush_current()
    return sections


def parse_minimal_yaml_suppressions(text: str) -> List[dict]:
    """Backward-compatible suppression-only entry point."""
    return parse_minimal_yaml_sections(text, ("suppress",))["suppress"]


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


def validate_resolutions_config(data: Any, name: str) -> dict:
    """Validate durable ``resolve:`` dispositions that close a finding.

    Only ``not-applicable`` is accepted: a finding cannot be declared
    ``fixed`` by configuration while the detector still emits it.  A reason is
    mandatory so the promotion stays reviewable after the scan artifact is
    regenerated.
    """
    if not isinstance(data, dict):
        return {"resolve": [], "config_error": f"{name} must contain a JSON/YAML object"}
    resolutions = data.get("resolve", [])
    if not isinstance(resolutions, list):
        return {"resolve": [], "config_error": f"{name} resolve must be a list"}
    normalized: List[dict] = []
    for index, resolution in enumerate(resolutions):
        if not isinstance(resolution, dict):
            return {"resolve": [], "config_error": f"{name} resolution {index} must be an object"}
        for key in ("id", "reason", "status", "reviewed_by", "reviewed_at"):
            if key in resolution and not isinstance(resolution[key], str):
                return {
                    "resolve": [],
                    "config_error": f"{name} resolution {index} field {key} must be a string",
                }
        finding_id = str(resolution.get("id") or "").strip()
        if not finding_id:
            return {"resolve": [], "config_error": f"{name} resolution {index} needs a finding id"}
        status = str(resolution.get("status") or "not-applicable").strip()
        if status != "not-applicable":
            return {
                "resolve": [],
                "config_error": (
                    f"{name} resolution {index} status must be not-applicable; "
                    "fix the exposure or remove the detector finding to mark it fixed"
                ),
            }
        reason = str(resolution.get("reason") or "").strip()
        if not reason:
            return {"resolve": [], "config_error": f"{name} resolution {index} needs a reason"}
        files: List[str] = []
        for key in ("files", "paths"):
            if key not in resolution:
                continue
            value = resolution[key]
            if isinstance(value, str):
                value = [value]
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                return {
                    "resolve": [],
                    "config_error": f"{name} resolution {index} field {key} must be a string or list of strings",
                }
            files.extend(item.strip() for item in value if item.strip())
        entry: Dict[str, Any] = {
            "id": finding_id,
            "status": "not-applicable",
            "reason": reason,
            "reviewed_by": str(resolution.get("reviewed_by") or "").strip(),
            "reviewed_at": str(resolution.get("reviewed_at") or "").strip(),
        }
        if files:
            entry["files"] = list(dict.fromkeys(files))
        normalized.append(entry)
    return {"resolve": normalized}


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
    resolutions = validate_resolutions_config(data, name)
    registry, registry_error = validate_verification_registry_config(data, name)
    result = {
        "suppress": suppressions.get("suppress", []),
        "resolve": resolutions.get("resolve", []),
        "verification_artifact_registry": registry,
    }
    if suppressions.get("config_error"):
        result["config_error"] = suppressions["config_error"]
    if resolutions.get("config_error"):
        result["config_error"] = "; ".join(
            item for item in (result.get("config_error"), resolutions["config_error"]) if item
        )
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
                    "resolve": [],
                    "verification_artifact_registry": _copy_verification_registry(
                        DEFAULT_VERIFICATION_ARTIFACT_REGISTRY
                    ),
                    "verification_registry_error": f"{name} could not be parsed as JSON",
                    "config_error": f"{name} could not be parsed as JSON",
                }
        try:
            # The minimal YAML parser reads reviewed suppressions and durable
            # resolved dispositions. JSON is the explicit configuration format
            # for registry overrides.
            sections = parse_minimal_yaml_sections(path.read_text(encoding="utf-8"), ("suppress", "resolve"))
            return _config_with_registry(sections, name)
        except (OSError, UnicodeError, ValueError) as exc:
            return {
                "suppress": [],
                "resolve": [],
                "verification_artifact_registry": _copy_verification_registry(DEFAULT_VERIFICATION_ARTIFACT_REGISTRY),
                "verification_registry_error": f"{name} is invalid: {exc}",
                "config_error": f"{name} is invalid: {exc}",
            }
    return {
        "suppress": [],
        "resolve": [],
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


def resolution_matches(finding: dict, resolution: dict) -> bool:
    """Match a durable disposition without hiding unrelated evidence.

    A path-scoped resolution only applies when every evidence path falls
    inside the reviewed scope.  A broader id-only disposition covers the whole
    finding.
    """
    sid = str(resolution.get("id") or "").strip()
    files = resolution.get("files") or resolution.get("paths") or []
    if not sid and not files:
        return False
    if sid and sid not in {str(finding.get("id")), str(finding.get("finding")), str(finding.get("title"))}:
        return False
    if isinstance(files, str):
        files = [files]
    if not files:
        return True
    paths = [evidence_path(str(item)) for item in finding.get("evidence") or []]
    return bool(paths) and all(
        any(fnmatch.fnmatch(path, pattern) or path == pattern for pattern in files) for path in paths
    )


def apply_resolutions(findings: List[dict], resolutions: List[dict]) -> List[dict]:
    """Promote findings with a durable reviewed disposition.

    Resolutions are applied before suppressions so a reviewed
    ``not-applicable`` disposition wins over a broader suppression entry.
    """
    for finding in findings:
        for resolution in resolutions:
            if not resolution_matches(finding, resolution):
                continue
            finding["status"] = "not-applicable"
            finding["disposition"] = {
                "status": "not-applicable",
                "reason": str(resolution.get("reason") or ""),
                "reviewed_by": str(resolution.get("reviewed_by") or ""),
                "reviewed_at": str(resolution.get("reviewed_at") or ""),
            }
            break
    return findings


def _resolution_key(entry: dict) -> Tuple[str, Tuple[str, ...]]:
    files = entry.get("files") or entry.get("paths") or []
    if isinstance(files, str):
        files = [files]
    return (
        str(entry.get("id") or "").strip(),
        tuple(sorted(str(item).strip() for item in files if str(item).strip())),
    )


def _upsert_resolution(existing: List[dict], entry: dict) -> List[dict]:
    key = _resolution_key(entry)
    updated: List[dict] = []
    replaced = False
    for resolution in existing:
        if isinstance(resolution, dict) and _resolution_key(resolution) == key:
            updated.append(entry)
            replaced = True
        else:
            updated.append(resolution)
    if not replaced:
        updated.append(entry)
    return updated


def _render_resolve_block(resolutions: List[dict]) -> str:
    lines = ["resolve:"]
    for resolution in resolutions:
        lines.append(f"  - id: {json.dumps(str(resolution.get('id') or ''))}")
        lines.append("    status: not-applicable")
        lines.append(f"    reason: {json.dumps(str(resolution.get('reason') or ''))}")
        files = resolution.get("files") or resolution.get("paths") or []
        if isinstance(files, str):
            files = [files]
        if files:
            lines.append("    files: [" + ", ".join(json.dumps(str(item)) for item in files) + "]")
        reviewed_by = str(resolution.get("reviewed_by") or "")
        if reviewed_by:
            lines.append(f"    reviewed_by: {json.dumps(reviewed_by)}")
        reviewed_at = str(resolution.get("reviewed_at") or "")
        if reviewed_at:
            lines.append(f"    reviewed_at: {json.dumps(reviewed_at)}")
    return "\n".join(lines) + "\n"


def _replace_top_level_block(text: str, key: str, block: str) -> Optional[str]:
    lines = text.splitlines(keepends=True)
    start = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(key + ":") and not line[:1].isspace():
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped and not lines[index][:1].isspace() and not stripped.startswith("- "):
            end = index
            break
    return "".join(lines[:start]) + block + "".join(lines[end:])


def write_resolution(root: Path, entry: dict) -> dict:
    """Write one durable ``not-applicable`` disposition to project config."""
    root = root.resolve()
    if not root.is_dir():
        raise CliError(f"project root not found: {root}")
    normalized = validate_resolutions_config({"resolve": [entry]}, "config")
    if normalized.get("config_error"):
        raise CliError(str(normalized["config_error"]))
    resolution = normalized["resolve"][0]
    path = next((root / name for name in CONFIG_NAMES if (root / name).exists()), root / CONFIG_NAMES[0])
    if path.suffix == ".json":
        if path.exists():
            data = strict_json_loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise CliError(f"{path.name} must contain a JSON object")
        else:
            data = {"version": 1}
        existing = data.get("resolve") or []
        if not isinstance(existing, list):
            raise CliError(f"{path.name} resolve must be a list")
        data["resolve"] = _upsert_resolution(existing, resolution)
        body = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    else:
        text = path.read_text(encoding="utf-8") if path.exists() else "version: 1\n"
        sections = parse_minimal_yaml_sections(text, ("suppress", "resolve"))
        updated = _upsert_resolution(sections["resolve"], resolution)
        block = _render_resolve_block(updated)
        replacement = _replace_top_level_block(text, "resolve", block)
        if replacement is None:
            replacement = text.rstrip() + "\n\n" + block if text.strip() else "version: 1\n\n" + block
        body = replacement if replacement.endswith("\n") else replacement + "\n"
    safe_write_text(path, body)
    return {
        "tool": "checkyourself-cli",
        "schema": RESOLVE_SCHEMA_ID,
        "config": str(path),
        "finding_id": resolution["id"],
        "status": resolution["status"],
        "reason": resolution["reason"],
        "reviewed_by": resolution["reviewed_by"],
        "reviewed_at": resolution["reviewed_at"],
        "files": resolution.get("files", []),
    }


def apply_suppressions(findings: List[dict], suppressions: List[dict]) -> List[dict]:
    for finding in findings:
        if is_resolved_status(finding.get("status")):
            continue
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
