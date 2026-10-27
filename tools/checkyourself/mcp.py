"""Thin stdio MCP server exposing the same verbs as the CLI."""

from __future__ import annotations

from pathlib import Path
import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional
from .constants import MCP_PROTOCOL_VERSION, SUPPORTED_MCP_PROTOCOLS
from .coverage import coverage_check, coverage_emit
from .describe import describe_capabilities, load_schema, read_manifest_version, schema_registry
from .errors import CLI_ENTRY, CliError, retry_message
from .jsonlite import strict_json_loads, validate_json_schema
from .planning import backlog_from_findings, diff_findings, next_from_findings
from .receipts import issue_receipt
from .scan import scan
from .scanning import DEFAULT_MAX_FILES
from .scoring import score_from_inputs
from .validation import validate_artifact


_SCHEMA_NAMES = sorted(schema_registry().keys())


def read_only_annotations(title: str) -> dict:
    return {
        "title": title,
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }


def object_schema(properties: dict, required: Optional[List[str]] = None) -> dict:
    schema = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def description(*parts: str) -> str:
    safety = (
        "Requires no authentication. It reads local inputs only, does not make network calls, "
        "does not modify local files, and has no external rate limits."
    )
    return " ".join([*parts, safety])


def findings_schema(action: str) -> dict:
    return {
        "type": ["object", "array"],
        "description": (
            "Scan result object, CheckYourself report object, object with findings/remediation_backlog, "
            f"or a plain list of finding objects to {action}."
        ),
    }


def _tool_describe() -> dict:
    return {
        "name": "describe",
        "title": "Describe CheckYourself",
        "description": description(
            "Return CheckYourself's machine-readable capability manifest: CLI commands, MCP "
            "transport, schema names, "
            "scoring weights, score caps, coverage surfaces, exit codes, and public-repository scope guardrails. "
            "This is a read-only discovery tool and does not scan a project."
        ),
        "inputSchema": object_schema({}),
        "annotations": read_only_annotations("Describe CheckYourself"),
        "outputSchema": {
            "type": "object",
            "description": "Capability manifest using schema checkyourself-capabilities/1.",
        },
    }


def _tool_scan() -> dict:
    return {
        "name": "scan",
        "title": "Scan Project",
        "description": description(
            "Inspect a local project directory for deterministic production-readiness "
            "signals: stack, scripts, CI, tests, "
            "environment files, obvious secret/config risks, generated findings, counts, "
            "and public-repo claim guardrails. "
            "MCP mode returns JSON only; it does not write generated files or apply fixes."
        ),
        "inputSchema": object_schema(
            {
                "project": {
                    "type": "string",
                    "description": "Project root path to inspect, confined to CHECKYOURSELF_SCAN_ROOT (default: the"
                    " MCP server process current directory).",
                },
                "deep": {
                    "type": "boolean",
                    "description": "Run slower validation checks for detected surfaces, such as mutable GitHub Acti"
                    "on references. Defaults to false.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum files to scan before truncating (default 6000). The result reports skip"
                    "ped inputs and incompleteness in scan_limits.",
                },
            }
        ),
        "annotations": read_only_annotations("Scan Project"),
        "outputSchema": {"type": "object", "description": "Scan result using schema checkyourself-scan/1."},
    }


def _tool_coverage_emit() -> dict:
    return {
        "name": "coverage_emit",
        "title": "Emit Coverage Skeleton",
        "description": description(
            "Return the 20-surface CheckYourself coverage skeleton that an agent fills with "
            "manual evidence, missing-evidence notes, "
            "and not-applicable reasons before coverage-backed scoring. In MCP mode this "
            "only returns the skeleton object; it does not create a file."
        ),
        "inputSchema": object_schema(
            {
                "project": {
                    "type": "string",
                    "description": "Optional project label or path to include in the returned coverage skeleton.",
                },
            }
        ),
        "annotations": read_only_annotations("Emit Coverage Skeleton"),
        "outputSchema": {
            "type": "object",
            "description": "Coverage skeleton using schema checkyourself-coverage/1.",
        },
    }


