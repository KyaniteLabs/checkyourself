"""CheckYourself — native Hermes plugin (Evidence Gate).

Surfaces:
  pre_llm_call   -> when the user asserts completion, inject an Evidence Gate brief
  pre_tool_call  -> block completion tools unless the CheckYourself score passes the gate
  post_tool_call -> record checkyourself_* score / finding counts in a profile-local ledger
  /checkyourself -> describe | scan | score | backlog | next | coverage | status | help
  tools          -> checkyourself_scan / _score / _backlog / _next / _describe / _coverage
  skill          -> skills/checkyourself/SKILL.md

Child processes get a scrubbed env; scan receipts and the score ledger live under
<HERMES_HOME>/plugin-data/checkyourself/ via plugins.plugin_storage. Only public ctx.* APIs.
challenge / init / mcp / receipt / diff are intentionally NOT exposed in v0.1.0.
"""

from __future__ import annotations

import contextlib
import contextvars
import fcntl
import json
import logging
import os
import re
import shlex
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    # Comma-separated tool names. The score gate blocks these unless the
    # completion-evidence score is numeric and has no open P0 or P1.
    "completion_tools": "kanban_complete",
}
LEDGER_MAX = 200
MAX_OUT = 20000
SLASH_MAX = 3500
_LOCAL_PLATFORMS = frozenset({"cli", "tui", "desktop", "local", "acp", ""})

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
# Per-call session override set by tool handlers (session id from handler kwargs).
# ContextVar (token/reset), never a process global: overlapping handlers on other
# threads / tasks must not observe or clobber each other's session id.
_CALL_SESSION: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "checkyourself_call_session", default=None
)
# Sessions whose implicit pointer could not be invalidated. Scoring stays
# fail-closed for that identity until a later scan commits a new pointer.
_IMPLICIT_BLOCK_LOCK = threading.Lock()
_IMPLICIT_BLOCKED: set[str] = set()
_NO_IDENTITY = (
    "no trustworthy caller identity for an implicit receipt; "
    "refusing a shared nosession pointer"
)
# Seconds between SIGTERM and SIGKILL of the child's process group on timeout.
_KILL_GRACE = 1.0
# Keys that mark a plugin-written receipt envelope (anything else is passed raw to the CLI).
_RECEIPT_KEYS = frozenset({"receipt_id", "valid", "data"})


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


def _receipts_dir() -> Path:
    p = _data_dir() / "receipts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _implicit_dir() -> Path:
    p = _data_dir() / "implicit"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_key(raw: str) -> str:
    key = re.sub(r"[^A-Za-z0-9._-]+", "_", (raw or "").strip()) or "nosession"
    return key[:96]


def _host_session_vars() -> Optional[Dict[str, str]]:
    """Read Hermes session vars once.

    None means the native helper is not importable (CLI / tests outside Hermes).
    A dict means ``get_session_env`` already applied its own rules, including an
    authoritative empty string. Callers must not read ``os.environ`` again.
    """
    try:
        from gateway.session_context import get_session_env
    except Exception:
        return None
    out: Dict[str, str] = {}
    for name in ("HERMES_SESSION_ID", "HERMES_SESSION_KEY"):
        try:
            out[name] = str(get_session_env(name, "") or "").strip()
        except Exception:
            out[name] = ""
    return out


def _resolve_identity() -> Tuple[str, str]:
    """Return ``(identity, source)``.

    Source is ``override``, ``session_id``, ``session_key``, ``local``, or ``none``.
    A gateway slash handler often has a session key and an authoritative empty
    session id (no session row yet). The key is namespaced so it cannot collide
    with a durable session id. ``local`` is only the single-operator bucket used
    when Hermes itself is not installed. ``none`` fail-closes implicit receipts.
    """
    override = _CALL_SESSION.get()
    if override:
        return str(override).strip(), "override"
    host = _host_session_vars()
    if host is None:
        sid = (os.environ.get("HERMES_SESSION_ID") or "").strip()
        if sid:
            return sid, "session_id"
        key = (os.environ.get("HERMES_SESSION_KEY") or "").strip()
        if key:
            return "key:" + key, "session_key"
        return "local", "local"
    sid = host.get("HERMES_SESSION_ID") or ""
    if sid:
        return sid, "session_id"
    key = host.get("HERMES_SESSION_KEY") or ""
    if key:
        return "key:" + key, "session_key"
    return "", "none"


def _session_id_from_host() -> str:
    """Bound caller id, or empty when the only fallback would be the local bucket."""
    ident, source = _resolve_identity()
    if source == "local":
        return ""
    return ident


def _implicit_session_id() -> str:
    """Identity allowed to own an implicit receipt. Raises when none is trustworthy."""
    ident, source = _resolve_identity()
    if source == "none" or not ident:
        raise ValueError(_NO_IDENTITY)
    return ident


