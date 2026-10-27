"""Committed per-surface challenge definitions and semantic contracts."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import re
from typing import Any, List, Optional, Tuple
from .constants import (
    CHALLENGE_SEMANTIC_CONTRACTS,
    COVERAGE_SURFACES,
    DEFAULT_CHALLENGES_PATH,
    TEST_COUNT_RE,
    TEST_RUNNER_MARKERS,
    VACUOUS_REGEX_FIXTURES,
)
from .describe import load_schema
from .jsonlite import strict_json_loads, validate_json_schema


def _default_challenge_definitions() -> dict:
    """Return fail-closed challenge defaults for every canonical surface."""
    return {
        sid: {
            "requires_explicit_config": True,
            "cwd": ".",
            "timeout_s": 60,
            "success": {"exit_zero": True},
            "output_kind": "text",
            "description": "Provide a project-specific verifier command for this surface.",
        }
        for sid, _surface, _category in COVERAGE_SURFACES
    }


def _challenge_surface_map(data: Any) -> Optional[dict]:
    if not isinstance(data, dict):
        return None
    for key in ("challenges", "surfaces", "challenge_registry"):
        value = data.get(key)
        if value is not None:
            return value if isinstance(value, dict) else {}
    return None


def _challenge_patterns(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [pattern for pattern in value if isinstance(pattern, str)]
    return []


def _challenge_artifact_paths(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [path for path in value if isinstance(path, str)]
    return []


def _regex_matches_vacuous_fixture(pattern: str) -> bool:
    try:
        compiled = re.compile(pattern)
    except re.error:
        return False
    return any(compiled.search(fixture) is not None for fixture in VACUOUS_REGEX_FIXTURES)


def _challenge_semantic_contract_errors(definition: dict, surface_id: str) -> List[str]:
    """Reject challenge definitions that cannot produce probative evidence."""
    contract = CHALLENGE_SEMANTIC_CONTRACTS.get(surface_id)
    if contract is None or not isinstance(definition.get("command"), list):
        return []

    command = definition["command"]
    if not command or not all(isinstance(part, str) for part in command):
        return []
    errors: List[str] = []
    executable = Path(command[0]).name.lower()
    command_text = " ".join(command).lower()
    if executable in {"true", "false", "echo", "printf", ":"}:
        errors.append(f"{surface_id} challenge command is a vacuous {executable!r} command")
    for index, part in enumerate(command[:-1]):
        if part == "-c" and re.fullmatch(r"\s*(?:echo|printf)\b.*", command[index + 1], re.I | re.S):
            errors.append(f"{surface_id} challenge command is echo-only and cannot establish evidence")
            break
    for index, part in enumerate(command[:-1]):
        if part == "-c" and re.fullmatch(
            r"\s*(?:print|puts|console\.log)\s*\(?.*?\)?\s*;?\s*", command[index + 1], re.I | re.S
        ):
            errors.append(f"{surface_id} challenge command is print-only and cannot establish evidence")
            break

    success = definition.get("success")
    if not isinstance(success, dict):
        return errors
    json_assertions = _json_field_assertions(success.get("json_field"))
    if any(not path.strip() for path, _expected in json_assertions):
        errors.append(f"{surface_id} challenge JSON assertions must name non-empty fields")
    regex_matches = _challenge_patterns(success.get("regex_match"))
    if not json_assertions and not regex_matches:
        errors.append(
            f"{surface_id} challenge needs a positive output assertion; exit_zero-only evidence is not allowed"
        )
    for pattern in regex_matches:
        if _regex_matches_vacuous_fixture(pattern):
            errors.append(f"{surface_id} challenge regex_match {pattern!r} is vacuous against empty/echo fixtures")

    required_kind = contract.get("required_output_kind")
    if required_kind and definition.get("output_kind", "text") != required_kind:
        errors.append(f"{surface_id} challenge must use {required_kind} output for structured findings")
    required_fields = set(contract.get("required_json_fields") or ())
    if required_fields:
        asserted_fields = {path.split(".", 1)[0] for path, _expected in json_assertions}
        missing = sorted(required_fields - asserted_fields)
        if missing:
            errors.append(
                f"{surface_id} challenge JSON assertions must include structured fields: {', '.join(missing)}"
            )

    if contract.get("requires_test_runner") and not any(marker in command_text for marker in TEST_RUNNER_MARKERS):
        errors.append(f"{surface_id} challenge command must reference a test runner")
    if contract.get("requires_test_count") and not any(
        _pattern_matches_test_count(pattern) for pattern in regex_matches
    ):
        errors.append(f"{surface_id} challenge assertions must include a test pass-count output")

    artifact_paths = _challenge_artifact_paths(success.get("artifact"))
    if contract.get("requires_artifact") and not artifact_paths:
        errors.append(f"{surface_id} challenge must assert a non-empty output artifact")
    for artifact_path in artifact_paths:
        candidate = Path(artifact_path)
        if candidate.is_absolute() or ".." in candidate.parts or not artifact_path.strip():
            errors.append(f"{surface_id} challenge artifact path must stay inside the project root")
    return errors


def _pattern_matches_test_count(pattern: str) -> bool:
    try:
        return TEST_COUNT_RE.search(pattern) is not None or any(
            re.search(pattern, fixture) is not None for fixture in ("1 passed", "2 failed", "3 skipped")
        )
    except re.error:
        return False


def semantic_challenge_errors(data: Any) -> List[str]:
    """Validate verifier-owned semantic contracts for a challenge artifact."""
    surface_map = _challenge_surface_map(data)
    if surface_map is None:
        return []
    if not isinstance(surface_map, dict):
        return ["challenge registry must be an object"]
    canonical_ids = {sid for sid, _surface, _category in COVERAGE_SURFACES}
    errors: List[str] = []
    for surface_id, definition in surface_map.items():
        if surface_id not in canonical_ids or not isinstance(definition, dict):
            continue
        errors.extend(_challenge_semantic_contract_errors(definition, surface_id))
    return list(dict.fromkeys(errors))


def _challenge_definition_errors(definition: Any, surface_id: str) -> List[str]:
    if not isinstance(definition, dict):
        return [f"{surface_id} challenge must be an object"]
    errors: List[str] = []
    command = definition.get("command")
    explicit = definition.get("requires_explicit_config", False)
    if not isinstance(explicit, bool):
        errors.append(f"{surface_id} requires_explicit_config must be boolean")
    if command is not None:
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(part, str) and part.strip() for part in command)
        ):
            errors.append(f"{surface_id} command must be a non-empty argv list of strings")
    elif not explicit:
        errors.append(f"{surface_id} challenge is missing a command")
    if "cwd" in definition:
        cwd = definition.get("cwd")
        if not isinstance(cwd, str) or not cwd.strip():
            errors.append(f"{surface_id} cwd must be a non-empty relative path")
        elif Path(cwd).is_absolute() or ".." in Path(cwd).parts:
            errors.append(f"{surface_id} cwd must stay inside the project root")
    timeout = definition.get("timeout_s", 60)
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(float(timeout))
        or timeout <= 0
    ):
        errors.append(f"{surface_id} timeout_s must be a finite positive number")
    if definition.get("output_kind", "text") not in {"text", "json"}:
        errors.append(f"{surface_id} output_kind must be text or json")

    success = definition.get("success", {"exit_zero": True})
    if not isinstance(success, dict):
        errors.append(f"{surface_id} success must be an object")
    else:
        exit_zero = success.get("exit_zero", True)
        if not isinstance(exit_zero, bool):
            errors.append(f"{surface_id} success.exit_zero must be boolean")
        json_field = success.get("json_field")
        if json_field is not None and not isinstance(json_field, (dict, list)):
            errors.append(f"{surface_id} success.json_field must be an object or array")
        regex_not_match = success.get("regex_not_match", [])
        if isinstance(regex_not_match, str):
            regex_not_match = [regex_not_match]
        if not isinstance(regex_not_match, list) or not all(isinstance(pattern, str) for pattern in regex_not_match):
            errors.append(f"{surface_id} success.regex_not_match must be a string array")
        else:
            for pattern in regex_not_match:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append(f"{surface_id} success.regex_not_match has invalid regex: {exc}")
        regex_match = success.get("regex_match", [])
        if isinstance(regex_match, str):
            regex_match = [regex_match]
        if not isinstance(regex_match, list) or not all(isinstance(pattern, str) for pattern in regex_match):
            errors.append(f"{surface_id} success.regex_match must be a string array")
        else:
            for pattern in regex_match:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append(f"{surface_id} success.regex_match has invalid regex: {exc}")
        artifact = success.get("artifact")
        if artifact is not None:
            artifact_paths = _challenge_artifact_paths(artifact)
            if not artifact_paths or len(artifact_paths) != (
                1 if isinstance(artifact, str) else len(artifact) if isinstance(artifact, list) else 0
            ):
                errors.append(f"{surface_id} success.artifact must be a string or string array")
            elif not all(path.strip() for path in artifact_paths):
                errors.append(f"{surface_id} success.artifact paths must be non-empty strings")
    if not errors:
        errors.extend(_challenge_semantic_contract_errors(definition, surface_id))
    return errors


def load_challenge_config(root: Path) -> Tuple[dict, Optional[str]]:
    """Load committed challenge definitions and merge only explicit overrides."""
    root = root.resolve()
    definitions = _default_challenge_definitions()
    candidates: List[Tuple[Path, Any]] = []
    dedicated = root / DEFAULT_CHALLENGES_PATH
    if dedicated.exists():
        try:
            data = strict_json_loads(dedicated.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            return definitions, f"{dedicated}: could not be parsed as JSON: {exc}"
        candidates.append((dedicated, data))
    else:
        for name in (".checkyourself.json",):
            path = root / name
            if not path.exists():
                continue
            try:
                candidates.append((path, strict_json_loads(path.read_text(encoding="utf-8"))))
            except (OSError, UnicodeError, ValueError) as exc:
                return definitions, f"{path}: could not be parsed as JSON: {exc}"

    config_error: Optional[str] = None
    canonical_ids = {sid for sid, _surface, _category in COVERAGE_SURFACES}
    for path, data in candidates:
        surface_map = _challenge_surface_map(data)
        if surface_map is None:
            continue
        if not isinstance(surface_map, dict):
            config_error = f"{path}: challenge registry must be an object"
            continue
        if path.name == "challenges.json":
            schema_errors = validate_json_schema(data, load_schema("challenges"))
            if schema_errors:
                config_error = f"{path}: invalid challenge configuration: {'; '.join(schema_errors)}"
        for sid, raw_definition in surface_map.items():
            if sid not in canonical_ids:
                config_error = f"{path}: unknown challenge surface {sid!r}"
                continue
            if not isinstance(raw_definition, dict):
                config_error = f"{path}: {sid} challenge must be an object"
                definitions[sid] = raw_definition
                continue
            merged = dict(definitions[sid])
            merged.update(raw_definition)
            definitions[sid] = merged

    definition_errors = [
        error for sid, definition in definitions.items() for error in _challenge_definition_errors(definition, sid)
    ]
    if definition_errors:
        config_error = "; ".join(item for item in (config_error, *definition_errors) if item)
    return definitions, config_error


def _challenge_config_digest(definition: dict) -> str:
    encoded = json.dumps(definition, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _json_path_value(value: Any, path: str) -> Tuple[bool, Any]:
    current = value
    for component in path.split(".") if path else []:
        if isinstance(current, dict) and component in current:
            current = current[component]
        else:
            return False, None
    return True, current


def _json_field_assertions(value: Any) -> List[Tuple[str, Any]]:
    if isinstance(value, dict) and "path" in value:
        return [(str(value.get("path") or ""), value.get("equals", value.get("value")))]
    if isinstance(value, dict):
        return [(str(path), expected) for path, expected in value.items()]
    if isinstance(value, list):
        assertions: List[Tuple[str, Any]] = []
        for item in value:
            if isinstance(item, dict) and "path" in item:
                assertions.append((str(item.get("path") or ""), item.get("equals", item.get("value"))))
        return assertions
    return []
