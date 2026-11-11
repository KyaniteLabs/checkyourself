"""CheckYourself for Hermes: check a project before anyone calls it done.

Surfaces:
  checkyourself_scan  -> scan a project folder, return findings and the score estimate
  checkyourself_next  -> the next approval batch from that project's last scan
  /checkyourself      -> scan | next | status | help
  pre_llm_call        -> when a message asks whether work is done or ready to ship,
                         remind the agent to check before it answers
  skill               -> skills/checkyourself/SKILL.md

The scanner is the CheckYourself CLI, vendored under vendor/checkyourself and run
with this Python in a child process. It reads files and never runs project code:
the CLI's `challenge` and `receipt` commands, which do, are not exposed. Scans are
confined to one root folder. The last scan per project is kept under
<HERMES_HOME>/plugin-data/checkyourself/scans/ so `next` can rank from it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PLUGIN_NAME = "checkyourself"
PLUGIN_DIR = Path(__file__).resolve().parent
CLI_PATH = PLUGIN_DIR / "vendor" / "checkyourself" / "tools" / "checkyourself.py"
VENDOR_MANIFEST = PLUGIN_DIR / "vendor" / "MANIFEST.json"
CLI_VERSION = "1.7.0"
SCANS_KEPT = 20
TOP_FINDINGS = 10
_LIMIT_KEYS = ("files_beyond_limit", "symlinks_skipped", "symlink_dirs_skipped", "files_oversized", "files_unreadable", "content_truncated")
TOOL_JSON_MAX = 20_000
SLASH_DISPLAY = 3_500
STDOUT_MAX = 8 * 1024 * 1024
STDERR_MAX = 64 * 1024
_KILL_GRACE = 0.5

DEFAULTS: Dict[str, Any] = {
    "scan_root": "",
    "inject_on_ship_talk": True,
    "allow_slash_scan_on_gateway": False,
    "max_files": 6000,
    "timeout_seconds": 120,
}

# Mirrors gateway.session_context.NON_MESSAGING_SESSION_SURFACES.
_NON_MESSAGING = frozenset({
    "", "api_server", "cli", "codex", "desktop", "gateway", "kanban", "local",
    "msgraph_webhook", "tool", "tui", "webhook",
})
_CWD_SENTINELS = frozenset({"", ".", "./", "auto", "cwd"})

# Questions about whether work is finished. Plain mentions of "ship" or "done"
# in other senses do not match: "are we done with lunch?", "is the oven ready?",
# "are you ready?", "can we ship the package to Ohio?". Pattern matching is still
# a heuristic; the README says so.
_WORK = (r"(?:it|this|that|we|the\s+(?:pr|branch|build|release|feature|fix|patch|change|changes|"
         r"code|app|site|page|api|migration|deploy|deployment|project|work|task|ticket|refactor|"
         r"tests?|ci|pipeline|service|plugin|update|upgrade|version|launch))")
_NOT_WORK_OBJ = (r"(?!\s+(?:the|a|an|this|that|my|your|our)\s+(?:package|parcel|box|order|letter|"
                 r"gift|car|boat|kayak|rocket|balloon|bag|kids?|dog)s?\b)")
_SHIP_RE = re.compile(
    r"(?:"
    r"\b(?:is|are)\s+" + _WORK + r"\s+(?:really\s+|actually\s+|all\s+)?"
    r"(?:done|finished|complete|ready)\b(?!\s+(?:with|for|to|eating|cooking|baking)\b)|"
    r"\b(?:we're|we\s+are|it's|it\s+is|this\s+is)\s+(?:really\s+)?(?:done|finished|ready)\s*[,.]?\s*(?:right|yes|correct|yeah)\s*\?|"
    r"\bready\s+(?:to|for)\s+(?:ship|launch|merge|deploy|release|production|prod)\b|"
    r"\b(?:production|launch|ship|release)[- ]ready\b|"
    r"\bgood\s+to\s+(?:ship|merge|go\s+live|launch|deploy|release)\b|"
    r"\bship\s+it\s*[?!]|"
    r"\b(?:can|could|should)\s+(?:we|i)\s+(?:ship|launch|merge|deploy|release)\b" + _NOT_WORK_OBJ + r"|"
    r"\bcheck\s*yourself\b|\bcheckyourself\b"
    r")",
    re.IGNORECASE,
)

_BRIEF = (
    "[CheckYourself] The user is asking whether work is done or ready to ship. "
    "Do not answer from memory or from the work's own summary. Re-derive each claim "
    "from the work: run checkyourself_scan on the project, run the tests or open the "
    "page yourself, and label each claim CONFIRMED, REFUTED or UNVERIFIABLE with the "
    "evidence. A scan with no findings is Unknown, not a pass. The score without "
    "coverage evidence is a low-confidence estimate; say so. Ask before fixing anything."
)

_ctx = None
_LOCK = threading.Lock()


# --- config and storage ------------------------------------------------------

def _settings_from_config() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config

        entries = ((load_config() or {}).get("plugins") or {}).get("entries") or {}
        settings = (entries.get(PLUGIN_NAME) or {}).get("settings") or {}
        return settings if isinstance(settings, dict) else {}
    except Exception:
        return {}


def _cfg(key: str) -> Any:
    try:
        val = _ctx.get_config(key, None) if _ctx is not None else _settings_from_config().get(key)
    except Exception:
        val = None
    return DEFAULTS[key] if val is None else val


def _bool_cfg(key: str) -> bool:
    """Only a real true/false counts; anything else (such as the string "false") is the default."""
    val = _cfg(key)
    return val if isinstance(val, bool) else bool(DEFAULTS[key])


def _int_cfg(key: str, lo: int, hi: int) -> int:
    try:
        val = int(_cfg(key))
    except (TypeError, ValueError):
        val = int(DEFAULTS[key])
    return max(lo, min(hi, val))


def _data_dir() -> Path:
    try:
        from plugins.plugin_storage import plugin_data_dir

        return plugin_data_dir(PLUGIN_NAME)
    except Exception:
        home = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
        p = Path(home) / "plugin-data" / PLUGIN_NAME
        p.mkdir(parents=True, exist_ok=True)
        return p


def _scans_dir() -> Path:
    p = _data_dir() / "scans"
    p.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p, 0o700)
    except OSError:
        pass
    return p


def _scan_file(project: Path) -> Path:
    """The raw scan JSON, exactly as the CLI wrote it, so score and next can read it."""
    digest = hashlib.sha256(str(project).encode("utf-8")).hexdigest()[:16]
    return _scans_dir() / f"{digest}.json"


def _meta_file(store: Path) -> Path:
    return store.with_name(store.stem + ".meta")


def _read_meta(store: Path) -> Dict[str, Any]:
    try:
        meta = json.loads(_meta_file(store).read_text(encoding="utf-8"))
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


def _write_private_json(path: Path, payload: Any) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:  # removed by a concurrent prune
        return 0.0


def _prune_scans() -> None:
    files = sorted(_scans_dir().glob("*.json"), key=_mtime, reverse=True)
    for old in files[SCANS_KEPT:]:
        for f in (old, _meta_file(old)):
            try:
                f.unlink()
            except OSError:
                pass


# --- where a scan may look -----------------------------------------------------

def _session_cwd() -> Path:
    """The session's working folder, as Hermes itself resolves it (per-session pin,
    then the active profile's terminal folder, then the launch folder)."""
    try:
        try:
            from agent.runtime_cwd import resolve_agent_cwd
        except ImportError:
            term = (os.environ.get("TERMINAL_CWD") or "").strip()
            if term.lower() not in _CWD_SENTINELS and os.path.isabs(os.path.expanduser(term)):
                return Path(os.path.expanduser(term))
            return Path.cwd()
        return Path(resolve_agent_cwd())
    except OSError:
        raise ValueError("the session's working folder no longer exists; set scan_root") from None


