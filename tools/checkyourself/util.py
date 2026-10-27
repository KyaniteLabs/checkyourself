"""Small text/JSON utility helpers shared across engine modules."""

from __future__ import annotations

from pathlib import Path
import datetime as _dt
from typing import Any, Tuple
from .constants import SECRET_SHAPE_RES, SECRET_VALUE_RE


def now_iso() -> str:
    # UTC so history entries from laptops and CI machines stay comparable.
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_text(path: Path, max_chars: int = 200_000) -> str:
    try:
        # Never read through symlinks: an adversarial project could point a
        # source-looking file at credentials outside the scanned tree.
        if path.is_symlink():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def read_text_with_status(path: Path, max_chars: int) -> Tuple[str, bool, bool]:
    """Read bounded text and distinguish truncation from an unreadable file."""
    try:
        if path.is_symlink():
            return "", False, True
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read(max_chars + 1)
        return text[:max_chars], len(text) > max_chars, False
    except OSError:
        return "", False, True


def looks_binary(text: str) -> bool:
    return "\x00" in text[:2048]


def redact_sensitive_text(value: str) -> str:
    """Redact credential-shaped substrings before they can reach generated output."""
    redacted = value
    redacted = SECRET_VALUE_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", redacted)
    for pattern in SECRET_SHAPE_RES:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def compact_context(line: str, limit: int = 140) -> str:
    context = " ".join(redact_sensitive_text(line).strip().split())
    if len(context) > limit:
        return context[: limit - 3] + "..."
    return context


def secret_evidence(
    rp: str,
    line_no: int,
    tag: str,
    match_type: str,
    confidence: str,
    line: str,
) -> str:
    return (
        f'{rp}:{line_no} ({tag}; matched: {match_type}; confidence: {confidence}; context: "{compact_context(line)}")'
    )


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [str(parse_scalar(part)) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value
