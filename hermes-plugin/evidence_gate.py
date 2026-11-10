"""Operator-approved test evidence gate for Hermes ``kanban_complete``.

Trust model (see README): the operator approves one S11 test command per project
prefix with ``hermes evidence-gate approve``. The approval, its HMAC key and every
verdict live in this profile's plugin-data directory, never in the project. The
agent runs ``checkyourself_evidence_check``; Hermes asks a human (or the operator's
``command_allowlist``) before it executes anything. The completion hook executes
nothing: it only checks a signed verdict against the task, workspace, approval and
current tree fingerprint.
"""

from __future__ import annotations

import enum
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path(__file__).resolve().parent
ENGINE = PLUGIN_DIR / "tools" / "checkyourself.py"
TOOL_NAME = "checkyourself_evidence_check"
RULE_PREFIX = "checkyourself-evidence-check"
DEFAULTS = {"max_run_s": 120, "hook_budget_s": 10, "max_attempts": 5, "ignore": [".git"]}
PINNED_ENV = ("PATH", "HOME", "LANG", "LC_ALL")
FIXED_ENV = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTEST_ADDOPTS": "-p no:cacheprovider"}
MAX_ENTRIES = 200_000
KILL_GRACE_S = 2.0
OUTPUT_TAIL = 4000


class State(str, enum.Enum):
    INERT_UNCONFIGURED = "INERT_UNCONFIGURED"
    NOT_ENROLLED = "NOT_ENROLLED"
    NO_TASK = "NO_TASK"
    WORKSPACE_UNRESOLVED = "WORKSPACE_UNRESOLVED"
    NO_VERDICT = "NO_VERDICT"
    VERDICT_TAMPERED = "VERDICT_TAMPERED"
    APPROVAL_CHANGED = "APPROVAL_CHANGED"
    STALE_TREE = "STALE_TREE"
    TESTS_FAILED = "TESTS_FAILED"
    TIMEOUT = "TIMEOUT"
    FINDINGS_BLOCK = "FINDINGS_BLOCK"
    TREE_CHANGED_DURING_RUN = "TREE_CHANGED_DURING_RUN"
    FINGERPRINT_TIMEOUT = "FINGERPRINT_TIMEOUT"
    CONFIG_INVALID = "CONFIG_INVALID"
    RUN_ERROR = "RUN_ERROR"
    RETRY_CAP_REACHED = "RETRY_CAP_REACHED"
    ALLOWED = "ALLOWED"


ALLOWING = {State.INERT_UNCONFIGURED, State.NOT_ENROLLED, State.ALLOWED}
OPERATOR_FAULTS = {
    State.WORKSPACE_UNRESOLVED, State.VERDICT_TAMPERED, State.APPROVAL_CHANGED, State.FINGERPRINT_TIMEOUT,
    State.CONFIG_INVALID, State.RETRY_CAP_REACHED,
}
ADVICE = {
    State.NO_TASK: "name the kanban task_id (or run as a dispatcher worker).",
    State.NO_VERDICT: "run checkyourself_evidence_check for this task, then retry.",
    State.STALE_TREE: "files changed after the passing check; run checkyourself_evidence_check again.",
    State.TESTS_FAILED: "fix the failing tests, then run checkyourself_evidence_check again.",
    State.TIMEOUT: "the approved test command exceeded its time limit; speed it up or ask the operator.",
    State.FINDINGS_BLOCK: "resolve the P0/P1 findings (operator may accept specific ids), then re-check.",
    State.TREE_CHANGED_DURING_RUN: "do not edit files while the check runs; run it again.",
    State.RUN_ERROR: "the approved command could not run; see detail, retry or ask the operator.",
    State.WORKSPACE_UNRESOLVED: "operator: check the task's workspace on the board.",
    State.VERDICT_TAMPERED: "operator: a verdict failed integrity checks; inspect plugin-data, then reset.",
    State.APPROVAL_CHANGED: "operator: the project's S11 or approved executable changed; review and re-approve.",
    State.FINGERPRINT_TIMEOUT: "operator: workspace too large for the hook budget; add ignores or raise it.",
    State.CONFIG_INVALID: "operator: fix the evidence-gate approval or project S11 config.",
    State.RETRY_CAP_REACHED: "operator: inspect the failures, then `hermes evidence-gate reset TASK`.",
}