def _root() -> Path:
    raw = str(_cfg("scan_root") or "").strip()
    root = Path(os.path.expanduser(raw)) if raw else _session_cwd()
    if not root.is_absolute():
        raise ValueError("scan_root must be an absolute path")
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"scan root {root} is not a folder")
    return root


def _project(path: Any) -> Path:
    """Resolve *path* inside the scan root, or refuse before touching it."""
    if path is not None and not isinstance(path, str):
        raise ValueError("path must be a string")
    root = _root()
    raw = (path or "").strip() or "."
    if "\x00" in raw:
        raise ValueError("path contains a NUL byte")
    candidate = Path(os.path.expanduser(raw))
    try:
        target = (candidate if candidate.is_absolute() else root / candidate).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"{raw} is outside the scan root {root}; set scan_root to widen it")
        is_dir = target.is_dir()
    except (OSError, RuntimeError) as exc:  # symlink loop, name too long
        raise ValueError(f"cannot open {raw[:80]}: {type(exc).__name__}") from None
    if not is_dir:
        raise ValueError(f"{raw} is not a folder")
    return target


def _on_gateway() -> bool:
    """True when this turn arrives over a human messaging surface (fails closed)."""
    try:
        from gateway.session_context import session_is_messaging_surface
    except ImportError:
        idents = (
            os.environ.get("HERMES_PLATFORM") or os.environ.get("HERMES_SESSION_PLATFORM") or "",
            os.environ.get("HERMES_SESSION_SOURCE") or "",
        )
        explicit = [str(v).strip().lower() for v in idents if str(v).strip()]
        return not explicit or any(v not in _NON_MESSAGING for v in explicit)
    try:
        return bool(session_is_messaging_surface())
    except Exception:
        logger.debug("checkyourself: session identity lookup failed; failing closed", exc_info=True)
        return True


