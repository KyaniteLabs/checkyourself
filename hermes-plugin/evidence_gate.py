"""Completion policy over the existing CheckYourself stdio MCP engine."""


def mcp_call(name, arguments, root):
    import json
    import subprocess
    import sys
    from pathlib import Path
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "hermes-evidence-gate", "version": "0.1.0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": arguments}},
    ]
    proc = subprocess.Popen(
        [sys.executable, "-I", "-B", str(Path(__file__).parent / "tools/checkyourself.py"), "mcp"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=root, start_new_session=True,
        env={"CHECKYOURSELF_SCAN_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    try:
        stdout, _ = proc.communicate("".join(json.dumps(m, allow_nan=False) + "\n" for m in messages), timeout=20)
    except BaseException:
        import os
        import signal
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise
    if proc.returncode:
        raise ValueError("MCP process failed")
    replies = [json.loads(line) for line in stdout.splitlines()]
    reply = next(r for r in replies if r.get("id") == 2)
    if "error" in reply or reply.get("result", {}).get("isError"):
        raise ValueError("MCP rejected evidence; check artifact schema and root")
    return reply["result"]["structuredContent"]


def evidence_score(args):
    import json
    import os
    from pathlib import Path
    if not isinstance(args, dict) or set(args) != {"findings", "coverage", "claim"}:
        raise ValueError("evidence requires exactly findings, coverage and claim")
    if not isinstance(args["claim"], str) or not args["claim"].strip():
        raise ValueError("claim must be nonempty")
    if os.environ.get("CHECKYOURSELF_ALLOW_CHALLENGES") != "1":
        raise ValueError("operator must opt in: scoring re-executes project challenge commands")
    configured = os.environ.get("CHECKYOURSELF_SCAN_ROOT")
    if not configured:
        raise ValueError("operator must set CHECKYOURSELF_SCAN_ROOT")
    root = Path(configured).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("evidence root must be a directory")
    payload = {"claim": args["claim"]}
    for key in ("findings", "coverage"):
        if not isinstance(args[key], str):
            raise ValueError("evidence paths must be strings")
        path = (root / args[key]).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("evidence file must stay under configured root")
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("evidence file exceeds 1 MiB")
        payload[key] = json.loads(path.read_text(encoding="utf-8"))
    result = mcp_call("score", payload, root)
    tests = next(c for c in result["per_category"] if c["id"] == "C5")
    allowed = (result.get("score_mode") == "coverage-backed"
               and tests["coverage_status"] == "Pass"
               and tests["awarded"] == tests["weight"]
               and bool(tests["verified_evidence"])
               and not tests["missing_evidence"]
               and not result.get("counts", {}).get("P0")
               and not result.get("counts", {}).get("P1"))
    return {"allowed": allowed, "policy": "S11-executed-test-evidence/full-C5-credit/no-P0-P1", "score": result}


def tool_handler(args, **kwargs):
    import json
    try:
        return json.dumps(evidence_score(args), allow_nan=False)
    except Exception as exc:
        return json.dumps({"allowed": False, "error": type(exc).__name__, "message": "Evidence unavailable or invalid; completion stays blocked."})


def completion_gate(tool_name=None, args=None, **kwargs):
    if tool_name != "kanban_complete":
        return None
    try:
        evidence = ((args or {}).get("metadata") or {}).get("checkyourself")
        verdict = evidence_score(evidence)
        if verdict["allowed"]:
            return None
        message = "Completion blocked: evidence score %s; add verified coverage receipts and retry." % verdict["score"]["score"]
    except Exception:
        message = "Completion blocked: missing/invalid evidence. Supply metadata.checkyourself {findings, coverage, claim} under CHECKYOURSELF_SCAN_ROOT."
    return {"action": "block", "message": message}


def invoke(raw_args=""):
    import json
    try:
        return tool_handler(json.loads(raw_args))
    except Exception:
        return '{"allowed": false, "error": "expected JSON evidence arguments"}'


def setup_cli(parser):
    parser.add_argument("text", help="JSON with findings, coverage paths and claim")


def cli_handler(args):
    print(invoke(args.text))


def register(ctx):
    ctx.register_tool(
        name="checkyourself_evidence_score", toolset="checkyourself",
        schema={"name": "checkyourself_evidence_score", "description": "Execute configured local verification via MCP and score evidence. Challenge commands may write files/use network; explicit operator opt-in required.", "parameters": {"type": "object", "properties": {"findings": {"type": "string"}, "coverage": {"type": "string"}, "claim": {"type": "string"}}, "required": ["findings", "coverage", "claim"], "additionalProperties": False}},
        handler=tool_handler,
    )
    ctx.register_hook("pre_tool_call", completion_gate)
    ctx.register_command("evidence-gate", invoke, description="Score completion evidence", args_hint="JSON")
    ctx.register_cli_command("evidence-gate", "Score completion evidence", setup_cli, cli_handler)