class GateError(Exception):
    def __init__(self, state: State, detail: str = ""):
        super().__init__(detail or state.value)
        self.state = state
        self.detail = detail


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --- operator store (profile plugin-data, outside every project) -------------------------------


class Store:
    def __init__(self, data_dir):
        self.dir = Path(data_dir)

    @property
    def key_path(self) -> Path:
        return self.dir / "key"

    @property
    def approvals_path(self) -> Path:
        return self.dir / "approvals.json"

    def configured(self) -> bool:
        return self.key_path.exists()

    def _key(self, create: bool = False) -> bytes:
        if create and not self.key_path.exists():
            self.dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "w") as handle:
                    handle.write(secrets.token_hex(32))
        raw = self.key_path.read_text().strip()
        if not re.fullmatch(r"[0-9a-f]{64}", raw):
            raise GateError(State.CONFIG_INVALID, "evidence-gate key is malformed")
        return bytes.fromhex(raw)

    def mac(self, body) -> str:
        return hmac.new(self._key(), canonical(body), hashlib.sha256).hexdigest()

    def write_signed(self, path: Path, body: dict, create_key: bool = False) -> None:
        self._key(create=create_key)
        record = dict(body, mac=self.mac(body))
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = path.with_name(path.name + ".%d.tmp" % os.getpid())
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(record, handle, sort_keys=True, indent=1)
        os.replace(tmp, path)

    def read_signed(self, path: Path):
        try:
            record = json.loads(path.read_text())
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            raise GateError(State.VERDICT_TAMPERED, "unreadable signed record %s" % path.name) from exc
        if not isinstance(record, dict) or not isinstance(record.get("mac"), str):
            raise GateError(State.VERDICT_TAMPERED, "unsigned record %s" % path.name)
        body = {k: v for k, v in record.items() if k != "mac"}
        if not hmac.compare_digest(record["mac"], self.mac(body)):
            raise GateError(State.VERDICT_TAMPERED, "signature mismatch on %s" % path.name)
        return body

    def approvals(self) -> dict:
        try:
            body = self.read_signed(self.approvals_path)
        except GateError as exc:
            raise GateError(State.CONFIG_INVALID, "approvals.json failed integrity check") from exc
        if body is None:
            raise GateError(State.CONFIG_INVALID, "key exists but approvals.json is missing")
        approvals = body.get("approvals")
        if not isinstance(approvals, dict):
            raise GateError(State.CONFIG_INVALID, "approvals.json has no approvals map")
        return approvals

    def save_approvals(self, approvals: dict) -> None:
        self.write_signed(self.approvals_path, {"v": 1, "approvals": approvals}, create_key=True)

    def verdict_path(self, binding: str) -> Path:
        return self.dir / "verdicts" / (hashlib.sha256(binding.encode()).hexdigest()[:32] + ".json")

    def lock(self, binding: str):
        import fcntl
        path = self.dir / "locks" / (hashlib.sha256(binding.encode()).hexdigest()[:32] + ".lock")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        handle = open(path, "w")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise GateError(State.RUN_ERROR, "another evidence check is already running for this task")
        return handle


# --- approvals ---------------------------------------------------------------------------------


def read_project_s11(root: Path) -> dict:
    path = root / ".checkyourself" / "challenges.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        s11 = data["challenges"]["S11"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise GateError(State.CONFIG_INVALID, "project has no readable S11 in .checkyourself/challenges.json") from exc
    command = s11.get("command") if isinstance(s11, dict) else None
    if not (isinstance(command, list) and command and all(isinstance(a, str) and a for a in command)):
        raise GateError(State.CONFIG_INVALID, "S11 command must be a non-empty argv list")
    success = s11.get("success") or {}
    if not isinstance(success, dict) or set(success) - {"exit_zero", "regex_match"}:
        raise GateError(State.CONFIG_INVALID, "S11 success supports only exit_zero and regex_match")
    regex = success.get("regex_match")
    if regex is not None:
        re.compile(regex)
    timeout = s11.get("timeout_s", DEFAULTS["max_run_s"])
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise GateError(State.CONFIG_INVALID, "S11 timeout_s must be positive")
    cwd = s11.get("cwd") or "."
    if not isinstance(cwd, str):
        raise GateError(State.CONFIG_INVALID, "S11 cwd must be a string")
    return {"command": command, "cwd": cwd, "timeout_s": timeout,
            "exit_zero": success.get("exit_zero", True) is not False, "regex_match": regex}