# --- the CLI -------------------------------------------------------------------

_ENV_ALLOW = ("PATH", "HOME", "USER", "LANG", "LC_ALL", "TMPDIR", "TMP", "TEMP", "SYSTEMROOT")


def _child_env(root: Path) -> Dict[str, str]:
    """The CLI gets a minimal environment: no keys, tokens or other settings."""
    env = {k: os.environ[k] for k in _ENV_ALLOW if os.environ.get(k)}
    env["CHECKYOURSELF_SCAN_ROOT"] = str(root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_COLOR"] = "1"
    return env


def _kill(proc: "subprocess.Popen[bytes]") -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except (ProcessLookupError, PermissionError, OSError):
                break
            try:
                proc.wait(timeout=_KILL_GRACE)
                break
            except subprocess.TimeoutExpired:
                continue
    try:
        proc.kill()
    except Exception:
        pass
    try:
        proc.wait(timeout=2.0)
    except Exception:
        pass


def _vendor_problem() -> Optional[str]:
    """None when every vendored file matches vendor/MANIFEST.json, else what is wrong.

    The CLI runs with this Python, so a changed copy must not run silently."""
    try:
        manifest = json.loads(VENDOR_MANIFEST.read_text(encoding="utf-8"))
        files = manifest["files"]
    except Exception:
        return "vendor/MANIFEST.json is missing or unreadable; reinstall the plugin"
    base = VENDOR_MANIFEST.parent
    for rel, want in files.items():
        f = (base / rel).resolve()
        if base.resolve() not in f.parents or not f.is_file():
            return f"vendored file {rel} is missing; reinstall the plugin"
        if hashlib.sha256(f.read_bytes()).hexdigest() != want:
            return f"vendored file {rel} has changed since release; reinstall the plugin"
    return None


def run_cli(args: List[str], root: Path) -> Dict[str, Any]:
    """Run the vendored CLI and parse its JSON stdout."""
    problem = _vendor_problem()
    if problem:
        return {"ok": False, "error": problem}
    cmd = [sys.executable, "-I", str(CLI_PATH)] + args
    kw: Dict[str, Any] = {}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        kw["start_new_session"] = True
    timeout = _int_cfg("timeout_seconds", 5, 900)
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(root), env=_child_env(root), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw,
        )
    except OSError as exc:
        return {"ok": False, "error": f"could not start the CheckYourself CLI: {exc}"}
    out_buf, err_buf = _CappedReader(proc.stdout, STDOUT_MAX), _CappedReader(proc.stderr, STDERR_MAX)
    deadline = time.monotonic() + timeout
    while proc.poll() is None:
        if out_buf.over:
            _kill(proc)
            return {"ok": False, "error": f"CheckYourself output was larger than {STDOUT_MAX // (1024 * 1024)} MB; scan a smaller folder"}
        if time.monotonic() >= deadline:
            _kill(proc)
            return {"ok": False, "error": f"CheckYourself did not finish within {timeout}s; raise timeout_seconds or scan a smaller folder"}
        time.sleep(0.05)
    out_buf.join(2.0)
    err_buf.join(2.0)
    if out_buf.over:
        return {"ok": False, "error": f"CheckYourself output was larger than {STDOUT_MAX // (1024 * 1024)} MB; scan a smaller folder"}
    text = bytes(out_buf.data).decode("utf-8", "replace").strip()
    err_tail = bytes(err_buf.data).decode("utf-8", "replace").strip().splitlines()[-1:]
    try:
        data = json.loads(text) if text else None
    except (json.JSONDecodeError, RecursionError):
        data = None
    if isinstance(data, dict) and isinstance(data.get("error"), str) and set(data) <= {"error", "code"}:
        return {"ok": False, "error": f"CheckYourself refused: {data['error'][:300]}"}
    if proc.returncode != 0:
        why = err_tail[0][:300] if err_tail else f"exit {proc.returncode}"
        return {"ok": False, "error": f"CheckYourself failed (exit {proc.returncode}: {why})"}
    if not isinstance(data, dict):
        why = err_tail[0][:300] if err_tail else "empty output"
        return {"ok": False, "error": f"CheckYourself returned no JSON ({why})"}
    return {"ok": True, "data": data}