def _tool_coverage_check() -> dict:
    return {
        "name": "coverage_check",
        "title": "Check Coverage",
        "description": description(
            "Validate an inline CheckYourself coverage object for required surfaces, valid "
            "statuses, reviewed evidence, "
            "missing-evidence notes, and not-applicable reasons. Returns errors and "
            "warnings; it does not calculate a score."
        ),
        "inputSchema": object_schema(
            {
                "coverage": {
                    "type": "object",
                    "description": "Coverage object produced by coverage_emit and filled with evidence statuses.",
                },
            },
            ["coverage"],
        ),
        "annotations": read_only_annotations("Check Coverage"),
        "outputSchema": {
            "type": "object",
            "description": "Coverage completeness result using schema checkyourself-coverage-check/1.",
        },
    }


def _tool_receipt_issue() -> dict:
    return {
        "name": "receipt_issue",
        "title": "Issue Verifier Receipt",
        "description": description(
            "Issue one verifier-hashed receipt only for an existing, registered "
            "surface-specific verification artifact under the configured MCP scan root. "
            "The result is returned inline and is not written to disk."
        ),
        "inputSchema": object_schema(
            {
                "reference": {
                    "type": "string",
                    "description": "In-root registered verification artifact path to hash.",
                },
                "surface_id": {"type": "string", "description": "Canonical coverage surface ID."},
                "source_revision": {"type": "string", "description": "Source revision examined."},
                "source_state": {"type": "string", "description": "Source/environment state examined."},
                "command": {"type": "string", "description": "Command recorded at issuance."},
                "claim": {"type": "string", "description": "One claim proved by the receipt."},
                "result": {"type": "string", "description": "Observed result recorded at issuance."},
                "subject_digest": {
                    "type": "string",
                    "description": "Optional content hash assertion for the registered verification artifact.",
                },
            },
            ["reference", "surface_id", "source_revision", "source_state", "command", "claim", "result"],
        ),
        "annotations": read_only_annotations("Issue Verifier Receipt"),
        "outputSchema": {"type": "object", "description": "Verifier receipt using schema checkyourself-receipt/1."},
    }


def _tool_score() -> dict:
    return {
        "name": "score",
        "title": "Score Findings",
        "description": description(
            "Compute a deterministic Production Reality Score from inline findings and optional coverage evidence. "
            "Returns score, raw score, confidence, score mode, severity counts, caps "
            "applied, per-category penalties, "
            "and manual evidence still needed. MCP mode does not write score history."
        ),
        "inputSchema": object_schema(
            {
                "findings": findings_schema("normalize and score"),
                "coverage": {
                    "type": ["object", "null"],
                    "description": "Optional filled coverage object. Provide this for coverage-backed scoring; omit"
                    " for scan-derived or finding-only estimates.",
                },
                "claim": {
                    "type": "string",
                    "description": "Optional accepted completion claim. This records the claim but does not execute"
                    " an independent challenge runner.",
                },
            },
            ["findings"],
        ),
        "annotations": read_only_annotations("Score Findings"),
        "outputSchema": {"type": "object", "description": "Score result using schema checkyourself-score/1."},
    }


def _tool_backlog() -> dict:
    return {
        "name": "backlog",
        "title": "Rank Backlog",
        "description": description(
            "Normalize inline findings and return the complete remediation backlog sorted "
            "by severity, category, and finding ID. "
            "The highest_severity_batch is a deterministic severity slice; safety and "
            "dependency analysis are not performed. "
            "Each item includes fix summary, order rationale, verification, rollback idea, "
            "learning value, and status. "
            "This recommends work only; it does not modify files or mark findings resolved."
        ),
        "inputSchema": object_schema(
            {
                "findings": findings_schema("convert into a remediation backlog"),
            },
            ["findings"],
        ),
        "annotations": read_only_annotations("Rank Backlog"),
        "outputSchema": {"type": "object", "description": "Backlog result using schema checkyourself-backlog/1."},
    }