def resolve_exe(argv0: str, env: dict, cwd: Path):
    if "/" in argv0:
        candidate = (cwd / argv0) if not os.path.isabs(argv0) else Path(argv0)
        found = str(candidate) if os.access(candidate, os.X_OK) and candidate.is_file() else None
    else:
        found = shutil.which(argv0, path=env.get("PATH", ""))
    if not found:
        raise GateError(State.CONFIG_INVALID, "S11 executable %r not found on the pinned PATH" % argv0)
    return os.path.abspath(found)


def build_approval(project: Path, prefix: Path, environ: dict, max_run_s=None, ignore=None,
                   accept_findings=None, max_attempts=None) -> dict:
    root = project.resolve(strict=True)
    prefix = prefix.resolve(strict=True)
    if not root.is_dir() or not (root == prefix or root.is_relative_to(prefix)):
        raise GateError(State.CONFIG_INVALID, "project must be a directory at or under prefix")
    ignore = list(DEFAULTS["ignore"]) + list(ignore or [])
    for item in ignore:
        if not item or os.path.isabs(item) or ".." in Path(item).parts:
            raise GateError(State.CONFIG_INVALID, "ignore entries must be relative paths inside the project")
    s11 = read_project_s11(root)
    env = {k: environ[k] for k in PINNED_ENV if environ.get(k)}
    env.update(FIXED_ENV)
    exe = resolve_exe(s11["command"][0], env, root)
    approval = {
        "v": 1,
        "prefix": str(prefix),
        "s11": s11,
        "env": env,
        "exe": {"argv0": s11["command"][0], "path": exe, "sha256": sha256_file(Path(exe))},
        "max_run_s": int(max_run_s or DEFAULTS["max_run_s"]),
        "hook_budget_s": DEFAULTS["hook_budget_s"],
        "max_attempts": int(max_attempts or DEFAULTS["max_attempts"]),
        "ignore": sorted(set(ignore)),
        "accept_findings": sorted(set(accept_findings or [])),
    }
    approval["digest"] = hashlib.sha256(canonical(approval)).hexdigest()
    return approval


def match_approval(approvals: dict, workspace: Path):
    best = None
    for prefix, approval in approvals.items():
        p = Path(prefix)
        if workspace == p or workspace.is_relative_to(p):
            if best is None or len(prefix) > len(best["prefix"]):
                best = approval
    if best is not None:
        body = {k: v for k, v in best.items() if k != "digest"}
        if hashlib.sha256(canonical(body)).hexdigest() != best.get("digest"):
            raise GateError(State.CONFIG_INVALID, "approval digest mismatch")
    return best


def rule_key(approval: dict) -> str:
    return "%s:%s" % (RULE_PREFIX, approval["digest"][:16])


# --- task / workspace resolution ---------------------------------------------------------------