class _CappedReader:
    """Drain a pipe on a thread, keeping at most `cap` bytes, so a runaway child
    can't make this process buffer more than the cap before we notice."""

    def __init__(self, pipe: Any, cap: int):
        self.data, self.over, self._cap, self._pipe = bytearray(), False, cap, pipe
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self) -> None:
        try:
            while True:
                chunk = self._pipe.read1(65536) if hasattr(self._pipe, "read1") else self._pipe.read(65536)
                if not chunk:
                    break
                if len(self.data) + len(chunk) > self._cap:
                    self.over = True
                    continue  # keep draining so the child never blocks on a full pipe
                self.data += chunk
        except Exception:
            pass
        finally:
            try:
                self._pipe.close()
            except Exception:
                pass

    def join(self, timeout: float) -> None:
        self._t.join(timeout)


# --- operations ------------------------------------------------------------------

def _summarize_findings(findings: List[Any]) -> List[Dict[str, Any]]:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    rows = [f for f in findings if isinstance(f, dict)]
    rows.sort(key=lambda f: (order.get(str(f.get("severity")), 9), str(f.get("id", ""))))
    out = []
    for f in rows[:TOP_FINDINGS]:
        ev = f.get("evidence") if isinstance(f.get("evidence"), list) else []
        out.append({
            "id": f.get("id"),
            "severity": f.get("severity"),
            "title": f.get("title"),
            "evidence": [str(e)[:240] for e in ev[:2]],
            "fix": f.get("recommended_fix"),
            "status": f.get("status") or "open",
            **({"suppression": f["suppression"]} if isinstance(f.get("suppression"), dict) else {}),
        })
    return out


def scan(path: Any = None, deep: Any = False) -> Dict[str, Any]:
    if not isinstance(deep, bool):
        raise ValueError("deep must be true or false")
    project = _project(path)
    root = _root()
    args = ["scan", str(project), "--format", "json", "--no-write", "--quiet",
            "--max-files", str(_int_cfg("max_files", 100, 50_000))]
    if deep:
        args.append("--deep")
    res = run_cli(args, root)
    if not res["ok"]:
        return res
    data = res["data"]
    findings = data.get("findings") if isinstance(data.get("findings"), list) else []
    with _LOCK:
        store = _scan_file(project)
        _write_private_json(store, data)
        _write_private_json(_meta_file(store), {"project": str(project), "scanned_at": time.time(), "deep": deep})
        _prune_scans()
        # Score this run's own findings, not whatever a concurrent scan of the
        # same project wrote to the shared store a moment later.
        fd, snap = tempfile.mkstemp(prefix=".score.", suffix=".snap", dir=str(store.parent))
        os.close(fd)
        _write_private_json(Path(snap), data)
    try:
        est = run_cli(["score", "--findings", snap, "--format", "json", "--no-history"], root)
    finally:
        try:
            os.unlink(snap)
        except OSError:
            pass
    score: Dict[str, Any] = {"error": est.get("error")}
    if est["ok"]:
        s = est["data"]
        score = {
            "value": s.get("score"),
            "mode": s.get("score_mode"),
            "confidence": s.get("confidence"),
            "caps": [c.get("reason") for c in s.get("caps_applied") or [] if isinstance(c, dict)],
        }
    limits = data.get("scan_limits") if isinstance(data.get("scan_limits"), dict) else {}
    return {
        "ok": True,
        "project": project.name or str(project),
        "deep": deep,
        "files_scanned": data.get("files_scanned"),
        "truncated": bool(limits.get("truncated")),
        "incomplete": bool(limits.get("incomplete")),
        "skipped": {k: limits.get(k, 0) for k in _LIMIT_KEYS if limits.get(k)},
        "counts": data.get("counts"),
        "finding_count": len(findings),
        "findings_shown": min(len(findings), TOP_FINDINGS),
        "findings": _summarize_findings(findings),
        "score": score,
        "reading": (
            "No findings means Unknown, not a pass: the scan only sees what files show."
            if not findings else
            "Findings are evidence to re-check, not a verdict. Fix nothing without the user's yes."
        ),
        "next": "checkyourself_next ranks what to fix first from this scan.",
    }


