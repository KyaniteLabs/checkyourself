"""Load the CheckYourself Hermes plugin against the vendored Hermes v0.21.6 runtime."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = Path(__file__).resolve().parent / "hermes_runtime"


class FakeCtx:
    def __init__(self, config=None):
        self.config = dict(config or {})
        self.hooks, self.tools, self.commands, self.skills = {}, {}, {}, {}

    def get_config(self, key, default=None):
        return self.config.get(key, default)

    def register_hook(self, name, fn):
        self.hooks[name] = fn

    def register_tool(self, name, **kw):
        self.tools[name] = kw

    def register_command(self, name, handler, **kw):
        self.commands[name] = handler

    def register_skill(self, name, path, description=""):
        self.skills[name] = (path, description)


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    for var in ("HERMES_PLATFORM", "HERMES_SESSION_PLATFORM", "HERMES_SESSION_SOURCE", "TERMINAL_CWD"):
        monkeypatch.delenv(var, raising=False)
    return home


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.syspath_prepend(str(RUNTIME_DIR))
    for name in list(sys.modules):
        if name in {"gateway", "agent"} or name.startswith(("gateway.", "agent.")):
            monkeypatch.delitem(sys.modules, name)
    from gateway import session_context

    session_context.reset_session_vars()
    yield session_context
    session_context.reset_session_vars()


@pytest.fixture
def project(tmp_path):
    """A scan root holding one small project with a planted fake secret."""
    root = tmp_path / "work"
    app = root / "app"
    app.mkdir(parents=True)
    (app / "README.md").write_text("# demo app\n", encoding="utf-8")
    (app / "main.py").write_text("print('hi')\n", encoding="utf-8")
    # Built at run time so secret scanners of this repo don't flag the fixture.
    fake_key = "sk" + "-" + "Zq8LmN3pRt5VwX7yB2cD4fG6hJ"
    (app / "settings.py").write_text(f'CLIENT = "{fake_key}"\n', encoding="utf-8")
    return root


@pytest.fixture
def plugin(hermes_home, runtime, project):
    name = "checkyourself_hermes_plugin"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, PLUGIN_DIR / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    mod._ctx = FakeCtx({"scan_root": str(project)})
    yield mod
    sys.modules.pop(name, None)
