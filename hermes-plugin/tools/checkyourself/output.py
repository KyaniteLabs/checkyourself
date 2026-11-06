"""Atomic generated-file writes, console output, and score history."""

from __future__ import annotations

from pathlib import Path
import json
import os
import sys
import tempfile
from typing import Any, List, Optional
from .constants import DEFAULT_SCORE_HISTORY_PATH, SCAN_SCHEMA_ID, SCORE_SCHEMA_ID
from .errors import CliError
from .jsonlite import strict_json_loads


def safe_write_text(path: Path, body: str) -> None:
    """Write a generated file, refusing to write through a symlink.

    Generated files land inside scanned (potentially untrusted) directories;
    a pre-planted symlink at the expected name could redirect the write.
    """
    candidate = path
    while True:
        # macOS exposes temporary directories through root-level aliases such
        # as /var and /tmp. They are outside the caller's writable subtree;
        # reject symlinks introduced below those OS-managed aliases.
        if candidate.is_symlink() and candidate.parent != Path(candidate.anchor):
            raise CliError(f"refusing to write through symlink: {path}")
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    temp_fd: Optional[int] = None
    temp_path: Optional[Path] = None
    try:
        temp_fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        temp_path = Path(temp_name)
        with os.fdopen(temp_fd, "w", encoding="utf-8", newline="") as handle:
            temp_fd = None
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_fd is not None:
            os.close(temp_fd)
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def write_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=False, allow_nan=False))


def write_text_result(data: dict) -> None:
    schema = data.get("schema", "")
    if schema == SCAN_SCHEMA_ID:
        c = data["counts"]
        print(
            f"Scanned {data['files_scanned']} files. "
            f"Findings — P0: {c['P0']}, P1: {c['P1']}, P2: {c['P2']}, P3: {c['P3']}"
        )
        limits = data.get("scan_limits") or {}
        if limits.get("incomplete"):
            print("  WARNING: scan incomplete; skipped, unreadable, oversized, or truncated inputs may hide findings.")
        if limits.get("truncated"):
            print(
                f"  WARNING: scan truncated at {limits.get('max_files')} files; "
                f"{limits.get('files_beyond_limit')} files were not scanned. Rerun with --max-files."
            )
        for f in data["findings"]:
            print(f"  [{f['severity']}] {f['id']} {f['finding']}")
        print("Next: run the full CheckYourself diagnostic, then use score/backlog/next for deterministic receipts.")
    elif schema == SCORE_SCHEMA_ID:
        print(f"Score: {data['score']} ({data['confidence']} confidence, raw {data['raw_score']})")
        for cap in data["caps_applied"]:
            print(f"  cap {cap['cap']}: {cap['reason']}")
    elif schema in {"checkyourself-backlog/1", "checkyourself-next-batch/1"}:
        if schema == "checkyourself-next-batch/1":
            ids = data.get("finding_ids") or []
        else:
            ids = data.get("highest_severity_batch") or data.get("first_approval_batch") or []
        print("Next batch: " + (", ".join(ids) if ids else "none"))
    else:
        write_json(data)


def resolve_history_path(findings_path: str, requested: Optional[str]) -> Optional[Path]:
    if requested == "none":
        return None
    if requested == "":
        if findings_path == "-":
            return Path.cwd() / DEFAULT_SCORE_HISTORY_PATH
        return Path(findings_path).resolve().parent / DEFAULT_SCORE_HISTORY_PATH
    if requested:
        return Path(requested)
    # Scoring is read-only by default. Persist a score history only when the
    # caller explicitly supplies --history.
    return None


def append_score_history(path: Optional[Path], result: dict, note: str = "") -> None:
    if path is None:
        return
    entry = {
        "timestamp": result["generated_at"],
        "score": result["score"],
        "raw_score": result["raw_score"],
        "confidence": result["confidence"],
        "score_mode": result.get("score_mode"),
        "counts": result["counts"],
        "findings": result["findings_scored"],
        "note": note,
    }
    history: List[dict] = []
    if path.exists():
        try:
            parsed = strict_json_loads(path.read_text(encoding="utf-8"))
            if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
                raise ValueError("score history must be a JSON array of objects")
            history = parsed
        except (ValueError, UnicodeError):
            # Never silently destroy the audit trail: preserve the corrupt
            # file and warn before starting a fresh history.
            backup = path.with_name(path.name + ".corrupt.bak")
            try:
                path.replace(backup)
                print(f"warning: score history was corrupt; preserved at {backup}", file=sys.stderr)
            except OSError:
                print("warning: score history was corrupt and could not be backed up", file=sys.stderr)
            history = []
    history.append(entry)
    safe_write_text(path, json.dumps(history, indent=2, allow_nan=False) + "\n")