def next_batch(path: Any = None) -> Dict[str, Any]:
    project = _project(path)
    store = _scan_file(project)
    if not store.is_file():
        return {"ok": False, "error": f"no scan for {project.name or project} yet; run checkyourself_scan first"}
    res = run_cli(["next", "--findings", str(store), "--format", "json"], _root())
    if not res["ok"]:
        return res
    data = res["data"]
    batch = data.get("highest_severity_batch") if isinstance(data.get("highest_severity_batch"), list) else []
    try:
        age: Optional[int] = int(time.time() - float(_read_meta(store).get("scanned_at")))
    except (TypeError, ValueError):
        age = None
    return {
        "ok": True,
        "project": project.name or str(project),
        "scan_age_seconds": age,
        "batch": [
            {k: item.get(k) for k in ("finding_id", "severity", "fix_summary", "verification", "rollback")}
            for item in batch if isinstance(item, dict)
        ],
        "reading": "This is ordering, not a safety review. Check dependencies and blast radius, then ask before fixing.",
    }


def status() -> Dict[str, Any]:
    try:
        root = str(_root())
    except (ValueError, OSError) as exc:
        root = f"invalid: {exc}"
    scans = []
    for f in sorted(_scans_dir().glob("*.json"), key=_mtime, reverse=True)[:5]:
        try:
            body = json.loads(f.read_text(encoding="utf-8"))
            meta = _read_meta(f)
            scans.append({
                "project": Path(str(meta.get("project", ""))).name or "?",
                "findings": len(body.get("findings") or []),
                "age_seconds": int(time.time() - float(meta.get("scanned_at", f.stat().st_mtime))),
            })
        except Exception:
            continue
    return {"ok": True, "cli_version": CLI_VERSION, "scan_root": root, "recent_scans": scans}


# --- hook ----------------------------------------------------------------------

def _message_text(msg: Any) -> str:
    """Plain text from a string or a multimodal list of parts."""
    if isinstance(msg, str):
        return msg
    if isinstance(msg, list):
        parts = []
        for part in msg:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "\n".join(parts)
    return ""


def _on_pre_llm(user_message: Any = "", **_: Any) -> Optional[Dict[str, str]]:
    try:
        if _bool_cfg("inject_on_ship_talk") and _SHIP_RE.search(_message_text(user_message)):
            return {"context": _BRIEF}
    except Exception:
        logger.debug("checkyourself: pre_llm_call failed", exc_info=True)
    return None


# --- tools ---------------------------------------------------------------------

SCAN_SCHEMA = {
    "name": "checkyourself_scan",
    "description": (
        "Scan a project folder for launch risks before calling work done: secrets in files, "
        "missing tests or CI, a missing lockfile, debug mode, open CORS, default credentials. Reads files only "
        "and never runs project code. Returns the top findings by severity and a score estimate. "
        "No findings means Unknown, not a pass."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Project folder, relative to the scan root (the session's working folder unless scan_root is set). Absolute paths outside it are refused. Default: the scan root itself."},
            "deep": {"type": "boolean", "description": "Also check CI workflow files and supply-chain details (slower).", "default": False},
        },
        "additionalProperties": False,
    },
}

NEXT_SCHEMA = {
    "name": "checkyourself_next",
    "description": (
        "From the last checkyourself_scan of a project, return the next batch to fix, highest "
        "severity first, each with how to verify and roll back. Ordering only, not a safety review."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The same project folder you scanned, relative to the scan root."},
        },
        "additionalProperties": False,
    },
}


