"""Minimal Hermes secret-scope stub for plugin tests (not a full vendored module)."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Mapping, Optional

_SCOPE: ContextVar[Optional[Mapping[str, str]]] = ContextVar("_SCOPE", default=None)


def set_secret_scope(mapping: Mapping[str, str] | None):
    return _SCOPE.set(mapping)


def reset_secret_scope(token) -> None:
    _SCOPE.reset(token)


def get_secret(name: str, default: str = "") -> str:
    scope = _SCOPE.get()
    if scope is not None and name in scope:
        return scope[name] or ""
    import os
    return os.environ.get(name, default) or ""