def _tool_next() -> dict:
    return {
        "name": "next",
        "title": "Next Approval Batch",
        "description": description(
            "Return the next highest-severity unresolved approval batch from inline "
            "findings by reusing the backlog ranking rules. "
            "The batch contains at most the first three unresolved findings at the highest "
            "current severity; safety and dependency analysis are not performed. "
            "This is a planning tool only and does not perform fixes."
        ),
        "inputSchema": object_schema(
            {
                "findings": findings_schema("batch into the next approval group"),
            },
            ["findings"],
        ),
        "annotations": read_only_annotations("Next Approval Batch"),
        "outputSchema": {
            "type": "object",
            "description": "Next-batch result using schema checkyourself-next-batch/1.",
        },
    }


def _tool_diff() -> dict:
    return {
        "name": "diff",
        "title": "Diff Findings",
        "description": description(
            "Compare two inline findings artifacts (scan results, reports, or finding lists) and return added, "
            "resolved, unchanged, status and severity transitions, evidence-level changes, "
            "severity count deltas, and "
            "a regression flag that is true for newly open, reopened, or escalated P0/P1 "
            "findings or increased counts. "
            "Use this to gate changes against a baseline."
        ),
        "inputSchema": object_schema(
            {
                "old": findings_schema("treat as the baseline"),
                "new": findings_schema("treat as the current state"),
            },
            ["old", "new"],
        ),
        "annotations": read_only_annotations("Diff Findings"),
        "outputSchema": {"type": "object", "description": "Diff result using schema checkyourself-diff/1."},
    }


def _tool_validate() -> dict:
    return {
        "name": "validate",
        "title": "Validate Artifact",
        "description": description(
            "Validate an inline JSON artifact against one bundled CheckYourself schema "
            "subset and return validation errors. "
            "Supported kinds include scan, coverage, score, backlog, next, diff, report, "
            "dashboard, dashboard-data, learning-plan, and capabilities."
        ),
        "inputSchema": object_schema(
            {
                "kind": {
                    "type": "string",
                    "enum": _SCHEMA_NAMES,
                    "description": "Bundled schema kind to validate against.",
                },
                "artifact": {
                    "type": "object",
                    "description": "Inline JSON object to validate. MCP mode does not read a file path for this tool.",
                },
            },
            ["kind", "artifact"],
        ),
        "annotations": read_only_annotations("Validate Artifact"),
        "outputSchema": {
            "type": "object",
            "description": "Validation result using schema checkyourself-validation/1.",
        },
    }


def _tool_schema() -> dict:
    return {
        "name": "schema",
        "title": "Get Schema",
        "description": description(
            "Return a bundled CheckYourself JSON schema by name so an agent can inspect "
            "expected fields before producing or validating artifacts. "
            "This reads the repository's schema file and returns it; it does not validate an artifact."
        ),
        "inputSchema": object_schema(
            {
                "name": {
                    "type": "string",
                    "enum": _SCHEMA_NAMES,
                    "description": "Schema name to return.",
                },
            },
            ["name"],
        ),
        "annotations": read_only_annotations("Get Schema"),
        "outputSchema": {"type": "object", "description": "The requested bundled JSON schema."},
    }


def mcp_tools() -> List[dict]:
    """Serve the 11-tool MCP surface; one builder per tool keeps each under the size gate."""
    return [
        _tool_describe(),
        _tool_scan(),
        _tool_coverage_emit(),
        _tool_coverage_check(),
        _tool_receipt_issue(),
        _tool_score(),
        _tool_backlog(),
        _tool_next(),
        _tool_diff(),
        _tool_validate(),
        _tool_schema(),
    ]