def _session_platform() -> str:
    """Platform identity from Hermes session ContextVars (not raw os.environ alone)."""
    try:
        from gateway.session_context import get_session_env

        session_plat = get_session_env("HERMES_SESSION_PLATFORM", "") or ""
    except Exception:
        session_plat = os.environ.get("HERMES_SESSION_PLATFORM") or ""
    # HERMES_PLATFORM remains a process-level override used by some local surfaces.
    plat = os.environ.get("HERMES_PLATFORM") or session_plat or ""
    return str(plat).strip().lower()


def _on_gateway() -> bool:
    plat = _session_platform()
    return bool(plat) and plat not in _LOCAL_PLATFORMS


def _agent_cwd() -> Path:
    """Hermes logical session / terminal cwd; falls back to process cwd."""
    try:
        from agent.runtime_cwd import resolve_agent_cwd

        return Path(resolve_agent_cwd()).resolve()
    except Exception:
        return Path.cwd().resolve()


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("checkyourself: failed reading %s", path, exc_info=True)
    return default


def _atomic_write_json(path: Path, payload: Any) -> None:
    """Write JSON via a unique temp file + os.replace (safe under concurrent writers)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _save_json(path: Path, payload: Any) -> None:
    _atomic_write_json(path, payload)


def _with_file_lock(lock_path: Path):
    """Exclusive flock context manager for ledger RMW."""

    class _Lock:
        def __enter__(self_inner):
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            self_inner._fh = open(lock_path, "a+", encoding="utf-8")
            fcntl.flock(self_inner._fh.fileno(), fcntl.LOCK_EX)
            return self_inner._fh

        def __exit__(self_inner, *exc):
            try:
                fcntl.flock(self_inner._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self_inner._fh.close()

    return _Lock()


def _append_ledger(entry: Dict[str, Any]) -> None:
    path = _ledger_path()
    lock_path = path.with_suffix(path.suffix + ".lock")
    with _with_file_lock(lock_path):
        ledger = _load_json(path, [])
        if not isinstance(ledger, list):
            ledger = []
        ledger.append(entry)
        _atomic_write_json(path, ledger[-LEDGER_MAX:])


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
    return env


def _close_pipes(proc: subprocess.Popen) -> None:
    for stream in (proc.stdout, proc.stderr, proc.stdin):
        if stream is None:
            continue
        try:
            stream.close()
        except Exception:
            pass


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _kill_process_group(proc: subprocess.Popen, grace: Optional[float] = None) -> None:
    """Terminate the whole process group started in its own session.

    Leader exit is NOT evidence the group is gone: descendants may ignore SIGTERM.
    After the grace period every remaining group member gets SIGKILL.
    """
    grace = _KILL_GRACE if grace is None else grace
    pgid = proc.pid
    if pgid is None:
        _close_pipes(proc)
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.terminate()
        except Exception:
            pass
    deadline = time.monotonic() + max(0.0, float(grace))
    while time.monotonic() < deadline:
        proc.poll()  # reap the leader so it does not linger as a zombie group member
        if not _group_alive(pgid):
            break
        time.sleep(0.05)
    if _group_alive(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except Exception:
                pass
    try:
        proc.wait(timeout=2.0)
    except Exception:
        pass
    _close_pipes(proc)


def run_checkyourself(args: List[str]) -> Dict[str, Any]:
    cmd = shlex.split(str(_cfg("checkyourself_command"))) + args
    timeout = int(_cfg("timeout_seconds"))
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_scrubbed_env(),
            cwd=str(_data_dir()),
            start_new_session=True,  # own process group for tree kill on timeout
        )
    except (OSError, ValueError) as exc:
        return {
            "ok": False,
            "error": f"checkyourself not runnable (need Node >=18 + npx + Python 3): {exc}",
        }
    try:
        out_s, err_s = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        return {"ok": False, "error": "checkyourself timed out"}
    except BaseException:
        _kill_process_group(proc, grace=0.0)
        raise
    if _group_alive(proc.pid):
        # Leader finished but left descendants in its group; do not leave them running.
        _kill_process_group(proc, grace=0.0)
    out = (out_s or "").strip()
    err = (err_s or "").strip()
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
        p = (_agent_cwd() / p).resolve()
    else:
        p = p.resolve()
    if not p.exists():
        raise ValueError(f"project path does not exist: {p}")
    if not p.is_dir():
        raise ValueError(f"project path is not a directory: {p}")
    return p


def _implicit_blocked(session_id: str) -> bool:
    with _IMPLICIT_BLOCK_LOCK:
        return session_id in _IMPLICIT_BLOCKED


def _block_implicit(session_id: str) -> None:
    if not session_id:
        return
    with _IMPLICIT_BLOCK_LOCK:
        _IMPLICIT_BLOCKED.add(session_id)


def _clear_implicit_block(session_id: str) -> None:
    if not session_id:
        return
    with _IMPLICIT_BLOCK_LOCK:
        _IMPLICIT_BLOCKED.discard(session_id)


def _implicit_pointer_path(session_id: Optional[str] = None) -> Path:
    sid = session_id if session_id is not None else _implicit_session_id()
    return _implicit_dir() / f"{_safe_key(str(sid))}.json"


def _invalidate_implicit(session_id: Optional[str] = None, reason: str = "failed_scan", error: str = "") -> bool:
    """Write an invalid pointer. Return False when the write did not land.

    A False return must not be reported as a successful invalidation. The caller
    fail-closes implicit scoring for this identity until a new scan commits.
    """
    sid = session_id if session_id is not None else _implicit_session_id()
    path = _implicit_pointer_path(sid)
    meta = {
        "valid": False,
        "invalidated_at": int(time.time()),
        "reason": reason,
        "session_id": sid or None,
        **({"error": str(error)[:300]} if error else {}),
    }
    try:
        _atomic_write_json(path, meta)
    except Exception:
        logger.debug("checkyourself: failed invalidating implicit receipt", exc_info=True)
        return False
    return True


def _mark_implicit_invalid(session_id: str, error: str) -> Tuple[bool, str]:
    """Invalidate the pointer and report the real outcome.

    When the write fails, implicit scoring stays fail-closed in this runtime
    even though the previous pointer file is still on disk.
    """
    if _invalidate_implicit(session_id, reason="failed_scan", error=error):
        return True, ""
    _block_implicit(session_id)
    return (
        False,
        "implicit receipt pointer could not be updated; scoring stays fail-closed until a new scan commits",
    )


def _write_receipt(
    scan_data: Dict[str, Any],
    *,
    project: Path,
    deep: bool,
    max_files: int,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Immutable session/project-bound scan receipt; updates the session's implicit pointer."""
    sid = session_id if session_id is not None else _session_id_from_host()
    receipt_id = uuid.uuid4().hex
    receipt_path = _receipts_dir() / f"{receipt_id}.json"
    provenance = {
        "receipt_id": receipt_id,
        "session_id": sid or None,
        "project": str(project),
        "deep": bool(deep),
        "max_files": int(max_files),
        "ts": int(time.time()),
    }
    envelope = {
        **provenance,
        "valid": True,
        "data": scan_data,
    }
    _atomic_write_json(receipt_path, envelope)
    _atomic_write_json(
        _implicit_pointer_path(sid),
        {
            "valid": True,
            "receipt_id": receipt_id,
            "receipt_path": str(receipt_path),
            "project": str(project),
            "session_id": sid or None,
            "ts": provenance["ts"],
        },
    )
    _clear_implicit_block(sid or "")
    return provenance | {"receipt_path": str(receipt_path)}