def resolve_task(args):
    args = args if isinstance(args, dict) else {}
    env_task = os.environ.get("HERMES_KANBAN_TASK", "").strip()
    task = args.get("task_id") or env_task
    if not isinstance(task, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", task or ""):
        raise GateError(State.NO_TASK, "no kanban task id")
    own = task == env_task
    board = (os.environ.get("HERMES_KANBAN_BOARD") if own else args.get("board")) or ""
    workspace = os.environ.get("HERMES_KANBAN_WORKSPACE") if own else None
    if not workspace:
        workspace = lookup_workspace(board or None, task)
    if not workspace:
        return task, board, None
    try:
        path = Path(workspace).resolve(strict=True)
    except OSError as exc:
        raise GateError(State.WORKSPACE_UNRESOLVED, "task workspace does not exist") from exc
    if not path.is_dir():
        raise GateError(State.WORKSPACE_UNRESOLVED, "task workspace is not a directory")
    return task, board, path


def lookup_workspace(board, task):
    """Read-only board lookup; never creates or migrates a board."""
    import sqlite3
    try:
        from hermes_cli import kanban_db
        db = Path(kanban_db.kanban_db_path(board=board))
    except Exception as exc:  # Hermes missing or board unknown
        raise GateError(State.WORKSPACE_UNRESOLVED, "cannot locate kanban board") from exc
    if not db.exists():
        raise GateError(State.WORKSPACE_UNRESOLVED, "kanban board database not found")
    try:
        conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            row = conn.execute("SELECT workspace_path FROM tasks WHERE id = ?", (task,)).fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise GateError(State.WORKSPACE_UNRESOLVED, "kanban board unreadable") from exc
    if row is None:
        raise GateError(State.WORKSPACE_UNRESOLVED, "task not found on board")
    return row[0]


# --- tree fingerprint --------------------------------------------------------------------------


def fingerprint(root: Path, ignore, deadline: float) -> str:
    """lstat every entry (content edits move ctime); follow nothing; bind out-of-tree link targets."""
    ignored = {root / p for p in ignore}
    digest = hashlib.sha256()
    stack = [root]
    count = 0

    def outside(target: Path) -> bool:
        return not target.is_relative_to(root) or any(target == i or target.is_relative_to(i) for i in ignored)

    while stack:
        directory = stack.pop()
        with os.scandir(directory) as it:
            entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            path = Path(entry.path)
            if path in ignored:
                continue
            count += 1
            if count % 256 == 0 and time.monotonic() > deadline:
                raise GateError(State.FINGERPRINT_TIMEOUT, "fingerprint exceeded budget")
            if count > MAX_ENTRIES:
                raise GateError(State.FINGERPRINT_TIMEOUT, "workspace has more than %d entries" % MAX_ENTRIES)
            st = entry.stat(follow_symlinks=False)
            rel = path.relative_to(root).as_posix()
            if entry.is_symlink():
                link = os.readlink(path)
                target = Path(os.path.realpath(path))
                extra = ""
                if outside(target):
                    if target.is_dir():
                        raise GateError(State.CONFIG_INVALID, "directory symlink %s leaves the workspace" % rel)
                    if target.exists():
                        t = target.stat()
                        extra = "%d:%d:%d:%d:%d" % (t.st_mode, t.st_size, t.st_mtime_ns, t.st_ctime_ns, t.st_ino)
                    else:
                        extra = "dangling"
                line = "L\0%s\0%s\0%s" % (rel, link, extra)
            elif entry.is_dir(follow_symlinks=False):
                line = "D\0%s\0%d\0%d" % (rel, st.st_mode, st.st_ino)
                stack.append(path)
            else:
                line = "F\0%s\0%d\0%d\0%d\0%d\0%d" % (
                    rel, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino)
            digest.update(line.encode("utf-8", "surrogateescape") + b"\n")
    return digest.hexdigest()


# --- execution ---------------------------------------------------------------------------------


def kill_group(pgid: int) -> None:
    for sig, grace in ((signal.SIGTERM, KILL_GRACE_S), (signal.SIGKILL, 0)):
        try:
            os.killpg(pgid, sig)
        except (ProcessLookupError, PermissionError):
            return
        end = time.monotonic() + grace
        while time.monotonic() < end:
            try:
                os.killpg(pgid, 0)
            except (ProcessLookupError, PermissionError):
                return
            time.sleep(0.05)


def run_group(argv, cwd, env, timeout):
    """Run in a fresh process group; on timeout or exit, terminate the whole group."""
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, start_new_session=True)
    timed_out = False
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_group(proc.pid)
        out, _ = proc.communicate()
    except BaseException:
        kill_group(proc.pid)
        proc.communicate()
        raise
    kill_group(proc.pid)  # reap leftovers that stayed in the group
    return proc.returncode, timed_out, out.decode("utf-8", "replace")


def run_s11(approval: dict, root: Path):
    s11 = approval["s11"]
    cwd = (root / s11["cwd"]).resolve()
    if not (cwd == root or cwd.is_relative_to(root)) or not cwd.is_dir():
        raise GateError(State.CONFIG_INVALID, "S11 cwd leaves the workspace")
    env = dict(approval["env"])
    exe = resolve_exe(s11["command"][0], env, cwd)
    if exe != approval["exe"]["path"] or sha256_file(Path(exe)) != approval["exe"]["sha256"]:
        raise GateError(State.APPROVAL_CHANGED, "approved executable %s changed" % approval["exe"]["argv0"])
    timeout = min(float(s11["timeout_s"]), float(approval["max_run_s"]))
    start = time.monotonic()
    code, timed_out, output = run_group([exe, *s11["command"][1:]], cwd, env, timeout)
    result = {"exit_code": code, "duration_s": round(time.monotonic() - start, 3), "output_tail": output[-OUTPUT_TAIL:]}
    if timed_out:
        return State.TIMEOUT, result
    if s11["exit_zero"] and code != 0:
        return State.TESTS_FAILED, result
    if s11["regex_match"] and not re.search(s11["regex_match"], output):
        return State.TESTS_FAILED, result
    return State.ALLOWED, result


