"""Executing challenges, capturing output, and minting executed receipts."""

from __future__ import annotations

from pathlib import Path
import hashlib
import hmac
import json
import os
import re
import secrets
import signal
import stat
import subprocess
from typing import Any, List, Optional, Sequence, Tuple
from .challenge_config import (
    _challenge_artifact_paths,
    _challenge_config_digest,
    _challenge_patterns,
    _json_field_assertions,
    _json_path_value,
    load_challenge_config,
)
from .constants import (
    CHALLENGE_RESULT_SCHEMA_ID,
    CHALLENGE_SEMANTIC_CONTRACTS,
    COVERAGE_SURFACES,
    DEFAULT_CHALLENGE_OUTPUT_DIR,
    DEFAULT_LOCAL_INTEGRITY_BINDING_PATH,
    EXECUTED_RECEIPT_BINDING_FIELDS,
    IGNORED_DIRS,
    LEGACY_EXECUTED_RECEIPT_BINDING_FIELDS,
    LOCAL_INTEGRITY_HMAC_FIELD,
    LOCAL_INTEGRITY_KEY_BYTES,
    RECEIPT_ISSUER,
    SCORE_CATEGORIES,
    TEST_COUNT_RE,
    TOOL_NAME,
    _CLOCK_DURATION_RE,
    _DURATION_RE,
    _ISO_TIMESTAMP_RE,
    _TEMP_PATH_RE,
)
from .errors import CliError
from .jsonlite import strict_json_loads
from .output import safe_write_text
from .util import now_iso


def _challenge_tree_excluded(relative: Path) -> bool:
    parts = relative.parts
    if ".git" in parts or any(
        part in IGNORED_DIRS or part in {".codegraph", ".omx", ".omc", ".claude"} for part in parts
    ):
        return True
    if parts[:2] == (".checkyourself", "challenge-runs"):
        return True
    if relative.as_posix() == DEFAULT_LOCAL_INTEGRITY_BINDING_PATH:
        return True
    if parts and parts[0].startswith("_retrofit-"):
        return True
    if relative.name.startswith("CHECKYOURSELF_") and relative.name.endswith(".generated.json"):
        return True
    if relative.name in {"findings.json", "coverage.json", "score.json"}:
        return True
    return False


def current_tree_hash(root: Path) -> str:
    """Hash the current project tree, including dirty and untracked source."""
    root = root.resolve()
    digest = hashlib.sha256()
    files: List[Path] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in IGNORED_DIRS and name not in {".codegraph", ".omx", ".omc", ".claude"}
        )
        for name in sorted(filenames):
            path = Path(directory) / name
            relative = path.relative_to(root)
            if _challenge_tree_excluded(relative) or path.is_symlink():
                continue
            files.append(path)
    for path in sorted(files):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        try:
            content = path.read_bytes()
        except OSError as exc:
            content = f"<unreadable:{exc}>".encode("utf-8", "replace")
        digest.update(relative + b"\0" + hashlib.sha256(content).digest() + b"\0")
    return digest.hexdigest()


def _challenge_cwd(root: Path, definition: dict) -> Path:
    raw = str(definition.get("cwd") or ".")
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise CliError(f"challenge cwd escapes project root: {raw!r}") from exc
    if not candidate.is_dir():
        raise CliError(f"challenge cwd does not exist: {candidate}")
    return candidate