def mcp_scan_root() -> Path:
    return Path(os.environ.get("CHECKYOURSELF_SCAN_ROOT") or os.getcwd()).resolve()


def resolve_mcp_scan_path(requested: str) -> Path:
    """Confine MCP-initiated scans to a configured root.

    The MCP server is driven by agents with attacker-influenceable arguments,
    so an absolute path like /etc or ~/.aws must not be scannable unless the
    operator deliberately widened the boundary via CHECKYOURSELF_SCAN_ROOT.
    """
    base = mcp_scan_root()
    candidate = Path(requested) if requested else base
    if not candidate.is_absolute():
        candidate = base / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise CliError(
            f"scan path {resolved} is outside the allowed scan root {base}. "
            "Set CHECKYOURSELF_SCAN_ROOT to widen the boundary deliberately.",
            code=2,
        )
    if not resolved.is_dir():
        raise CliError(f"project root not found: {resolved}", code=2)
    return resolved


def call_mcp_tool(name: str, arguments: dict) -> dict:
    if name == "describe":
        return describe_capabilities()
    if name == "scan":
        project = resolve_mcp_scan_path(str(arguments.get("project") or ""))
        max_files = int(arguments.get("max_files") or DEFAULT_MAX_FILES)
        return scan(project, deep=bool(arguments.get("deep")), max_files=max_files)
    if name == "coverage_emit":
        return coverage_emit(str(arguments.get("project") or ""))
    if name == "coverage_check":
        return coverage_check(arguments.get("coverage") or {}, mcp_scan_root())
    if name == "receipt_issue":
        return issue_receipt(
            str(arguments.get("reference") or ""),
            mcp_scan_root(),
            surface_id=str(arguments.get("surface_id") or ""),
            source_revision=str(arguments.get("source_revision") or ""),
            source_state=str(arguments.get("source_state") or ""),
            command=str(arguments.get("command") or ""),
            claim=str(arguments.get("claim") or ""),
            result=str(arguments.get("result") or ""),
            subject_digest=arguments.get("subject_digest"),
        )
    if name == "score":
        findings = arguments.get("findings") or {}
        if "coverage" in arguments:
            return score_from_inputs(
                findings,
                arguments["coverage"],
                evidence_root=mcp_scan_root(),
                claim=arguments.get("claim"),
            )
        return score_from_inputs(findings, claim=arguments.get("claim"))
    if name == "backlog":
        return backlog_from_findings(arguments.get("findings") or {})
    if name == "next":
        return next_from_findings(arguments.get("findings") or {})
    if name == "diff":
        return diff_findings(arguments.get("old") or {}, arguments.get("new") or {})
    if name == "validate":
        return validate_artifact(str(arguments.get("kind")), arguments.get("artifact"))
    if name == "schema":
        return load_schema(str(arguments.get("name")))
    raise CliError(f"unknown MCP tool: {name}")


def mcp_success(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def mcp_error(request_id: Any, code: int, message: str, data: Optional[dict] = None) -> dict:
    error: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def mcp_tool_result(data: dict, is_error: bool = False) -> dict:
    text = json.dumps(data, indent=2, allow_nan=False)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": data,
        "isError": is_error,
    }