def _wrap(fn):
    def handler(args: Optional[Dict[str, Any]] = None, **_: Any) -> str:
        try:
            if args is not None and not isinstance(args, dict):
                raise ValueError("arguments must be an object")
            out = fn(args or {})
        except ValueError as exc:
            out = {"ok": False, "error": str(exc)}
        except Exception as exc:  # never crash the agent loop
            logger.debug("checkyourself tool failed", exc_info=True)
            out = {"ok": False, "error": f"CheckYourself hit an unexpected {type(exc).__name__}; see the Hermes log"}
        raw = json.dumps(out, ensure_ascii=False)
        if len(raw) <= TOOL_JSON_MAX:
            return raw
        return json.dumps({"ok": False, "error": f"result is {len(raw)} characters, over {TOOL_JSON_MAX}; scan a smaller folder"})
    return handler


def _known(args: Dict[str, Any], allowed: set) -> Dict[str, Any]:
    extra = sorted(set(args) - allowed)
    if extra:
        raise ValueError(f"unknown argument(s): {', '.join(extra)}")
    return args


_tool_scan = _wrap(lambda a: scan(**_known(a, {"path", "deep"})))
_tool_next = _wrap(lambda a: next_batch(**_known(a, {"path"})))


# --- slash -----------------------------------------------------------------------

_HELP = (
    "Usage:\n"
    "  /checkyourself scan [folder] [--deep]   Scan a project inside the scan root\n"
    "  /checkyourself next [folder]            What to fix first, from the last scan\n"
    "  /checkyourself status                   Scan root and recent scans\n"
    "Reads files only; never runs project code. No findings means Unknown, not a pass."
)


def _fmt_scan(res: Dict[str, Any]) -> str:
    if not res.get("ok"):
        return f"CheckYourself: {res.get('error')}"
    c = res.get("counts") or {}
    sc = res.get("score") or {}
    lines = [
        f"{res['project']}: {res['finding_count']} finding(s) in {res.get('files_scanned')} files"
        + (" (incomplete scan)" if res.get("incomplete") or res.get("truncated") else ""),
        "  " + "  ".join(f"{k} {c.get(k, 0)}" for k in ("P0", "P1", "P2", "P3")),
    ]
    if sc.get("value") is not None:
        lines.append(f"  Score estimate {sc['value']}/100, {sc.get('confidence')} confidence (no coverage evidence yet)")
    if res.get("skipped"):
        lines.append("  Not fully read: " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in res["skipped"].items()))
    for f in res.get("findings") or []:
        mark = f" ({f['status']})" if f.get("status") not in (None, "open") else ""
        lines.append(f"  [{f.get('severity')}] {f.get('id')}: {f.get('title')}{mark}")
    if res.get("finding_count", 0) > res.get("findings_shown", 0):
        lines.append(f"  Showing {res['findings_shown']} of {res['finding_count']}, highest severity first.")
    lines.append(res["reading"])
    return "\n".join(lines)


def _fmt_next(res: Dict[str, Any]) -> str:
    if not res.get("ok"):
        return f"CheckYourself: {res.get('error')}"
    if not res["batch"]:
        return f"{res['project']}: nothing open in the last scan. That is Unknown, not a pass."
    lines = [f"{res['project']}: fix next (from the scan {_ago(res.get('scan_age_seconds'))})"]
    for b in res["batch"]:
        lines.append(f"  [{b.get('severity')}] {b.get('finding_id')}: {b.get('fix_summary')}")
        lines.append(f"      verify: {b.get('verification')}")
        if b.get("rollback"):
            lines.append(f"      roll back: {b['rollback']}")
    lines.append(res["reading"])
    return "\n".join(lines)


def _clip(text: str) -> str:
    if len(text) <= SLASH_DISPLAY:
        return text
    return text[:SLASH_DISPLAY].rsplit("\n", 1)[0] + "\n… cut for length. Ask the agent to run the scan for the full list."


def _messaging(platform: Any) -> bool:
    """Whether this slash call came over a chat platform. Hermes passes the
    platform name to handlers that ask for it, which also works when the plugin
    runs in its own host process; the session lookup is the fallback."""
    if isinstance(platform, str) and platform.strip():
        return platform.strip().lower() not in _NON_MESSAGING
    return _on_gateway()