def _load_receipt(receipt_path: Path) -> Dict[str, Any]:
    envelope = _load_json(receipt_path, None)
    if not isinstance(envelope, dict) or not envelope.get("valid", True):
        raise ValueError(f"receipt is missing or invalidated: {receipt_path}")
    if not _is_receipt_envelope(envelope):
        # Raw scan JSON written directly
        if "counts" in envelope or "findings" in envelope:
            return envelope
        raise ValueError(f"receipt has no scan data: {receipt_path}")
    return envelope["data"]


def _resolve_explicit_findings(explicit: str) -> Path:
    p = Path(str(explicit)).expanduser()
    if not p.is_absolute():
        p = (_agent_cwd() / p).resolve()
    else:
        p = p.resolve()
    if not p.is_file():
        raise ValueError(f"findings file not found: {p}")
    return p


def _select_findings(explicit: Optional[str], session_id: str) -> tuple[Path, Optional[Dict[str, Any]]]:
    """Pick the score input once. Returns (path, pointer snapshot for implicit receipts).

    The pointer is read exactly once; callers must use the returned snapshot for provenance
    instead of rereading the mutable per-session pointer after the CLI runs.
    """
    if explicit:
        return _resolve_explicit_findings(explicit), None
    if _implicit_blocked(session_id):
        raise ValueError(
            "implicit scoring is fail-closed after the receipt pointer could not be invalidated; "
            "re-run checkyourself_scan once plugin-data is writable"
        )
    pointer = _load_json(_implicit_pointer_path(session_id), None)
    if not isinstance(pointer, dict) or not pointer.get("valid"):
        raise ValueError(
            "no valid session receipt: run checkyourself_scan first, or pass findings_path / receipt_id "
            "to an existing scan JSON (a failed scan invalidates the previous implicit receipt)"
        )
    receipt_path = Path(str(pointer.get("receipt_path") or ""))
    if not receipt_path.is_file():
        rid = pointer.get("receipt_id")
        if rid:
            receipt_path = _receipts_dir() / f"{_safe_key(str(rid))}.json"
    if not receipt_path.is_file():
        raise ValueError(
            "session receipt pointer is stale; re-run checkyourself_scan or pass an explicit findings_path"
        )
    return receipt_path, dict(pointer)