def scan_blockers(root: Path, approval: dict):
    """P0/P1 findings from the bundled engine; project suppressions are ignored."""
    code, timed_out, output = run_group(
        [sys.executable, "-I", "-B", str(ENGINE), "scan", str(root), "--format", "json", "--no-write", "--quiet"],
        PLUGIN_DIR, {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}, 60)
    if timed_out or code != 0:
        raise GateError(State.RUN_ERROR, "finding scan failed (exit %s)" % code)
    data = json.loads(output)
    if (data.get("scan_limits") or {}).get("truncated"):
        return ["SCAN_TRUNCATED: scan hit its file limit; findings are incomplete"]
    accepted = set(approval["accept_findings"])
    return ["%s %s %s" % (f.get("severity"), f.get("id"), f.get("title", ""))
            for f in data.get("findings", [])
            if f.get("severity") in ("P0", "P1") and f.get("id") not in accepted]


# --- the two entry points ----------------------------------------------------------------------


class Gate:
    def __init__(self, data_dir_fn):
        self._data_dir_fn = data_dir_fn
        self._warned = False

    def store(self) -> Store:
        return Store(self._data_dir_fn())

    def context(self, store: Store, args):
        """Return (State, details) where details holds task/board/root/approval when enrolled."""
        if not store.configured():
            return State.INERT_UNCONFIGURED, {}
        approvals = store.approvals()
        if not approvals:
            return State.NOT_ENROLLED, {}
        task, board, root = resolve_task(args)
        if root is None:
            return State.NOT_ENROLLED, {"task": task}
        approval = match_approval(approvals, root)
        if approval is None:
            return State.NOT_ENROLLED, {"task": task}
        if read_project_s11(root) != approval["s11"]:
            raise GateError(State.APPROVAL_CHANGED, "project S11 differs from the operator-approved definition")
        return None, {"task": task, "board": board, "root": root, "approval": approval,
                      "binding": "%s:%s" % (board, task)}

    def completion(self, args):
        store = self.store()
        state, ctx = self.context(store, args)
        if state is not None:
            return state, ""
        verdict = store.read_signed(store.verdict_path(ctx["binding"]))
        if verdict is None:
            return State.NO_VERDICT, ""
        if verdict.get("binding") != ctx["binding"] or verdict.get("root") != str(ctx["root"]):
            raise GateError(State.VERDICT_TAMPERED, "verdict is bound to another task or workspace")
        if verdict.get("approval_digest") != ctx["approval"]["digest"]:
            raise GateError(State.APPROVAL_CHANGED, "verdict predates the current approval")
        if verdict.get("status") != State.ALLOWED.value:
            return State(verdict.get("status")), "last check: %s" % verdict.get("detail", "")
        deadline = time.monotonic() + ctx["approval"]["hook_budget_s"]
        if fingerprint(ctx["root"], ctx["approval"]["ignore"], deadline) != verdict.get("fingerprint"):
            return State.STALE_TREE, ""
        return State.ALLOWED, ""

    def check(self, args) -> dict:
        claim = args.get("claim") if isinstance(args, dict) else None
        if not isinstance(claim, str) or not claim.strip():
            raise GateError(State.CONFIG_INVALID, "claim must be a non-empty string")
        store = self.store()
        state, ctx = self.context(store, args)
        if state is not None:
            return {"state": state.value, "executed": False}
        approval, root, binding = ctx["approval"], ctx["root"], ctx["binding"]
        handle = store.lock(binding)
        try:
            path = store.verdict_path(binding)
            previous = store.read_signed(path)
            if previous and (previous.get("binding") != binding or previous.get("root") != str(root)):
                raise GateError(State.VERDICT_TAMPERED, "verdict is bound to another task or workspace")
            same = previous and previous.get("approval_digest") == approval["digest"]
            attempts = previous.get("attempts", 0) if same else 0
            budget = approval["max_run_s"]
            before = fingerprint(root, approval["ignore"], time.monotonic() + budget)
            if same and previous.get("status") == State.ALLOWED.value and previous.get("fingerprint") == before:
                return {"state": State.ALLOWED.value, "executed": False, "cached": True}
            if attempts >= approval["max_attempts"]:
                raise GateError(State.RETRY_CAP_REACHED, "%d checks used for this task" % attempts)
            attempts += 1
            try:
                status, result = run_s11(approval, root)
            except GateError as exc:
                status, result = exc.state, {"error": exc.detail}
            blockers = []
            after = before
            if status == State.ALLOWED:
                after = fingerprint(root, approval["ignore"], time.monotonic() + budget)
                if after != before:
                    status = State.TREE_CHANGED_DURING_RUN
            if status == State.ALLOWED:
                try:
                    blockers = scan_blockers(root, approval)
                except GateError as exc:
                    status, result = exc.state, dict(result, error=exc.detail)
            if status == State.ALLOWED:
                known = args.get("known_blockers") or []
                if not isinstance(known, list) or not all(isinstance(b, str) for b in known):
                    raise GateError(State.CONFIG_INVALID, "known_blockers must be a list of strings")
                blockers += ["reported: " + b for b in known]
                if blockers:
                    status = State.FINDINGS_BLOCK
            verdict = {
                "v": 1, "binding": binding, "task": ctx["task"], "root": str(root),
                "approval_digest": approval["digest"], "fingerprint": after, "status": status.value,
                "attempts": attempts, "claim": claim.strip()[:500], "blockers": blockers[:50],
                "detail": result.get("error", "exit %s" % result.get("exit_code")),
                "checked_at": int(time.time()),
            }
            store.write_signed(path, verdict)
            logger.info("evidence check %s for %s: %s (attempt %d)", root, binding, status.value, attempts)
            return {"state": status.value, "executed": True, "attempts": attempts,
                    "max_attempts": approval["max_attempts"], "blockers": blockers[:50], **result}
        finally:
            handle.close()

    # Hermes hook ------------------------------------------------------------------------------

    def pre_tool_call(self, tool_name=None, args=None, **kwargs):
        if tool_name == TOOL_NAME:
            return self.approve_directive(args)
        if tool_name != "kanban_complete":
            return None
        try:
            state, detail = self.completion(args)
        except GateError as exc:
            state, detail = exc.state, exc.detail
        except Exception:
            logger.exception("evidence gate failed")
            state, detail = State.RUN_ERROR, "internal error (see Hermes log)"
        if state == State.INERT_UNCONFIGURED and not self._warned:
            self._warned = True
            logger.warning("checkyourself evidence gate is enabled but unconfigured; completions are not gated. "
                           "Run `hermes evidence-gate approve PROJECT` to enroll a project.")
        if state in ALLOWING:
            return None
        return {"action": "block", "message": block_message(state, detail)}

    def approve_directive(self, args):
        try:
            state, ctx = self.context(self.store(), args)
        except GateError:
            return None  # the tool reports the state and executes nothing
        if state is not None:
            return None
        approval = ctx["approval"]
        message = "Run operator-approved S11 %s in %s (limit %ss). It executes project code with your OS authority." % (
            json.dumps(approval["s11"]["command"]), ctx["root"],
            min(approval["s11"]["timeout_s"], approval["max_run_s"]))
        return {"action": "approve", "message": message, "rule_key": rule_key(approval)}

    def tool(self, args, **kwargs) -> str:
        try:
            result = self.check(args if isinstance(args, dict) else {})
        except GateError as exc:
            result = {"state": exc.state.value, "executed": False, "detail": exc.detail}
        except Exception:
            logger.exception("evidence check failed")
            result = {"state": State.RUN_ERROR.value, "executed": False}
        state = State(result["state"])
        result["advice"] = ADVICE.get(state, "")
        result["completion_allowed_now"] = state in ALLOWING
        return json.dumps(result, allow_nan=False)


