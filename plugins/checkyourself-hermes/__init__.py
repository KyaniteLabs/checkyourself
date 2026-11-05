"""CheckYourself — native Hermes plugin (Evidence Gate).

Surfaces:
  pre_llm_call   -> when the user asserts completion, inject an Evidence Gate brief
  post_tool_call -> record checkyourself_* score / finding counts in a profile-local ledger
  /checkyourself -> describe | scan | score | backlog | next | coverage | status | help
  tools          -> checkyourself_scan / _score / _backlog / _next / _describe / _coverage
  skill          -> skills/checkyourself/SKILL.md

Child processes get a scrubbed env; scan artifacts and the score ledger live under
<HERMES_HOME>/plugin-data/checkyourself/ via plugins.plugin_storage. Only public ctx.* APIs.
challenge / init / mcp / receipt / diff are intentionally NOT exposed in v0.1.0.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PLUGIN_NAME = "checkyourself"
PINNED_PKG = "@puenteworks/checkyourself@1.7.0"
DEFAULTS: Dict[str, Any] = {
    "checkyourself_command": f"npx -y {PINNED_PKG}",
    "default_project": ".",
    "inject_on_claim": True,
    "allow_project_slash_on_gateway": False,
    "max_files": 6000,
    "timeout_seconds": 180,
}
LEDGER_MAX = 200
MAX_OUT = 20000

# Completion / launch claims that should trip the Evidence Gate brief.
_CLAIM_RE = re.compile(
    r"(?:"
    r"\b(?:done|finished|complete(?:d)?|ship(?:ped|ping)?|launch(?:ed|ing)?|"
    r"ready to (?:ship|launch|merge|deploy|go)|production[- ]?ready|"
    r"tests? pass(?:ed|ing)?|all (?:green|good)|it works|lgtm|merge it|"
    r"we're good|good to go|claims? (?:of )?(?:completion|done)|"
    r"evidence gate|check ?yourself|score (?:this|the) (?:app|project|repo))\b"
    r")",
    re.IGNORECASE,
)

_ctx = None


# --- config / storage -------------------------------------------------------

def _cfg(key: str) -> Any:
    try:
        val = _ctx.get_config(key, None) if _ctx is not None else None
    except Exception:
        val = None
    return DEFAULTS[key] if val is None else val


def _data_dir() -> Path:
    try:
        from plugins.plugin_storage import plugin_data_dir

        return plugin_data_dir(PLUGIN_NAME)
    except Exception:
        home = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
        p = Path(home) / "plugin-data" / PLUGIN_NAME
        p.mkdir(parents=True, exist_ok=True)
        return p


def _ledger_path() -> Path:
    return _data_dir() / "score_ledger.json"


def _last_scan_path() -> Path:
    return _data_dir() / "last_scan.json"


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("checkyourself: failed reading %s", path, exc_info=True)
    return default


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _on_gateway() -> bool:
    plat = (os.environ.get("HERMES_PLATFORM") or os.environ.get("HERMES_SESSION_PLATFORM") or "").lower()
    return bool(plat) and plat not in {"cli", "tui", "desktop", "local", "acp"}


# --- child process ----------------------------------------------------------

_ENV_ALLOW = (
    "PATH", "HOME", "USER", "LANG", "LC_ALL", "TMPDIR", "TMP", "TEMP",
    "NODE_OPTIONS", "npm_config_cache", "NPM_CONFIG_CACHE", "XDG_CACHE_HOME",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy",
    "CHECKYOURSELF_PYTHON",
)


def _scrubbed_env() -> Dict[str, str]:
    """Minimal env for the CheckYourself child — never hand it full os.environ."""
    env = {k: os.environ[k] for k in _ENV_ALLOW if os.environ.get(k)}
    env["NO_COLOR"] = "1"
    env["CHECKYOURSELF_PLUGIN_DATA"] = str(_data_dir())
    # No API keys needed — CLI is local-first and prints no secrets. Do not copy
    # anything from Hermes secret scope into the child.
    return env


def run_checkyourself(args: List[str]) -> Dict[str, Any]:
    cmd = shlex.split(str(_cfg("checkyourself_command"))) + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=int(_cfg("timeout_seconds")),
            env=_scrubbed_env(),
            cwd=str(_data_dir()),
        )
    except FileNotFoundError as exc:
        return {"ok": False, "error": f"checkyourself not runnable (need Node >=18 + npx + Python 3): {exc}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "checkyourself timed out"}
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0 and not out:
        return {"ok": False, "exit": proc.returncode, "error": err[-800:] or f"exit {proc.returncode}"}
    data: Any = None
    for opener in ("{", "["):
        i = out.find(opener)
        if i >= 0:
            try:
                data, _end = json.JSONDecoder().raw_decode(out[i:])
                break
            except json.JSONDecodeError:
                continue
    res: Dict[str, Any] = {"ok": proc.returncode == 0, "exit": proc.returncode}
    if data is not None:
        res["data"] = data
    else:
        res["text"] = out[:8000]
    if err:
        res["stderr"] = err[-400:]
    return res


# --- project path helper ----------------------------------------------------

def _resolve_project(project: Optional[str] = None) -> Path:
    raw = str(project if project not in (None, "") else _cfg("default_project")).strip() or "."
    p = Path(raw).expanduser()
    if not p.is_absolute():
        # Prefer cwd when default "."; otherwise resolve relative to cwd.
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    if not p.exists():
        raise ValueError(f"project path does not exist: {p}")
    if not p.is_dir():
        raise ValueError(f"project path is not a directory: {p}")
    return p


def _findings_path(explicit: Optional[str] = None) -> Path:
    if explicit:
        p = Path(str(explicit)).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
        if not p.is_file():
            raise ValueError(f"findings file not found: {p}")
        return p
    last = _last_scan_path()
    if not last.is_file():
        raise ValueError(
            "no findings file: run checkyourself_scan first, or pass findings_path to an existing scan JSON"
        )
    return last


# --- operations -------------------------------------------------------------

def describe() -> Dict[str, Any]:
    return run_checkyourself(["describe", "--format", "json"])


def scan(project: Optional[str] = None, deep: bool = False, max_files: Optional[int] = None) -> Dict[str, Any]:
    root = _resolve_project(project)
    mf = int(max_files if max_files is not None else _cfg("max_files"))
    args = [
        "scan",
        str(root),
        "--no-write",
        "--format", "json",
        "--max-files", str(mf),
    ]
    if deep:
        args.append("--deep")
    res = run_checkyourself(args)
    if res.get("ok") and isinstance(res.get("data"), dict):
        _save_json(_last_scan_path(), res["data"])
        # Also stash a sidecar pointer for humans
        _save_json(
            _data_dir() / "last_scan_meta.json",
            {"ts": int(time.time()), "project": str(root), "deep": bool(deep), "max_files": mf},
        )
    return res


def score(findings_path: Optional[str] = None, claim: Optional[str] = None) -> Dict[str, Any]:
    path = _findings_path(findings_path)
    args = ["score", "--findings", str(path), "--format", "json", "--no-history"]
    if claim:
        args += ["--claim", str(claim)[:500]]
    return run_checkyourself(args)


def backlog(findings_path: Optional[str] = None) -> Dict[str, Any]:
    path = _findings_path(findings_path)
    return run_checkyourself(["backlog", "--findings", str(path), "--format", "json"])


def next_batch(findings_path: Optional[str] = None) -> Dict[str, Any]:
    path = _findings_path(findings_path)
    return run_checkyourself(["next", "--findings", str(path), "--format", "json"])


def coverage_emit(project_label: Optional[str] = None) -> Dict[str, Any]:
    args = ["coverage", "--emit", "--format", "json"]
    if project_label:
        args += ["--project", str(project_label)[:200]]
    return run_checkyourself(args)


# --- hooks ------------------------------------------------------------------

_BRIEF = (
    "[CheckYourself Evidence Gate] This message looks like a completion / launch claim. "
    "Do not accept 'done', 'tests pass', or 'ready to ship' on assertion alone. "
    "1) Extract the concrete claims. 2) Re-derive each with `checkyourself_scan` on the "
    "project (read-only, --no-write). 3) Run `checkyourself_score` (and backlog/next) on "
    "the scan JSON. 4) Label each claim CONFIRMED / REFUTED / UNVERIFIABLE with evidence. "
    "Stay read-only unless the user approves a named fix. The score is scoped evidence, "
    "not a production-safety certification."
)


def _on_pre_llm(user_message: str = "", **_: Any) -> Optional[Dict[str, str]]:
    try:
        if _cfg("inject_on_claim") and user_message and _CLAIM_RE.search(user_message):
            return {"context": _BRIEF}
    except Exception:
        logger.debug("checkyourself: pre_llm_call failed", exc_info=True)
    return None


def _on_post_tool(tool_name: str = "", args: Optional[Dict[str, Any]] = None, result: Any = None,
                  **_: Any) -> None:
    """Score ledger: remember scan/score summaries (no file contents stored)."""
    try:
        if not str(tool_name or "").startswith("checkyourself_"):
            return None
        payload = result
        if isinstance(result, str):
            try:
                payload = json.loads(result)
            except Exception:
                payload = {"raw": result[:200]}
        entry: Dict[str, Any] = {
            "ts": int(time.time()),
            "tool": tool_name,
            "ok": isinstance(payload, dict) and bool(payload.get("ok")),
        }
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            if tool_name == "checkyourself_scan":
                entry["project"] = data.get("project")
                entry["files_scanned"] = data.get("files_scanned")
                findings = data.get("findings") or data.get("summary") or {}
                if isinstance(findings, dict):
                    entry["finding_counts"] = {
                        k: findings.get(k)
                        for k in ("p0", "p1", "p2", "total", "P0", "P1", "P2", "count")
                        if k in findings
                    } or None
            if tool_name == "checkyourself_score":
                entry["score"] = data.get("score", data.get("production_reality_score"))
                entry["band"] = data.get("band", data.get("tier"))
        ledger = _load_json(_ledger_path(), [])
        if not isinstance(ledger, list):
            ledger = []
        ledger.append(entry)
        _save_json(_ledger_path(), ledger[-LEDGER_MAX:])
    except Exception:
        logger.debug("checkyourself: post_tool_call failed", exc_info=True)
    return None


# --- tools ------------------------------------------------------------------

SCAN_SCHEMA = {
    "name": "checkyourself_scan",
    "description": (
        "Read-only CheckYourself scan of a project: stack signals + deterministic local findings. "
        "Writes no files into the project (--no-write); saves JSON under HERMES plugin-data for score/backlog."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "project": {"type": "string", "description": "Project root to scan (default: plugin default_project)."},
            "deep": {"type": "boolean", "description": "Slower validation checks (mutable CI actions, dep coverage)."},
            "max_files": {"type": "integer", "description": "Cap files scanned before truncation."},
        },
        "required": [],
    },
}
SCORE_SCHEMA = {
    "name": "checkyourself_score",
    "description": (
        "Compute the deterministic Production Reality Score (0-100) from a CheckYourself findings/scan JSON. "
        "Defaults to the last scan saved by checkyourself_scan. Score is evidence, not a safety certification."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "findings_path": {"type": "string", "description": "Path to scan/findings JSON; omit to use last scan."},
            "claim": {"type": "string", "description": "Optional completion claim to record alongside the score."},
        },
        "required": [],
    },
}
BACKLOG_SCHEMA = {
    "name": "checkyourself_backlog",
    "description": "Rank the complete remediation backlog from a CheckYourself findings/scan JSON.",
    "parameters": {
        "type": "object",
        "properties": {
            "findings_path": {"type": "string"},
        },
        "required": [],
    },
}
NEXT_SCHEMA = {
    "name": "checkyourself_next",
    "description": (
        "Return the next highest-severity unresolved approval batch from findings. "
        "Does not perform safety analysis or apply fixes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "findings_path": {"type": "string"},
        },
        "required": [],
    },
}
DESCRIBE_SCHEMA = {
    "name": "checkyourself_describe",
    "description": "Emit the CheckYourself CLI capability manifest (offline, no project needed).",
    "parameters": {"type": "object", "properties": {}},
}
COVERAGE_SCHEMA = {
    "name": "checkyourself_coverage",
    "description": "Emit the 20-surface coverage skeleton JSON (offline).",
    "parameters": {
        "type": "object",
        "properties": {
            "project_label": {"type": "string", "description": "Optional label stored on the skeleton."},
        },
        "required": [],
    },
}


def _wrap(fn):
    def handler(args: Optional[Dict[str, Any]] = None, **_: Any) -> str:
        try:
            out = fn(args or {})
        except ValueError as exc:
            out = {"ok": False, "error": str(exc)}
        except Exception as exc:  # never crash the agent loop
            logger.debug("checkyourself tool failed", exc_info=True)
            out = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        return json.dumps(out, ensure_ascii=False)[:MAX_OUT]
    return handler


_tool_scan = _wrap(lambda a: scan(a.get("project"), bool(a.get("deep")), a.get("max_files")))
_tool_score = _wrap(lambda a: score(a.get("findings_path"), a.get("claim")))
_tool_backlog = _wrap(lambda a: backlog(a.get("findings_path")))
_tool_next = _wrap(lambda a: next_batch(a.get("findings_path")))
_tool_describe = _wrap(lambda a: describe())
_tool_coverage = _wrap(lambda a: coverage_emit(a.get("project_label")))


# --- slash ------------------------------------------------------------------

_SAFE_SLASH = {"describe", "scan", "score", "backlog", "next", "coverage", "status", "help"}
_PROJECT_SLASH = {"scan", "score", "backlog", "next", "coverage"}
_HELP = (
    "Usage:\n"
    "  /checkyourself describe                         Capability manifest\n"
    "  /checkyourself scan [project] [--deep]          Read-only scan (saves findings in plugin-data)\n"
    "  /checkyourself score [findings.json]            Production Reality Score\n"
    "  /checkyourself backlog [findings.json]          Ranked remediation backlog\n"
    "  /checkyourself next [findings.json]             Next approval batch\n"
    "  /checkyourself coverage [label]                 20-surface coverage skeleton\n"
    "  /checkyourself status                           Recent score-ledger entries\n"
    "Not exposed via slash: challenge, init, mcp, receipt, diff (use the CheckYourself CLI).\n"
    "On gateway platforms, scan/score/backlog/next/coverage are refused unless "
    "allow_project_slash_on_gateway: true."
)


def _fmt(res: Dict[str, Any]) -> str:
    if not res.get("ok") and "data" not in res:
        return f"CheckYourself failed: {res.get('error') or res.get('stderr') or res}"
    if "data" in res:
        return json.dumps(res["data"], indent=2, ensure_ascii=False)[:3500]
    return str(res.get("text", ""))[:3500]


def _slash(raw_args: str) -> str:
    raw = (raw_args or "").strip()
    if not raw:
        return _HELP
    parts = shlex.split(raw)
    cmd = parts[0].lower() if parts else "help"
    rest = parts[1:]
    if cmd in {"help", "-h", "--help"}:
        return _HELP
    if cmd not in _SAFE_SLASH:
        return (
            f"Unknown or blocked subcommand `{cmd}`. "
            f"Allowed: {', '.join(sorted(_SAFE_SLASH))}. "
            "challenge/init/mcp/receipt/diff stay on the CLI."
        )
    if cmd in _PROJECT_SLASH and _on_gateway() and not _cfg("allow_project_slash_on_gateway"):
        return (
            f"/checkyourself {cmd} is disabled on gateway platforms (filesystem access). "
            "Ask the agent to use the tools instead, or set allow_project_slash_on_gateway: true."
        )
    try:
        if cmd == "describe":
            return _fmt(describe())
        if cmd == "status":
            return json.dumps(_load_json(_ledger_path(), [])[-10:], indent=2)
        if cmd == "coverage":
            label = rest[0] if rest else None
            return _fmt(coverage_emit(label))
        if cmd == "scan":
            deep = "--deep" in rest
            project = next((a for a in rest if a != "--deep"), None)
            return _fmt(scan(project, deep=deep))
        if cmd == "score":
            return _fmt(score(rest[0] if rest else None))
        if cmd == "backlog":
            return _fmt(backlog(rest[0] if rest else None))
        if cmd == "next":
            return _fmt(next_batch(rest[0] if rest else None))
    except ValueError as exc:
        return f"{exc}\n\n{_HELP}"
    except Exception as exc:
        logger.debug("checkyourself slash failed", exc_info=True)
        return f"CheckYourself error: {type(exc).__name__}: {exc}"
    return _HELP


# --- register ---------------------------------------------------------------

def register(ctx) -> None:
    global _ctx
    _ctx = ctx
    ctx.register_hook("pre_llm_call", _on_pre_llm)
    ctx.register_hook("post_tool_call", _on_post_tool)
    ctx.register_command(
        "checkyourself",
        handler=_slash,
        description="CheckYourself Evidence Gate (describe/scan/score/backlog/next/coverage/status).",
        args_hint="describe | scan [path] [--deep] | score [findings.json] | backlog | next | coverage | status",
    )
    for schema, handler, emoji in (
        (SCAN_SCHEMA, _tool_scan, "🔎"),
        (SCORE_SCHEMA, _tool_score, "📊"),
        (BACKLOG_SCHEMA, _tool_backlog, "📋"),
        (NEXT_SCHEMA, _tool_next, "➡️"),
        (DESCRIBE_SCHEMA, _tool_describe, "ℹ️"),
        (COVERAGE_SCHEMA, _tool_coverage, "🧩"),
    ):
        ctx.register_tool(
            name=schema["name"],
            toolset="checkyourself",
            schema=schema,
            handler=handler,
            description=schema["description"],
            emoji=emoji,
        )
    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                try:
                    ctx.register_skill(child.name, skill_md)
                except Exception:
                    logger.debug("checkyourself: register_skill failed for %s", child.name, exc_info=True)