def _findings_path(explicit: Optional[str] = None) -> Path:
    if explicit:
        return _select_findings(explicit, _session_id_from_host())[0]
    return _select_findings(None, _implicit_session_id())[0]


def _is_receipt_envelope(raw: Any) -> bool:
    return isinstance(raw, dict) and _RECEIPT_KEYS.issubset(raw.keys()) and "session_id" in raw


def _tmp_dir() -> Path:
    p = _data_dir() / "tmp"
    p.mkdir(parents=True, exist_ok=True)
    return p


@contextlib.contextmanager
def _materialized_findings(path: Path):
    """Yield a CLI-ready findings path.

    Raw CLI-supported inputs (scan objects, findings arrays including ``[]``, anything else)
    are passed through untouched. Only a recognized plugin receipt envelope is unpacked, into
    a unique temp file under plugin-data that is removed afterwards. The caller's input
    directory is never written to.
    """
    raw = _load_json(path, None)
    if not _is_receipt_envelope(raw):
        yield path
        return
    if not raw.get("valid", False):
        raise ValueError(f"receipt is invalidated: {path}")
    fd, tmp_name = tempfile.mkstemp(prefix="findings-", suffix=".json", dir=str(_tmp_dir()))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(raw["data"], ensure_ascii=False))
        yield Path(tmp_name)
    finally:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass


# --- operations -------------------------------------------------------------

def describe() -> Dict[str, Any]:
    return run_checkyourself(["describe", "--format", "json"])


def _scan_once(project: Optional[str], deep: bool, max_files: Optional[int], sid: str) -> Dict[str, Any]:
    root = _resolve_project(project)
    try:
        mf = int(max_files if max_files is not None else _cfg("max_files"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"max_files must be an integer: {max_files!r}") from exc
    if mf <= 0:
        raise ValueError(f"max_files must be positive: {mf}")
    args = ["scan", str(root), "--no-write", "--format", "json", "--max-files", str(mf)]
    if deep:
        args.append("--deep")
    res = run_checkyourself(args)
    if not (res.get("ok") and isinstance(res.get("data"), dict)):
        return res
    provenance = _write_receipt(res["data"], project=root, deep=bool(deep), max_files=mf, session_id=sid)
    res["receipt_id"] = provenance["receipt_id"]
    res["receipt_path"] = provenance["receipt_path"]
    res["provenance"] = {
        "session_id": provenance.get("session_id"),
        "project": provenance["project"],
        "ts": provenance["ts"],
        "deep": provenance["deep"],
        "max_files": provenance["max_files"],
    }
    return res


def scan(project: Optional[str] = None, deep: bool = False, max_files: Optional[int] = None) -> Dict[str, Any]:
    """Scan and bind a receipt to the caller identity captured once at entry.

    ANY failure (path / argument validation, missing executable, raised subprocess error,
    non-zero CLI, non-scan output) tries to invalidate that caller's implicit receipt.
    ``implicit_receipt_invalidated`` is true only when that write landed. A failed write
    fail-closes implicit scoring until a later scan commits.
    """
    try:
        sid = _implicit_session_id()
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "implicit_receipt_invalidated": False}
    try:
        res = _scan_once(project, deep, max_files, sid)
    except Exception as exc:
        invalidated, detail = _mark_implicit_invalid(sid, str(exc))
        out: Dict[str, Any] = {"ok": False, "error": str(exc), "implicit_receipt_invalidated": invalidated}
        if detail:
            out["implicit_invalidation_error"] = detail
        return out
    if not res.get("receipt_id"):
        invalidated, detail = _mark_implicit_invalid(sid, str(res.get("error") or ""))
        res["implicit_receipt_invalidated"] = invalidated
        if detail:
            res["implicit_invalidation_error"] = detail
    return res


def _run_on_findings(verb: str, findings_path: Optional[str], extra: List[str]) -> Dict[str, Any]:
    if findings_path:
        path, pointer = _select_findings(findings_path, _session_id_from_host())
    else:
        path, pointer = _select_findings(None, _implicit_session_id())
    with _materialized_findings(path) as cli_path:
        res = run_checkyourself([verb, "--findings", str(cli_path), "--format", "json", *extra])
    if pointer is not None:
        # Provenance from the snapshot actually scored — never a reread of the live pointer.
        res["receipt_id"] = pointer.get("receipt_id")
        res["receipt_path"] = str(path)
        res["provenance"] = {
            "session_id": pointer.get("session_id"),
            "project": pointer.get("project"),
            "ts": pointer.get("ts"),
        }
    return res