def _challenge_result(
    definition: dict,
    *,
    surface_id: Optional[str] = None,
    exit_code: Optional[int],
    stdout: str,
    stderr: str,
    timed_out: bool,
    execution_error: str,
    root: Optional[Path] = None,
) -> Tuple[str, List[str]]:
    """Evaluate committed assertions against verifier-captured subprocess output."""
    success = definition.get("success") or {"exit_zero": True}
    reasons: List[str] = []
    if timed_out:
        reasons.append("challenge timed out")
    if execution_error:
        reasons.append(execution_error)
    expected_zero = success.get("exit_zero", True)
    if expected_zero and exit_code != 0:
        reasons.append(f"exit code was {exit_code!r}, expected zero")
    if not expected_zero and exit_code == 0:
        reasons.append("exit code was zero, expected a non-zero result")
    contract = CHALLENGE_SEMANTIC_CONTRACTS.get(str(surface_id or definition.get("surface_id") or ""), {})
    combined = stdout + ("\n" if stdout and stderr else "") + stderr
    minimum_tokens = int(contract.get("minimum_output_tokens", 0) or 0)
    output_tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.:/+\-]*", combined)
    if len(output_tokens) < minimum_tokens:
        reasons.append(f"captured output has {len(output_tokens)} semantic tokens; minimum is {minimum_tokens}")
    output_kind = definition.get("output_kind", "text")
    parsed: Any = None
    if output_kind == "json" or success.get("json_field") is not None:
        try:
            parsed = strict_json_loads(stdout)
        except (ValueError, UnicodeError) as exc:
            reasons.append(f"stdout was not valid JSON: {exc}")
    for path, expected in _json_field_assertions(success.get("json_field")):
        found, actual = _json_path_value(parsed, path)
        if not found or actual != expected:
            reasons.append(f"JSON field {path!r} did not equal the configured expected value")
    for pattern in _challenge_patterns(success.get("regex_match")):
        if not re.search(pattern, combined):
            reasons.append(f"captured output did not match required regex {pattern!r}")
    patterns = success.get("regex_not_match", [])
    if isinstance(patterns, str):
        patterns = [patterns]
    for pattern in patterns or []:
        if re.search(pattern, combined):
            reasons.append(f"captured output matched forbidden regex {pattern!r}")
    if contract.get("requires_test_count") and not TEST_COUNT_RE.search(combined):
        reasons.append("captured output did not include a test pass-count result")
    artifact_paths = _challenge_artifact_paths(success.get("artifact"))
    if artifact_paths:
        if root is None:
            reasons.append("artifact assertion cannot be verified without a project root")
        else:
            root = root.resolve()
            for artifact_path in artifact_paths:
                candidate = root / artifact_path
                try:
                    resolved = candidate.resolve()
                    resolved.relative_to(root)
                except (OSError, RuntimeError, ValueError):
                    reasons.append(f"artifact path escapes the project root: {artifact_path!r}")
                    continue
                if candidate.is_symlink() or not candidate.is_file():
                    reasons.append(f"required artifact was not produced: {artifact_path}")
                else:
                    try:
                        if candidate.stat().st_size <= 0:
                            reasons.append(f"required artifact is empty: {artifact_path}")
                    except OSError as exc:
                        reasons.append(f"required artifact could not be inspected: {artifact_path}: {exc}")
    return ("PASS" if not reasons else "FAIL"), reasons


def _local_integrity_binding_path(root: Path) -> Path:
    return root.resolve() / DEFAULT_LOCAL_INTEGRITY_BINDING_PATH


def _load_local_integrity_binding_key(root: Path, *, create: bool) -> bytes:
    """Load the local integrity binding key, creating it with mode 0600 once.

    The key makes project-local receipt edits detectable. It does not prove
    independent issuance or operator identity because it lives in the project
    being inspected.
    """
    path = _local_integrity_binding_path(root)
    parent = path.parent
    if parent.is_symlink():
        raise CliError(f"local integrity binding key directory must not be a symlink: {parent}")
    if create:
        parent.mkdir(parents=True, exist_ok=True)
        if parent.is_symlink():
            raise CliError(f"local integrity binding key directory must not be a symlink: {parent}")
        if not path.exists():
            try:
                fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                try:
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(secrets.token_bytes(LOCAL_INTEGRITY_KEY_BYTES))
                except Exception:
                    try:
                        path.unlink()
                    except OSError:
                        pass
                    raise
    if path.is_symlink() or not path.is_file():
        raise CliError(f"local integrity binding key is missing or not a regular file: {path}")
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        raise CliError(f"local integrity binding key could not be inspected: {exc}") from exc
    if mode != 0o600:
        raise CliError(f"local integrity binding key must have mode 0600: {path}")
    try:
        key = path.read_bytes()
    except OSError as exc:
        raise CliError(f"local integrity binding key could not be read: {exc}") from exc
    if len(key) != LOCAL_INTEGRITY_KEY_BYTES:
        raise CliError(f"local integrity binding key must contain {LOCAL_INTEGRITY_KEY_BYTES} bytes: {path}")
    return key


