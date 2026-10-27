"""User-facing error type and retry re-invocation recipes for every error path.

Every operator-visible failure — CLI ``CliError``, argparse usage errors, and
MCP JSON-RPC errors — must name a concrete re-invocation, mirroring kinocut's
errors.py ``retry_message`` pattern: a stable key maps to a runnable command on
each surface (MCP ``tools/call`` and the CLI entry) instead of a bare apology.
"""

from __future__ import annotations


class CliError(Exception):
    """User-facing CLI error with a stable exit code."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


CLI_ENTRY = "python3 tools/checkyourself.py"

# Concrete MCP tools/call re-invocations for the 11-tool surface. Placeholders
# name what the caller must supply; nothing here is invented at runtime.
MCP_TOOL_CALLS: dict[str, str] = {
    "describe": '{"name":"describe","arguments":{}}',
    "scan": '{"name":"scan","arguments":{"project":"/abs/project/root"}}',
    "coverage_emit": '{"name":"coverage_emit","arguments":{"project":"optional project label"}}',
    "coverage_check": '{"name":"coverage_check","arguments":{"coverage":{<filled coverage object>}}}',
    "receipt_issue": (
        '{"name":"receipt_issue","arguments":{"reference":"coverage/verification/S11/record.json",'
        '"surface_id":"S11","source_revision":"<revision>","source_state":"<state>",'
        '"command":"<command>","claim":"<claim>","result":"<result>"}}'
    ),
    "score": (
        '{"name":"score","arguments":{"findings":{<findings or scan object>},'
        '"coverage":{<optional filled coverage object>}}}'
    ),
    "backlog": '{"name":"backlog","arguments":{"findings":{<findings or scan object>}}}',
    "next": '{"name":"next","arguments":{"findings":{<findings or scan object>}}}',
    "diff": '{"name":"diff","arguments":{"old":{<baseline findings>},"new":{<current findings>}}}',
    "validate": '{"name":"validate","arguments":{"kind":"scan","artifact":{<inline artifact>}}}',
    "schema": '{"name":"schema","arguments":{"name":"scan"}}',
}

# Concrete CLI re-invocations, verb by verb, for the same surface.
CLI_INVOCATIONS: dict[str, str] = {
    "describe": f"{CLI_ENTRY} describe --format json",
    "scan": f"{CLI_ENTRY} scan /abs/project/root --format json",
    "diagnostic": f"{CLI_ENTRY} diagnostic /abs/project/root --format json",
    "coverage": f"{CLI_ENTRY} coverage --emit --format json  # or --check CHECKYOURSELF_COVERAGE.generated.json",
    "challenge": f"{CLI_ENTRY} challenge /abs/project/root --format json",
    "receipt": (
        f"{CLI_ENTRY} receipt --reference coverage/verification/S11/record.json --surface-id S11 "
        "--source-revision <rev> --source-state <state> --command <cmd> --claim <claim> --result <result>"
    ),
    "score": f"{CLI_ENTRY} score --findings findings.json --format json  # add --coverage coverage.json",
    "backlog": f"{CLI_ENTRY} backlog --findings findings.json --format json",
    "next": f"{CLI_ENTRY} next --findings findings.json --format json",
    "diff": f"{CLI_ENTRY} diff --old baseline.json --new current.json --format json",
    "validate": f"{CLI_ENTRY} validate --kind scan scan.json --format json",
    "schema": f"{CLI_ENTRY} schema scan",
    "init": f"{CLI_ENTRY} init /abs/project/root",
    "mcp": f"{CLI_ENTRY} mcp  # stdio JSON-RPC: initialize, then tools/list, then tools/call",
}

_DEFAULT_CLI_RETRY = f"{CLI_ENTRY} scan . --format json  # or {CLI_ENTRY} --help to list commands"
_MCP_ENUMERATE = "MCP: tools/list {} to enumerate the 11 tool names"


def mcp_reinvocation(tool: str) -> str:
    """Concrete MCP re-invocation for a tool name (or how to enumerate tools)."""
    call = MCP_TOOL_CALLS.get(tool)
    return f"MCP: tools/call {call}" if call else _MCP_ENUMERATE


def cli_reinvocation(verb: str) -> str:
    """Concrete CLI re-invocation for a subcommand (or the safe default)."""
    return CLI_INVOCATIONS.get(verb, _DEFAULT_CLI_RETRY)


def retry_message(verb: str) -> str:
    """One concrete retry string covering both surfaces for a verb or tool name.

    This is the single source of every retry hint the CLI and MCP server append
    to user-facing errors: pass the failing verb (CLI subcommand or MCP tool
    name) and callers get a runnable command for each surface.
    """
    mcp = f"MCP: tools/call {MCP_TOOL_CALLS[verb]}" if verb in MCP_TOOL_CALLS else _MCP_ENUMERATE
    return f"Retry — {mcp} · {cli_reinvocation(verb)}"


def cli_retry_for(raw_command: str) -> str:
    """Retry hint for the CLI main() error handler, keyed by the raw argv head."""
    verb = raw_command if raw_command in CLI_INVOCATIONS else ""
    return f"Retry — {cli_reinvocation(verb)}"