def score(findings_path: Optional[str] = None, claim: Optional[str] = None) -> Dict[str, Any]:
    extra = ["--no-history"]
    if claim:
        extra += ["--claim", str(claim)[:500]]
    return _run_on_findings("score", findings_path, extra)


def backlog(findings_path: Optional[str] = None) -> Dict[str, Any]:
    return _run_on_findings("backlog", findings_path, [])


def next_batch(findings_path: Optional[str] = None) -> Dict[str, Any]:
    return _run_on_findings("next", findings_path, [])


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


def _extract_message_text(user_message: Any) -> str:
    """Flatten Hermes multimodal / list content into plain text for claim matching."""
    if user_message is None:
        return ""
    if isinstance(user_message, str):
        return user_message
    if isinstance(user_message, dict):
        # Single content block
        for key in ("text", "content", "value"):
            val = user_message.get(key)
            if isinstance(val, str):
                return val
            if isinstance(val, (list, dict)):
                return _extract_message_text(val)
        return ""
    if isinstance(user_message, (list, tuple)):
        parts: List[str] = []
        for block in user_message:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                btype = str(block.get("type") or "").lower()
                if btype in {"image", "image_url", "input_image", "media"}:
                    continue
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
                elif isinstance(text, dict) and isinstance(text.get("value"), str):
                    parts.append(text["value"])
                elif isinstance(block.get("content"), str):
                    parts.append(block["content"])
                else:
                    nested = _extract_message_text(block.get("content"))
                    if nested:
                        parts.append(nested)
        return "\n".join(p for p in parts if p)
    return str(user_message)


def _on_pre_llm(user_message: Any = "", **_: Any) -> Optional[Dict[str, str]]:
    try:
        text = _extract_message_text(user_message)
        if _cfg("inject_on_claim") and text and _CLAIM_RE.search(text):
            return {"context": _BRIEF}
    except Exception:
        logger.debug("checkyourself: pre_llm_call failed", exc_info=True)
    return None


