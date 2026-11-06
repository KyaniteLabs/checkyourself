"""Strict JSON parsing and the bundled JSON-schema subset validator."""

from __future__ import annotations

from pathlib import Path
import json
import math
import re
import sys
from typing import Any, List
from .errors import CliError


def _ensure_finite_json(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number is not valid JSON")
    if isinstance(value, dict):
        for item in value.values():
            _ensure_finite_json(item)
    elif isinstance(value, list):
        for item in value:
            _ensure_finite_json(item)


def strict_json_loads(body: str) -> Any:
    """Parse standard JSON only; Python otherwise accepts NaN and Infinity."""

    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite number {token} is not valid JSON")

    # A UTF-8 BOM is metadata about the byte stream, not part of the JSON
    # document. Accept it at the boundary so receipts from BOM-aware editors
    # remain usable; a BOM anywhere else is still invalid JSON.
    if body.startswith("\ufeff"):
        body = body[1:]
    value = json.loads(body, parse_constant=reject_constant)
    _ensure_finite_json(value)
    return value


def load_json_arg(path: str) -> Any:
    if path == "-":
        body = sys.stdin.read()
    else:
        p = Path(path)
        if not p.exists():
            raise CliError(f"JSON file not found: {path}")
        try:
            body = p.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise CliError(f"could not read JSON in {path}: {exc}") from exc
    try:
        return strict_json_loads(body)
    except (ValueError, UnicodeError) as exc:
        raise CliError(f"invalid JSON in {path}: {exc}") from exc


def json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    return type(value).__name__


def type_matches(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(type_matches(value, item) for item in expected)
    actual = json_type_name(value)
    return actual == expected or (expected == "number" and actual == "integer")


_SCHEMA_ANNOTATION_KEYWORDS = {
    "$schema",
    "$id",
    "$comment",
    "title",
    "description",
    "default",
    "examples",
    "deprecated",
    "readOnly",
    "writeOnly",
}

_SCHEMA_VALIDATION_KEYWORDS = {
    "type",
    "enum",
    "const",
    "oneOf",
    "anyOf",
    "allOf",
    "not",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
}


def _schema_definition_errors(schema: Any, path: str = "$") -> List[str]:
    """Find unsupported keywords anywhere in a schema before validating data."""
    if schema is True or schema is False:
        return []
    if not isinstance(schema, dict):
        return [f"{path}: schema must be an object or boolean"]
    errors: List[str] = []
    unsupported = sorted(set(schema) - _SCHEMA_ANNOTATION_KEYWORDS - _SCHEMA_VALIDATION_KEYWORDS)
    if unsupported:
        errors.append(f"{path}: unsupported schema keyword(s): {', '.join(unsupported)}")
    for keyword in ("oneOf", "anyOf", "allOf"):
        branches = schema.get(keyword)
        if branches is not None and isinstance(branches, list):
            for index, branch in enumerate(branches):
                errors.extend(_schema_definition_errors(branch, f"{path}.{keyword}[{index}]"))
    if "not" in schema:
        errors.extend(_schema_definition_errors(schema["not"], f"{path}.not"))
    props = schema.get("properties")
    if isinstance(props, dict):
        for key, subschema in props.items():
            errors.extend(_schema_definition_errors(subschema, f"{path}.properties.{key}"))
    for keyword in ("additionalProperties", "items"):
        subschema = schema.get(keyword)
        if isinstance(subschema, dict):
            errors.extend(_schema_definition_errors(subschema, f"{path}.{keyword}"))
    return errors


def validate_json_schema(data: Any, schema: Any, path: str = "$", _check_schema: bool = True) -> List[str]:
    """Validate the bundled schema subset without silently ignoring keywords.

    The CLI intentionally stays standard-library-only.  Every validation keyword
    supported here has executable semantics; an unknown keyword is an error so a
    schema cannot claim a constraint that this validator quietly skips.
    """
    errors: List[str] = []
    if _check_schema:
        errors.extend(_schema_definition_errors(schema, path))
    if isinstance(data, float) and not math.isfinite(data):
        return errors + [f"{path}: non-finite number is not valid JSON"]
    if schema is True:
        return errors
    if schema is False:
        return [f"{path}: schema is false"]
    if not isinstance(schema, dict):
        return [f"{path}: schema must be an object or boolean"]

    for keyword, relation in (("oneOf", "exactly one"), ("anyOf", "at least one")):
        if keyword not in schema:
            continue
        branches = schema[keyword]
        if not isinstance(branches, list) or not branches:
            errors.append(f"{path}: {keyword} must be a non-empty array")
            continue
        branch_errors = [validate_json_schema(data, branch, path, False) for branch in branches]
        matches = sum(not branch_error for branch_error in branch_errors)
        valid = matches == 1 if keyword == "oneOf" else matches >= 1
        if not valid:
            errors.append(f"{path}: {keyword} must match {relation} schema (matched {matches})")

    if "allOf" in schema:
        branches = schema["allOf"]
        if not isinstance(branches, list):
            errors.append(f"{path}: allOf must be an array")
        else:
            for branch in branches:
                errors.extend(validate_json_schema(data, branch, path, False))

    if "not" in schema and not validate_json_schema(data, schema["not"], path, False):
        errors.append(f"{path}: value must not match the not schema")

    if "type" in schema and not type_matches(data, schema["type"]):
        errors.append(f"{path}: expected {schema['type']}, got {json_type_name(data)}")
        return errors
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: value {data!r} not in enum {schema['enum']!r}")
    if "const" in schema and data != schema["const"]:
        errors.append(f"{path}: value {data!r} does not equal const {schema['const']!r}")

    if isinstance(data, dict):
        required = schema.get("required", [])
        if not isinstance(required, list) or not all(isinstance(key, str) for key in required):
            errors.append(f"{path}: required must be an array of strings")
            required = []
        for key in required:
            if key not in data:
                errors.append(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        if not isinstance(props, dict):
            errors.append(f"{path}: properties must be an object")
            props = {}
        for key, subschema in props.items():
            if key in data:
                errors.extend(validate_json_schema(data[key], subschema, f"{path}.{key}", False))
        additional = schema.get("additionalProperties", True)
        if additional not in (True, False) and not isinstance(additional, dict):
            errors.append(f"{path}: additionalProperties must be boolean or an object")
            additional = False
        for key, value in data.items():
            if key in props or additional is True:
                continue
            if additional is False:
                errors.append(f"{path}: unexpected key {key!r}")
            else:
                errors.extend(validate_json_schema(value, additional, f"{path}.{key}", False))

    if isinstance(data, list):
        items = schema.get("items")
        if items is not None and not isinstance(items, (dict, bool)):
            errors.append(f"{path}: items must be an object or boolean")
        elif isinstance(items, (dict, bool)):
            for i, item in enumerate(data):
                errors.extend(validate_json_schema(item, items, f"{path}[{i}]", False))
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append(f"{path}: array has {len(data)} items, below minimum {schema['minItems']}")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errors.append(f"{path}: array has {len(data)} items, above maximum {schema['maxItems']}")
        if schema.get("uniqueItems"):
            try:
                unique = len({json.dumps(item, sort_keys=True) for item in data}) == len(data)
            except (TypeError, ValueError):
                unique = False
            if not unique:
                errors.append(f"{path}: array items must be unique")

    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"{path}: string length is below minimum {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(f"{path}: string length is above maximum {schema['maxLength']}")
        if "pattern" in schema:
            try:
                matches = re.search(schema["pattern"], data) is not None
            except (re.error, TypeError):
                errors.append(f"{path}: invalid schema pattern")
                matches = True
            if not matches:
                errors.append(f"{path}: value does not match pattern {schema['pattern']!r}")

    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} is below minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} is above maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: {data} is not above exclusive minimum {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and data >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: {data} is not below exclusive maximum {schema['exclusiveMaximum']}")
    return errors