def _redact(text: str) -> str:
    """Absolute paths of this machine shortened to their last part, for chat replies."""
    for raw in {str(Path.home()), os.environ.get("HERMES_HOME") or "", _safe_root_str()}:
        if raw and len(raw) > 1:
            text = text.replace(raw, "~" if raw == str(Path.home()) else f"…/{Path(raw).name}")
    return re.sub(r"(?<![\w~.:/])/(?:[\w.-]+/)+([\w.-]+)", r"…/\1", text)


def _safe_root_str() -> str:
    try:
        return str(_root())
    except Exception:
        return ""


def _ago(seconds: Any) -> str:
    try:
        s = max(0, int(seconds))
    except (TypeError, ValueError):
        return "at an unknown time"
    for unit, size in (("d", 86400), ("h", 3600), ("min", 60)):
        if s >= size:
            return f"{s // size} {unit} ago"
    return "just now"


def _slash(raw_args: str, platform: Any = None, **_: Any) -> str:
    try:
        out = _slash_inner(raw_args, platform)
    except Exception as exc:  # a slash command must always answer, never raise
        logger.debug("checkyourself slash failed", exc_info=True)
        out = f"CheckYourself hit an unexpected {type(exc).__name__}; see the Hermes log."
    try:
        return _redact(out) if _messaging(platform) else out
    except Exception:
        return out


def _slash_inner(raw_args: str, platform: Any = None) -> str:
    if not isinstance(raw_args, str):
        raw_args = ""
    try:
        parts = shlex.split(raw_args)
    except ValueError:  # unbalanced quotes
        parts = raw_args.split()
    if not parts or parts[0].lower() in {"help", "-h", "--help"}:
        return _HELP
    cmd, rest = parts[0].lower(), parts[1:]
    if any(p.lower() in {"-h", "--help", "help"} for p in rest):
        return _HELP
    try:
        if cmd == "status":
            s = status()
            lines = [f"CheckYourself {s['cli_version']}, scan root {s['scan_root']}"]
            lines += [f"  {r['project']}: {r['findings']} finding(s), {_ago(r['age_seconds'])}" for r in s["recent_scans"]]
            return "\n".join(lines)
        if cmd in {"scan", "next"}:
            if _messaging(platform) and not _bool_cfg("allow_slash_scan_on_gateway"):
                return ("/checkyourself scan and next are off on chat platforms, because they read this "
                        "machine's files. Ask the agent, or set allow_slash_scan_on_gateway: true.")
            deep = any(p.lower() == "--deep" for p in rest)
            folder = " ".join(p for p in rest if p.lower() != "--deep") or None
            if cmd == "scan":
                return _clip(_fmt_scan(scan(folder, deep)))
            if deep:
                return "--deep belongs to scan.\n\n" + _HELP
            return _clip(_fmt_next(next_batch(folder)))
    except ValueError as exc:
        return f"CheckYourself: {exc}"
    return f"Unknown subcommand `{cmd}`.\n\n{_HELP}"


# --- register --------------------------------------------------------------------

def _skill_description(skill_md: Path) -> str:
    """The description from SKILL.md's frontmatter (plain or folded), for the skill list."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    lines = text.split("---", 2)[1].splitlines()
    for i, line in enumerate(lines):
        if line.startswith("description:"):
            value = line.split(":", 1)[1].strip()
            if value in (">", ">-", "|", "|-"):
                folded = []
                for nxt in lines[i + 1:]:
                    if nxt and not nxt[0].isspace():
                        break
                    folded.append(nxt.strip())
                value = " ".join(x for x in folded if x)
            return value.strip("'\"")
    return ""


def register(ctx) -> None:
    global _ctx
    _ctx = ctx
    ctx.register_hook("pre_llm_call", _on_pre_llm)
    ctx.register_command(
        "checkyourself",
        handler=_slash,
        description="Check a project before calling it done (scan, next, status).",
        args_hint="scan [folder] [--deep] | next [folder] | status",
    )
    for schema, handler, emoji in ((SCAN_SCHEMA, _tool_scan, "🔍"), (NEXT_SCHEMA, _tool_next, "📋")):
        ctx.register_tool(
            name=schema["name"],
            toolset=PLUGIN_NAME,
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
                    ctx.register_skill(child.name, skill_md, description=_skill_description(skill_md))
                except Exception:
                    logger.debug("checkyourself: register_skill failed for %s", child.name, exc_info=True)