def _finding_counts_from_scan(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Prefer CLI contract `data.counts` (P0–P3); fall back to summary dicts."""
    counts = data.get("counts")
    if isinstance(counts, dict):
        out = {
            k: counts[k]
            for k in ("P0", "P1", "P2", "P3", "total", "p0", "p1", "p2", "p3")
            if k in counts
        }
        if out:
            return out
    findings = data.get("findings") or data.get("summary") or {}
    if isinstance(findings, dict):
        out = {
            k: findings.get(k)
            for k in ("p0", "p1", "p2", "p3", "total", "P0", "P1", "P2", "P3", "count")
            if k in findings
        }
        return out or None
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
                payload = {"raw": result[:200], "ok": False}
        entry: Dict[str, Any] = {
            "ts": int(time.time()),
            "tool": tool_name,
            "ok": isinstance(payload, dict) and bool(payload.get("ok")),
        }
        if isinstance(payload, dict):
            if payload.get("truncated"):
                entry["truncated"] = True
            if payload.get("receipt_id"):
                entry["receipt_id"] = payload.get("receipt_id")
            if isinstance(payload.get("provenance"), dict):
                entry["project"] = payload["provenance"].get("project")
                entry["session_id"] = payload["provenance"].get("session_id")
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            if tool_name == "checkyourself_scan":
                entry["project"] = entry.get("project") or data.get("project")
                entry["files_scanned"] = data.get("files_scanned")
                entry["finding_counts"] = _finding_counts_from_scan(data)
            if tool_name == "checkyourself_score":
                entry["score"] = data.get("score", data.get("production_reality_score"))
                entry["band"] = data.get("band", data.get("tier"))
        # Summary-only payloads (truncated envelope) still carry top-level summary fields.
        if isinstance(payload, dict) and tool_name == "checkyourself_scan":
            summary = payload.get("summary")
            if isinstance(summary, dict):
                entry.setdefault("project", summary.get("project"))
                entry.setdefault("files_scanned", summary.get("files_scanned"))
                if entry.get("finding_counts") is None and isinstance(summary.get("counts"), dict):
                    entry["finding_counts"] = _finding_counts_from_scan({"counts": summary["counts"]})
        if isinstance(payload, dict) and tool_name == "checkyourself_score":
            summary = payload.get("summary")
            if isinstance(summary, dict):
                entry.setdefault("score", summary.get("score"))
                entry.setdefault("band", summary.get("band"))
        _append_ledger(entry)
    except Exception:
        logger.debug("checkyourself: post_tool_call failed", exc_info=True)
    return None


def _completion_tool_names() -> set[str]:
    raw = str(_cfg("completion_tools") or "")
    return {part.strip() for part in raw.split(",") if part.strip()}


def _score_gate_verdict(score_res: Dict[str, Any]) -> Dict[str, Any]:
    """Turn one CheckYourself score payload into an allow/block decision.

    Allowed only when the CLI returned ok, the score is numeric, and the open
    counts contain no P0 or P1. Anything else, including a missing score, blocks.
    """
    data = score_res.get("data") if isinstance(score_res.get("data"), dict) else {}
    counts = data.get("counts") if isinstance(data.get("counts"), dict) else {}
    try:
        p0 = int(counts.get("P0") or 0)
        p1 = int(counts.get("P1") or 0)
    except (TypeError, ValueError):
        p0, p1 = 1, 1
    raw_score = data.get("score", data.get("production_reality_score"))
    numeric = isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool)
    allowed = bool(score_res.get("ok")) and numeric and p0 == 0 and p1 == 0
    return {
        "allowed": allowed,
        "policy": "numeric-score-and-no-open-P0-or-P1",
        "score": raw_score if numeric else None,
        "counts": {"P0": p0, "P1": p1},
        "score_mode": data.get("score_mode"),
        "ok": bool(score_res.get("ok")),
        "error": score_res.get("error"),
    }


def _gate_findings_arg(args: Optional[Dict[str, Any]]) -> Optional[str]:
    """Explicit evidence on a completion call, if the caller supplied any."""
    if not isinstance(args, dict):
        return None
    meta = args.get("metadata") if isinstance(args.get("metadata"), dict) else {}
    bundled = meta.get("checkyourself") if isinstance(meta.get("checkyourself"), dict) else {}
    for source in (bundled, args):
        for key in ("findings_path", "receipt_id"):
            val = source.get(key)
            if isinstance(val, str) and val.strip():
                token = val.strip()
                if key == "receipt_id" and re.fullmatch(r"[0-9a-fA-F]{32}", token):
                    path = _receipts_dir() / f"{token}.json"
                    if not path.is_file():
                        raise ValueError("receipt_id is not in plugin-data")
                    return str(path)
                return token
    return None


def evaluate_completion_gate(tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Score completion evidence and decide. Non-completion tools are not gated."""
    if tool_name not in _completion_tool_names():
        return {"gated": False, "allowed": True, "tool": tool_name}
    try:
        explicit = _gate_findings_arg(args)
        scored = score(explicit)
    except Exception as exc:
        scored = {"ok": False, "error": str(exc)}
    verdict = _score_gate_verdict(scored if isinstance(scored, dict) else {"ok": False, "error": "non-dict score"})
    verdict["gated"] = True
    verdict["tool"] = tool_name
    return verdict


def _completion_block_message(verdict: Dict[str, Any]) -> str:
    score_val = verdict.get("score")
    counts = verdict.get("counts") if isinstance(verdict.get("counts"), dict) else {}
    if score_val is None:
        detail = verdict.get("error") or "evidence unavailable"
        return (
            "Completion blocked: no completion-evidence score. "
            "Run checkyourself_scan and checkyourself_score, then retry. "
            f"({detail})"
        )
    return (
        f"Completion blocked: evidence score {score_val} "
        f"(P0={counts.get('P0', '?')}, P1={counts.get('P1', '?')}). "
        "Policy requires a numeric score and no open P0 or P1."
    )


def _on_pre_tool(tool_name: str = "", args: Optional[Dict[str, Any]] = None, **_: Any) -> Optional[Dict[str, str]]:
    """Fail-closed completion gate. None means allow; a block dict stops the tool."""
    try:
        if tool_name not in _completion_tool_names():
            return None
        verdict = evaluate_completion_gate(tool_name, args)
        if verdict.get("allowed"):
            return None
        return {"action": "block", "message": _completion_block_message(verdict)}
    except Exception:
        logger.debug("checkyourself: pre_tool_call gate failed", exc_info=True)
        return {
            "action": "block",
            "message": "Completion blocked: evidence gate failed closed.",
        }


# --- tools ------------------------------------------------------------------

SCAN_SCHEMA = {
    "name": "checkyourself_scan",
    "description": (
        "Read-only CheckYourself scan of a project: stack signals + deterministic local findings. "
        "Writes no files into the project (--no-write); saves an immutable session/project receipt "
        "under HERMES plugin-data for score/backlog (returns receipt_id)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "project": {"type": "string", "description": "Project root to scan (default: plugin default_project / Hermes session cwd)."},
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
        "Defaults to this session's last valid scan receipt. Score is evidence, not a safety certification."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "findings_path": {"type": "string", "description": "Path to scan/findings JSON or receipt; omit to use this session's last valid receipt."},
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


def _scan_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    counts = data.get("counts") if isinstance(data.get("counts"), dict) else {}
    return {
        "project": data.get("project") or (payload.get("provenance") or {}).get("project"),
        "files_scanned": data.get("files_scanned"),
        "counts": {
            k: counts[k] for k in ("P0", "P1", "P2", "P3") if k in counts
        } or None,
        "deep": data.get("deep"),
        "scan_limits": data.get("scan_limits"),
        "receipt_id": payload.get("receipt_id"),
        "receipt_path": payload.get("receipt_path"),
        "provenance": payload.get("provenance"),
    }


def _score_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    counts = data.get("counts") if isinstance(data.get("counts"), dict) else {}
    return {
        "score": data.get("score", data.get("production_reality_score")),
        "raw_score": data.get("raw_score"),
        "score_mode": data.get("score_mode"),
        "confidence": data.get("confidence"),
        "band": data.get("band", data.get("tier")),
        "caps": _score_caps(data),
        "counts": {k: counts[k] for k in ("P0", "P1", "P2", "P3") if k in counts} or None,
        "coverage_complete": data.get("coverage_complete"),
        "receipt_id": payload.get("receipt_id"),
        "receipt_path": payload.get("receipt_path"),
        "provenance": payload.get("provenance"),
    }


def _score_caps(data: Dict[str, Any]) -> Optional[List[Any]]:
    caps = data.get("caps_applied", data.get("caps", data.get("score_caps")))
    if isinstance(caps, list):
        return [
            {"cap": c.get("cap"), "reason": str(c.get("reason", ""))[:160]} if isinstance(c, dict) else c
            for c in caps[:10]
        ]
    return caps or None


def _payload_kind(data: Any) -> str:
    """Dispatch on the CLI schema id first; score is checked before shared fields like counts."""
    if not isinstance(data, dict):
        return "generic"
    schema = str(data.get("schema") or "")
    if schema.startswith("checkyourself-score"):
        return "score"
    if schema.startswith("checkyourself-scan"):
        return "scan"
    if schema:
        return "generic"
    if "score" in data or "production_reality_score" in data:
        return "score"
    if "files_scanned" in data or "counts" in data or "findings" in data:
        return "scan"
    return "generic"


def _bounded_tool_json(out: Dict[str, Any], max_out: int = MAX_OUT) -> str:
    """Always return valid JSON. Large payloads become a truncated envelope with artifact ref."""
    full = json.dumps(out, ensure_ascii=False)
    if len(full) <= max_out:
        return full
    kind = _payload_kind(out.get("data"))
    if kind == "scan":
        summary: Dict[str, Any] = _scan_summary(out)
    elif kind == "score":
        summary = _score_summary(out)
    else:
        summary = {
            "keys": sorted(out.keys())[:20],
            "receipt_id": out.get("receipt_id"),
            "receipt_path": out.get("receipt_path"),
            "error": out.get("error"),
        }
    artifact = out.get("receipt_path") or out.get("receipt_id")
    candidates: List[Dict[str, Any]] = [
        {
            "ok": bool(out.get("ok")),
            "truncated": True,
            "kind": kind,
            "summary": summary,
            "artifact_ref": artifact,
            "note": (
                "Full CLI JSON omitted to keep a valid tool response; "
                "use artifact_ref / receipt_path for the complete scan."
                if artifact
                else "Full payload omitted to keep a valid tool response."
            ),
            **({"stderr": str(out.get("stderr"))[-200:]} if out.get("stderr") else {}),
            **({"error": out.get("error")} if out.get("error") else {}),
        },
        {
            "ok": bool(out.get("ok")),
            "truncated": True,
            "kind": kind,
            "summary": {
                k: summary.get(k)
                for k in ("project", "files_scanned", "counts", "score", "score_mode", "band", "receipt_id")
                if k in summary and summary.get(k) is not None
            },
            "artifact_ref": artifact,
        },
        {
            "ok": bool(out.get("ok")),
            "truncated": True,
            "summary": {"receipt_id": out.get("receipt_id"), "project": (out.get("provenance") or {}).get("project") if isinstance(out.get("provenance"), dict) else None},
            "artifact_ref": artifact,
        },
        {
            "ok": bool(out.get("ok")),
            "truncated": True,
            "artifact_ref": artifact,
        },
    ]
    for envelope in candidates:
        encoded = json.dumps(envelope, ensure_ascii=False)
        if len(encoded) <= max_out:
            return encoded
    # Absolute last resort: still valid JSON, never a mid-string cut of the original.
    return json.dumps({"ok": bool(out.get("ok")), "truncated": True}, ensure_ascii=False)


def _capture_session_kwargs(kwargs: Dict[str, Any]) -> Optional[str]:
    for key in ("session_id", "hermes_session_id", "task_id", "sessionId"):
        val = kwargs.get(key)
        if val:
            return str(val)
    return None


def _wrap(fn):
    def handler(args: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
        captured = _capture_session_kwargs(kwargs)
        token = _CALL_SESSION.set(captured) if captured else None
        try:
            try:
                out = fn(args or {})
            except ValueError as exc:
                out = {"ok": False, "error": str(exc)}
            except Exception as exc:  # never crash the agent loop
                logger.debug("checkyourself tool failed", exc_info=True)
                out = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            if not isinstance(out, dict):
                out = {"ok": False, "error": "internal: non-dict tool result"}
            return _bounded_tool_json(out)
        finally:
            if token is not None:
                _CALL_SESSION.reset(token)

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
    "  /checkyourself scan [project] [--deep]          Read-only scan (session-bound receipt)\n"
    "  /checkyourself score [findings.json]            Production Reality Score\n"
    "  /checkyourself backlog [findings.json]          Ranked remediation backlog\n"
    "  /checkyourself next [findings.json]             Next approval batch\n"
    "  /checkyourself coverage [label]                 20-surface coverage skeleton\n"
    "  /checkyourself status                           Recent score-ledger entries\n"
    "Not exposed via slash: challenge, init, mcp, receipt, diff (use the CheckYourself CLI).\n"
    "On gateway platforms, scan/score/backlog/next/coverage are refused unless "
    "allow_project_slash_on_gateway: true.\n"
    "Completion tools named in completion_tools (default kanban_complete) stay blocked "
    "until the CheckYourself score is numeric and has no open P0 or P1."
)


def _fmt_scan(data: Dict[str, Any], res: Dict[str, Any], lines: List[str]) -> str:
    counts = data.get("counts") if isinstance(data.get("counts"), dict) else {}
    lines.append(f"files_scanned: {data.get('files_scanned')}")
    if counts:
        lines.append("counts: " + ", ".join(f"{k}={counts.get(k, 0)}" for k in ("P0", "P1", "P2", "P3")))
    if data.get("project"):
        lines.append(f"scanned_project: {data.get('project')}")
    findings = data.get("findings")
    if isinstance(findings, list) and findings:
        lines.append(f"findings_listed: {len(findings)}")
    if res.get("receipt_path"):
        lines.append(f"full_artifact: {res['receipt_path']}")
    return "\n".join(lines)[:SLASH_MAX]


def _fmt_score(data: Dict[str, Any], res: Dict[str, Any], lines: List[str]) -> str:
    summary = _score_summary(res)
    lines.append(f"score: {summary['score']}")
    if summary.get("raw_score") is not None and summary.get("raw_score") != summary.get("score"):
        lines.append(f"raw_score: {summary['raw_score']}")
    for key in ("score_mode", "confidence", "band"):
        if summary.get(key):
            lines.append(f"{key}: {summary[key]}")
    if summary.get("counts"):
        lines.append("counts: " + ", ".join(f"{k}={v}" for k, v in summary["counts"].items()))
    caps = summary.get("caps")
    if isinstance(caps, list):
        for cap in caps:
            if isinstance(cap, dict):
                lines.append(f"cap: {cap.get('cap')} ({cap.get('reason')})")
    if summary.get("coverage_complete") is not None:
        lines.append(f"coverage_complete: {summary['coverage_complete']}")
    if res.get("receipt_path"):
        lines.append(f"from_receipt: {res['receipt_path']}")
    return "\n".join(lines)[:SLASH_MAX]


def _fmt(res: Dict[str, Any]) -> str:
    """Slash-facing summary — never slice mid-JSON."""
    if not res.get("ok") and "data" not in res:
        return f"CheckYourself failed: {res.get('error') or res.get('stderr') or res}"
    lines: List[str] = []
    if res.get("receipt_id"):
        lines.append(f"receipt_id: {res['receipt_id']}")
    if isinstance(res.get("provenance"), dict):
        prov = res["provenance"]
        if prov.get("project"):
            lines.append(f"project: {prov['project']}")
        if prov.get("session_id"):
            lines.append(f"session: {prov['session_id']}")
    data = res.get("data")
    kind = _payload_kind(data)
    if kind == "score":
        return _fmt_score(data, res, lines)
    if kind == "scan":
        return _fmt_scan(data, res, lines)
    if isinstance(data, dict):
        # Generic small JSON — dump with indent but never mid-cut invalidly
        dumped = json.dumps(data, indent=2, ensure_ascii=False)
        if len(dumped) <= SLASH_MAX:
            prefix = ("\n".join(lines) + "\n") if lines else ""
            return (prefix + dumped)[:SLASH_MAX]
        keys = list(data.keys())[:12]
        lines.append(f"keys: {keys}")
        lines.append("(truncated — ask via tool for full JSON)")
        return "\n".join(lines)[:SLASH_MAX]
    text = str(res.get("text", ""))
    return text[:SLASH_MAX]


def _slash(raw_args: str) -> str:
    raw = (raw_args or "").strip()
    if not raw:
        return _HELP
    try:
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
        if cmd == "describe":
            return _fmt(describe())
        if cmd == "status":
            return json.dumps(_load_json(_ledger_path(), [])[-10:], indent=2)[:SLASH_MAX]
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
    ctx.register_hook("pre_tool_call", _on_pre_tool)
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