def handle_mcp_message(message: dict) -> Optional[dict]:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if method == "initialize":
        requested = str(params.get("protocolVersion") or MCP_PROTOCOL_VERSION)
        protocol = requested if requested in SUPPORTED_MCP_PROTOCOLS else MCP_PROTOCOL_VERSION
        return mcp_success(
            request_id,
            {
                "protocolVersion": protocol,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "checkyourself",
                    "title": "CheckYourself",
                    "version": read_manifest_version(),
                    "description": "Local-first production-readiness diagnostic tools.",
                },
                "instructions": (
                    "Use CheckYourself read-only first. Scan, fill coverage with evidence, "
                    "score, rank backlog, ask before fixes. For public repository claims, "
                    "name exact owner namespaces, repository counts, verification timestamps, "
                    "live evidence surfaces, and fork exclusions before saying all or 100%."
                ),
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return mcp_success(request_id, {})
    if method == "tools/list":
        return mcp_success(request_id, {"tools": mcp_tools()})
    if method == "tools/call":
        name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return mcp_error(
                request_id,
                -32602,
                f'tools/call arguments must be an object. Retry: tools/call {{"name": {name!r}, "arguments": {{}}}}',
            )
        tools_by_name = {tool["name"]: tool for tool in mcp_tools()}
        if name not in tools_by_name:
            return mcp_error(
                request_id,
                -32602,
                f"unknown tool: {name}. Known tools: {', '.join(sorted(tools_by_name))}. "
                "Retry: tools/list {} to enumerate names, then tools/call with one of them",
            )
        input_schema = tools_by_name[name].get("inputSchema") or {}
        allowed = set((input_schema.get("properties") or {}).keys())
        unknown = sorted(set(arguments) - allowed)
        if unknown:
            # Silently ignoring a misspelled argument (e.g. `path` instead of
            # `project`) made the tool scan the wrong directory and report
            # success. Reject unknown keys loudly instead.
            return mcp_error(
                request_id,
                -32602,
                f"unknown argument(s) for {name}: {', '.join(unknown)}. "
                f"Allowed: {', '.join(sorted(allowed)) or 'none'}. {retry_message(name)}",
            )
        missing = sorted(set(input_schema.get("required") or []) - set(arguments))
        if missing:
            return mcp_error(
                request_id,
                -32602,
                f"missing required argument(s) for {name}: {', '.join(missing)}. {retry_message(name)}",
            )
        type_errors = validate_json_schema(arguments, input_schema)
        if type_errors:
            return mcp_error(
                request_id,
                -32602,
                f"invalid argument value(s) for {name}: {'; '.join(type_errors)}. {retry_message(name)}",
            )
        try:
            data = call_mcp_tool(name, arguments)
            return mcp_success(request_id, mcp_tool_result(data))
        except CliError as exc:
            return mcp_success(
                request_id,
                mcp_tool_result(
                    {"error": str(exc), "code": exc.code, "retry": retry_message(name)},
                    is_error=True,
                ),
            )
        except Exception as exc:  # pragma: no cover - defensive protocol boundary.
            return mcp_success(
                request_id,
                mcp_tool_result(
                    {"error": str(exc), "retry": retry_message(name)},
                    is_error=True,
                ),
            )
    if request_id is None:
        return None
    return mcp_error(
        request_id,
        -32601,
        f"method not found: {method}. Retry: initialize, then tools/list, then tools/call; CLI: {CLI_ENTRY} --help",
    )


def run_mcp_server() -> int:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = strict_json_loads(raw)
        except (ValueError, UnicodeError) as exc:
            response = mcp_error(
                None,
                -32700,
                f"parse error: {exc}. Retry: send one JSON-RPC object per line, e.g. "
                '\'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\'',
            )
        else:
            if not isinstance(message, dict):
                # JSON-RPC batch arrays would otherwise crash on .get().
                sys.stdout.write(
                    json.dumps(
                        mcp_error(
                            None,
                            -32600,
                            "batch requests are not supported; send one JSON-RPC object per line. "
                            "Retry: split the batch into one object per line, each like "
                            '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{}}',
                        ),
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                    + "\n"
                )
                sys.stdout.flush()
                continue
            try:
                response = handle_mcp_message(message)
            except Exception as exc:  # pragma: no cover - defensive protocol boundary.
                traceback.print_exc(file=sys.stderr)
                response = mcp_error(message.get("id"), -32603, str(exc))
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":"), allow_nan=False) + "\n")
            sys.stdout.flush()
    return 0