def block_message(state: State, detail: str = "") -> str:
    who = "Operator action needed" if state in OPERATOR_FAULTS else "Completion blocked"
    text = "%s [%s]: %s" % (who, state.value, ADVICE.get(state, ""))
    return text + (" (%s)" % detail if detail else "")


# --- operator CLI ------------------------------------------------------------------------------


def setup_cli(parser):
    sub = parser.add_subparsers(dest="evidence_gate_cmd", required=True)
    approve = sub.add_parser("approve", help="Preview, then approve, a project's S11 test command")
    approve.add_argument("project")
    approve.add_argument("--prefix", help="apply to task workspaces under this directory (default: project)")
    approve.add_argument("--max-run-s", type=int)
    approve.add_argument("--max-attempts", type=int)
    approve.add_argument("--ignore", action="append", help="relative path to leave out of the fingerprint")
    approve.add_argument("--accept-finding", action="append", help="finding id the operator accepts")
    approve.add_argument("--confirm", metavar="DIGEST", help="digest printed by the preview")
    status = sub.add_parser("status", help="Show approvals")
    status.add_argument("project", nargs="?")
    revoke = sub.add_parser("revoke", help="Remove the approval for a prefix")
    revoke.add_argument("prefix")
    reset = sub.add_parser("reset", help="Clear a task's verdict and retry count")
    reset.add_argument("task")
    reset.add_argument("--board", default="")