def _executed_receipt_binding_bytes(receipt: dict) -> bytes:
    # Receipts minted before semantic re-execution existed have no semantic
    # field and must retain their original binding so they can be re-derived.
    fields = (
        EXECUTED_RECEIPT_BINDING_FIELDS
        if "semantic_output_digest" in receipt
        else LEGACY_EXECUTED_RECEIPT_BINDING_FIELDS
    )
    binding = {field: receipt.get(field) for field in fields}
    return json.dumps(
        binding,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _executed_receipt_binding_digest(receipt: dict) -> str:
    return hashlib.sha256(_executed_receipt_binding_bytes(receipt)).hexdigest()


def _executed_receipt_hmac(receipt: dict, binding_key: bytes) -> str:
    run_id = str(receipt.get("run_id") or "")
    run_key = hmac.new(
        binding_key,
        (RECEIPT_ISSUER + ":" + run_id).encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return hmac.new(run_key, _executed_receipt_binding_bytes(receipt), hashlib.sha256).hexdigest()


def _captured_output_payload(stdout: str, stderr: str) -> str:
    return json.dumps({"stdout": stdout, "stderr": stderr}, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _normalize_output_text(value: str, *, root: Optional[Path] = None) -> str:
    """Normalize only re-execution noise from one captured output stream.

    The contract is deliberately deterministic: remove carriage returns, replace
    durations, ISO-8601 timestamps, and absolute project/temp paths, then strip
    trailing whitespace from each line. All other content remains significant.
    """
    text = value.replace("\r", "")
    if root is not None:
        try:
            project_path = str(root.resolve())
        except (OSError, RuntimeError):
            project_path = str(root)
        if project_path:
            project_pattern = re.compile(re.escape(project_path) + r"(?:[/\\][^\s\"'<>]+)*")
            text = project_pattern.sub("<path>", text)
    text = _TEMP_PATH_RE.sub("<path>", text)
    text = _ISO_TIMESTAMP_RE.sub("<timestamp>", text)
    text = _DURATION_RE.sub("in <duration>", text)
    text = _CLOCK_DURATION_RE.sub("<duration>", text)
    return "\n".join(line.rstrip() for line in text.split("\n"))


def normalize_captured_output(
    stdout: str,
    stderr: str,
    *,
    root: Optional[Path] = None,
) -> dict:
    """Return the canonical semantic form of captured stdout and stderr."""
    return {
        "stdout": _normalize_output_text(stdout, root=root),
        "stderr": _normalize_output_text(stderr, root=root),
    }


def semantic_output_digest(
    exit_code: Optional[int],
    stdout: str,
    stderr: str,
    command: Sequence[str],
    *,
    root: Optional[Path] = None,
) -> str:
    """Hash exit code, normalized output, and argv using canonical JSON."""
    binding = {
        "command": list(command),
        "exit_code": exit_code,
        "normalized_output": normalize_captured_output(stdout, stderr, root=root),
    }
    encoded = json.dumps(
        binding,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _terminate_process_group(process: subprocess.Popen, *, grace_s: float = 1.0) -> Tuple[str, str]:
    """Terminate a timed-out challenge and all of its descendants."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return process.communicate(timeout=grace_s)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return process.communicate()


def _run_challenge(
    root: Path,
    definition: dict,
    *,
    initial_error: str = "",
    surface_id: Optional[str] = None,
) -> dict:
    stdout = ""
    stderr = ""
    exit_code: Optional[int] = None
    timed_out = False
    execution_error = initial_error
    status = "FAIL"
    reasons: List[str] = []
    command = definition.get("command") if isinstance(definition, dict) else None
    if not execution_error and isinstance(command, list) and command:
        try:
            cwd = _challenge_cwd(root, definition)
            process = subprocess.Popen(
                command,
                cwd=str(cwd),
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=float(definition.get("timeout_s", 60)))
                stdout = stdout or ""
                stderr = stderr or ""
                exit_code = process.returncode
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout, stderr = _terminate_process_group(process)
                stdout = stdout or exc.stdout or ""
                stderr = stderr or exc.stderr or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", "replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", "replace")
            status, reasons = _challenge_result(
                definition,
                surface_id=surface_id,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                timed_out=timed_out,
                execution_error="",
                root=root,
            )
        except (OSError, ValueError, CliError) as exc:
            execution_error = str(exc)
            status, reasons = _challenge_result(
                definition,
                surface_id=surface_id,
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                timed_out=False,
                execution_error=execution_error,
                root=root,
            )
    else:
        if not execution_error:
            execution_error = "challenge requires an explicit committed command; no command was configured"
        reasons = [execution_error]
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "execution_error": execution_error,
        "status": status,
        "reasons": reasons,
    }


def _make_challenge_receipt(
    root: Path,
    surface_id: str,
    definition: dict,
    output_path: Path,
    *,
    exit_code: Optional[int],
    status: str,
    timed_out: bool,
    execution_error: str,
    source_revision: str,
    run_id: Optional[str] = None,
    signing_key: Optional[bytes] = None,
) -> dict:
    command = definition.get("command")
    argv = list(command) if isinstance(command, list) else []
    capture = strict_json_loads(output_path.read_text(encoding="utf-8"))
    semantic_digest = semantic_output_digest(
        exit_code,
        capture.get("stdout", ""),
        capture.get("stderr", ""),
        argv,
        root=root,
    )
    receipt = {
        "receipt_type": "EXECUTED",
        "surface_id": surface_id,
        "command": argv,
        "cwd": str(definition.get("cwd") or "."),
        "exit_code": exit_code,
        "captured_output": output_path.relative_to(root).as_posix(),
        "captured_output_digest": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "semantic_output_digest": semantic_digest,
        "source_revision": source_revision,
        "timestamp": now_iso(),
        "timed_out": timed_out,
        "status": status,
        "execution_error": execution_error,
        "challenge_config_digest": _challenge_config_digest(definition),
        "run_id": run_id or "",
    }
    receipt["receipt_sha256"] = _executed_receipt_binding_digest(receipt)
    if signing_key is not None and run_id:
        receipt[LOCAL_INTEGRITY_HMAC_FIELD] = _executed_receipt_hmac(receipt, signing_key)
    return receipt


def _challenge_finding(surface_id: str, reason: str, evidence: str) -> dict:
    category = next((category for sid, _surface, category in COVERAGE_SURFACES if sid == surface_id), "C5")
    if category not in SCORE_CATEGORIES:
        category = "C5"
    return {
        "id": f"CY-CHALLENGE-{surface_id}",
        "severity": "P1",
        "category": category,
        "finding": f"Executed challenge failed for {surface_id}",
        "plain_english_risk": reason,
        "evidence": [evidence],
        "recommended_fix": "Fix the challenged surface or update its committed command/assertions, then rerun the chall"
        "enge.",
        "status": "open",
    }


def challenge_from_root(root: Path, surface_id: Optional[str] = None, output_dir: Optional[Path] = None) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise CliError(f"project root not found: {root}")
    definitions, config_error = load_challenge_config(root)
    selected = [surface_id] if surface_id else [sid for sid, _surface, _category in COVERAGE_SURFACES]
    canonical_ids = {sid for sid, _surface, _category in COVERAGE_SURFACES}
    unknown = sorted(set(selected) - canonical_ids)
    if unknown:
        raise CliError(f"challenge surface must be canonical: {', '.join(unknown)}")
    destination = (output_dir or (root / DEFAULT_CHALLENGE_OUTPUT_DIR)).resolve()
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise CliError("challenge output directory must stay inside the project root") from exc
    destination.mkdir(parents=True, exist_ok=True)
    try:
        signing_key = _load_local_integrity_binding_key(root, create=True)
        key_error = ""
    except CliError as exc:
        signing_key = None
        key_error = str(exc)
    run_id = secrets.token_hex(16)
    source_revision = current_tree_hash(root)
    receipts: List[dict] = []
    findings: List[dict] = []
    surface_results: List[dict] = []
    for sid in selected:
        definition = definitions.get(sid, {})
        execution = _run_challenge(
            root,
            definition if isinstance(definition, dict) else {},
            initial_error=config_error or key_error,
            surface_id=sid,
        )
        stdout = execution["stdout"]
        stderr = execution["stderr"]
        exit_code = execution["exit_code"]
        timed_out = execution["timed_out"]
        execution_error = execution["execution_error"]
        status = execution["status"]
        reasons = execution["reasons"]
        output_path = destination / f"{sid}.capture.json"
        safe_write_text(output_path, _captured_output_payload(stdout, stderr))
        receipt = _make_challenge_receipt(
            root,
            sid,
            definition if isinstance(definition, dict) else {},
            output_path,
            exit_code=exit_code,
            status=status,
            timed_out=timed_out,
            execution_error=execution_error,
            source_revision=source_revision,
            run_id=run_id,
            signing_key=signing_key,
        )
        receipt_path = destination / f"{sid}.receipt.json"
        safe_write_text(receipt_path, json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
        receipt["receipt_path"] = receipt_path.relative_to(root).as_posix()
        receipt["captured_output"] = output_path.relative_to(root).as_posix()
        receipts.append(receipt)
        if status != "PASS":
            findings.append(_challenge_finding(sid, "; ".join(reasons), receipt["captured_output"]))
        surface_results.append(
            {
                "surface_id": sid,
                "status": status,
                "reasons": reasons,
                "receipt": receipt,
            }
        )
    result = {
        "tool": TOOL_NAME,
        "schema": CHALLENGE_RESULT_SCHEMA_ID,
        "generated_at": now_iso(),
        "project": str(root),
        "source_revision": source_revision,
        "complete": not findings and not config_error,
        "surfaces": surface_results,
        "receipts": receipts,
        "findings": findings,
    }
    return result