def run_cli(store: Store, args, environ=None) -> int:
    environ = os.environ if environ is None else environ
    cmd = args.evidence_gate_cmd
    if cmd in ("approve", "revoke", "reset") and environ.get("HERMES_KANBAN_TASK"):
        print("refused: run evidence-gate %s from an operator shell, not a kanban worker" % cmd)
        return 2
    try:
        approvals = store.approvals() if store.configured() else {}
        if cmd == "approve":
            approval = build_approval(Path(args.project), Path(args.prefix or args.project), environ,
                                      args.max_run_s, args.ignore, args.accept_finding, args.max_attempts)
            print(json.dumps(approval, indent=1, sort_keys=True))
            if args.confirm != approval["digest"]:
                print("\nReview the command and pinned environment above. To approve run again with\n"
                      "  --confirm %s\nHeadless workers also need this in config.yaml command_allowlist:\n"
                      "  plugin_rule:%s" % (approval["digest"], rule_key(approval)))
                return 1 if args.confirm else 0
            approvals[approval["prefix"]] = approval
            store.save_approvals(approvals)
            print("approved %s (rule plugin_rule:%s)" % (approval["prefix"], rule_key(approval)))
        elif cmd == "status":
            for prefix, approval in sorted(approvals.items()):
                if args.project and not Path(args.project).resolve().is_relative_to(Path(prefix)):
                    continue
                print("%s  %s  %s" % (prefix, approval["digest"][:16], json.dumps(approval["s11"]["command"])))
            if not store.configured():
                print("unconfigured: completions are not gated")
        elif cmd == "revoke":
            prefix = str(Path(args.prefix).resolve())
            if approvals.pop(prefix, None) is None:
                print("no approval for %s" % prefix)
                return 1
            store.save_approvals(approvals)
            print("revoked %s" % prefix)
        elif cmd == "reset":
            path = store.verdict_path("%s:%s" % (args.board, args.task))
            path.unlink(missing_ok=True)
            print("reset %s:%s" % (args.board, args.task))
        return 0
    except (GateError, OSError) as exc:
        print("error: %s" % exc)
        return 2


def register(ctx):
    def data_dir():
        return ctx.state.data_dir  # lazy: the validator probe has no real state

    gate = Gate(data_dir)
    ctx.register_tool(
        name=TOOL_NAME, toolset="checkyourself",
        schema={"name": TOOL_NAME, "description": (
            "Run the operator-approved S11 test command for this kanban task's workspace (Hermes asks for "
            "approval first), scan for P0/P1 findings, and record a signed verdict. kanban_complete is allowed "
            "only while that verdict passes and the workspace is unchanged."),
            "parameters": {"type": "object", "properties": {
                "claim": {"type": "string", "description": "What you believe is done."},
                "task_id": {"type": "string", "description": "Kanban task id; defaults to the worker's task."},
                "known_blockers": {"type": "array", "items": {"type": "string"},
                                   "description": "Problems you know about; any entry blocks completion."}},
                "required": ["claim"], "additionalProperties": False}},
        handler=gate.tool,
    )
    ctx.register_hook("pre_tool_call", gate.pre_tool_call)
    ctx.register_command("evidence-gate", lambda raw="": _status_text(gate), description="Show evidence-gate approvals")
    ctx.register_cli_command("evidence-gate", "Approve and inspect the CheckYourself evidence gate", setup_cli,
                             lambda args: sys.exit(run_cli(gate.store(), args)))


def _status_text(gate) -> str:
    try:
        store = gate.store()
        if not store.configured():
            return "Evidence gate unconfigured: completions are not gated."
        lines = ["%s  %s" % (p, a["digest"][:16]) for p, a in sorted(store.approvals().items())]
        return "\n".join(lines) or "No projects enrolled."
    except Exception as exc:
        return "Evidence gate status unavailable: %s" % exc
