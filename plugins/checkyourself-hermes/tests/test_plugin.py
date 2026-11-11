"""Behaviour of the CheckYourself Hermes plugin: scope, chat platforms, the hook,
stored scans, the vendored CLI's integrity and its time limit."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from conftest import PLUGIN_DIR, FakeCtx

REPO_CLI = PLUGIN_DIR.parents[1] / "tools" / "checkyourself.py"


def _tool(plugin, name, args):
    handler = plugin._tool_scan if name == "scan" else plugin._tool_next
    return json.loads(handler(args))


# --- registration ----------------------------------------------------------------


def test_register(plugin):
    ctx = FakeCtx()
    plugin.register(ctx)
    assert set(ctx.tools) == {"checkyourself_scan", "checkyourself_next"}
    assert set(ctx.hooks) == {"pre_llm_call"}
    assert set(ctx.commands) == {"checkyourself"}
    path, desc = ctx.skills["checkyourself"]
    assert Path(path).is_file()
    assert desc.startswith("Use when finished work claims") and "\n" not in desc


def test_manifest_matches_code(plugin):
    text = (PLUGIN_DIR / "plugin.yaml").read_text(encoding="utf-8")
    for key in plugin.DEFAULTS:
        assert f"\n  {key}:\n" in text, key
    for tool in ("checkyourself_scan", "checkyourself_next"):
        assert f"  - {tool}\n" in text


# --- scanning ---------------------------------------------------------------------

def test_scan_finds_planted_secret_and_stores_it(plugin):
    res = _tool(plugin, "scan", {"path": "app"})
    assert res["ok"], res
    assert res["project"] == "app" and res["finding_count"] >= 1
    assert any(str(f["id"]).startswith("CY-SECRET") for f in res["findings"])
    assert "Zq8LmN3p" not in json.dumps(res)  # the CLI redacts the value
    assert "Unknown" in res["reading"] or "re-check" in res["reading"]
    stored = list((plugin._scans_dir()).glob("*.json"))
    assert len(stored) == 1
    assert oct(stored[0].parent.stat().st_mode & 0o777) == "0o700"
    nxt = _tool(plugin, "next", {"path": "app"})
    assert nxt["ok"] and nxt["batch"], nxt
    assert nxt["scan_age_seconds"] is not None


def test_next_without_scan_says_so(plugin):
    res = _tool(plugin, "next", {"path": "app"})
    assert res == {"ok": False, "error": "no scan for app yet; run checkyourself_scan first"}


@pytest.mark.parametrize("path", ["..", "/", "/etc", "app/../../"])
def test_paths_outside_root_refused_before_cli(plugin, monkeypatch, path):
    monkeypatch.setattr(plugin, "run_cli", lambda *a, **k: pytest.fail("CLI must not run"))
    res = _tool(plugin, "scan", {"path": path})
    assert res["ok"] is False and "outside the scan root" in res["error"]


def test_symlink_escape_refused(plugin, project, tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / "link").symlink_to(outside)
    monkeypatch.setattr(plugin, "run_cli", lambda *a, **k: pytest.fail("CLI must not run"))
    res = _tool(plugin, "scan", {"path": "link"})
    assert res["ok"] is False and "outside" in res["error"]


def test_outside_path_refused_even_when_missing(plugin):
    res = _tool(plugin, "scan", {"path": "/no/such/place"})
    assert "outside the scan root" in res["error"]


@pytest.mark.parametrize("args", [{"path": 3}, {"deep": "yes"}, {"bogus": 1}, ["x"]])
def test_bad_arguments(plugin, args):
    res = json.loads(plugin._tool_scan(args))
    assert res["ok"] is False


def test_unexpected_error_does_not_leak_detail(plugin, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("/home/someone/secret-path")

    monkeypatch.setattr(plugin, "scan", boom)
    monkeypatch.setattr(plugin, "_tool_scan", plugin._wrap(lambda a: plugin.scan(**a)))
    res = json.loads(plugin._tool_scan({}))
    assert "secret-path" not in res["error"] and "RuntimeError" in res["error"]


# --- the vendored CLI --------------------------------------------------------------

def test_vendor_manifest_is_complete_and_current(plugin):
    manifest = json.loads(plugin.VENDOR_MANIFEST.read_text(encoding="utf-8"))
    base = plugin.VENDOR_MANIFEST.parent
    on_disk = {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file() and p.name != "MANIFEST.json"}
    assert set(manifest["files"]) == on_disk
    assert plugin._vendor_problem() is None


def _repo_cli_is_single_file() -> bool:
    """The bundle is the single-file CLI. A repo whose tools/checkyourself.py is a
    thin facade over a package has no single file to compare against."""
    try:
        return len(REPO_CLI.read_text(encoding="utf-8").splitlines()) > 1000
    except OSError:
        return False


@pytest.mark.skipif(not _repo_cli_is_single_file(), reason="needs the single-file CLI in this repository")
def test_vendored_cli_matches_repo_cli(plugin):
    """A release must ship the CLI it names; re-vendor when tools/ changes."""
    assert plugin.CLI_PATH.read_bytes() == REPO_CLI.read_bytes()


def test_changed_vendor_file_blocks_the_cli(plugin, tmp_path, monkeypatch):
    vendor = tmp_path / "vendor"
    shutil.copytree(plugin.VENDOR_MANIFEST.parent, vendor)
    monkeypatch.setattr(plugin, "VENDOR_MANIFEST", vendor / "MANIFEST.json")
    cli = vendor / "checkyourself" / "tools" / "checkyourself.py"
    monkeypatch.setattr(plugin, "CLI_PATH", cli)
    cli.write_text(cli.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    res = plugin.run_cli(["describe"], Path.cwd())
    assert res["ok"] is False and "changed since release" in res["error"]
    cli.unlink()
    assert "missing" in plugin.run_cli(["describe"], Path.cwd())["error"]


def test_cli_gets_no_secrets_in_env(plugin, monkeypatch, project):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-pass")
    env = plugin._child_env(project)
    assert "OPENAI_API_KEY" not in env and env["CHECKYOURSELF_SCAN_ROOT"] == str(project)


def test_timeout_kills_and_reports(plugin, tmp_path, monkeypatch):
    slow = tmp_path / "slow.py"
    slow.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    monkeypatch.setattr(plugin, "CLI_PATH", slow)
    monkeypatch.setattr(plugin, "_vendor_problem", lambda: None)
    plugin._ctx = FakeCtx({"timeout_seconds": 5})
    res = plugin.run_cli([], tmp_path)
    assert res["ok"] is False and "within 5s" in res["error"]


def test_non_json_output_is_an_error(plugin, tmp_path, monkeypatch):
    bad = tmp_path / "bad.py"
    bad.write_text("import sys\nprint('nope')\nsys.stderr.write('boom\\n')\n", encoding="utf-8")
    monkeypatch.setattr(plugin, "CLI_PATH", bad)
    monkeypatch.setattr(plugin, "_vendor_problem", lambda: None)
    res = plugin.run_cli([], tmp_path)
    assert res == {"ok": False, "error": "CheckYourself returned no JSON (boom)"}


def test_scans_are_pruned(plugin, project, monkeypatch):
    monkeypatch.setattr(plugin, "SCANS_KEPT", 2)
    for i in range(4):
        (project / f"p{i}").mkdir()
        assert _tool(plugin, "scan", {"path": f"p{i}"})["ok"]
    assert len(list(plugin._scans_dir().glob("*.json"))) == 2


# --- hook ----------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "is it really done?", "Is this ready to ship", "can we launch tomorrow",
    "production-ready yet?", "please checkyourself",
    [{"type": "text", "text": "is the app done?"}, {"type": "image_url", "image_url": {"url": "x"}}],
])
def test_hook_fires_on_ship_questions(plugin, msg):
    assert plugin._on_pre_llm(user_message=msg) == {"context": plugin._BRIEF}


@pytest.mark.parametrize("msg", [
    "Is this PR good to merge?", "lgtm, ship it?", "we're done right?", "are the tests done?", "should we merge this",
])
def test_hook_fires_on_less_formal_ship_questions(plugin, msg):
    assert plugin._on_pre_llm(user_message=msg) == {"context": plugin._BRIEF}


@pytest.mark.parametrize("msg", [
    "I'm done with lunch", "ship the package to Ohio", "are we done with lunch?", "Is the oven ready?",
    "are you ready?", "Is the download complete?", "can we ship the package to Ohio?", "are we ready for dinner?",
    "", None, 42, [{"type": "image_url"}],
])
def test_hook_quiet_otherwise(plugin, msg):
    assert plugin._on_pre_llm(user_message=msg) is None


def test_hook_can_be_turned_off(plugin, project):
    plugin._ctx = FakeCtx({"scan_root": str(project), "inject_on_ship_talk": False})
    assert plugin._on_pre_llm(user_message="is it done?") is None


# --- slash and chat platforms ----------------------------------------------------------

def test_slash_help_and_unknown(plugin):
    assert plugin._slash("", platform="cli").startswith("Usage:")
    assert "Unknown subcommand" in plugin._slash("frobnicate", platform="cli")


def test_slash_scan_on_cli(plugin):
    out = plugin._slash("scan app", platform="cli")
    assert out.startswith("app:") and "finding(s)" in out


@pytest.mark.parametrize("platform", ["telegram", "discord", "slack"])
def test_slash_scan_refused_on_chat(plugin, monkeypatch, platform):
    monkeypatch.setattr(plugin, "run_cli", lambda *a, **k: pytest.fail("CLI must not run"))
    assert "off on chat platforms" in plugin._slash("scan app", platform=platform)


def test_slash_platform_kwarg_beats_session_lookup(plugin, monkeypatch):
    monkeypatch.setattr(plugin, "_on_gateway", lambda: True)
    assert plugin._slash("scan app", platform="tui").startswith("app:")


def test_slash_falls_back_to_session_lookup(plugin, runtime, monkeypatch):
    monkeypatch.setattr(plugin, "run_cli", lambda *a, **k: pytest.fail("CLI must not run"))
    tokens = runtime.set_session_vars(platform="telegram")
    try:
        assert "off on chat platforms" in plugin._slash("scan app")
    finally:
        runtime.clear_session_vars(tokens)


def test_chat_replies_hide_machine_paths(plugin, project):
    out = plugin._slash("status", platform="telegram")
    assert str(project) not in out and str(Path.home()) not in out
    assert "…/work" in out
    assert str(project) in plugin._slash("status", platform="cli")


def test_chat_scan_when_allowed_is_redacted(plugin, project):
    plugin._ctx = FakeCtx({"scan_root": str(project), "allow_slash_scan_on_gateway": True})
    out = plugin._slash("scan /etc", platform="telegram")
    assert "outside the scan root" in out and str(project) not in out


def test_redact_shortens_any_absolute_path(plugin):
    assert plugin._redact("see /var/lib/thing/file.txt now") == "see …/file.txt now"


def test_slash_deep_only_for_scan(plugin):
    assert plugin._slash("next app --deep", platform="cli").startswith("--deep belongs to scan")


# --- roast fixes: hostile input, string settings, session folder ---------------------

def test_slash_never_raises_on_hostile_folders(plugin, project, monkeypatch):
    monkeypatch.setattr(plugin, "run_cli", lambda *a, **k: pytest.fail("CLI must not run"))
    (project / "loop").symlink_to(project / "loop")
    for arg in ("scan loop", "scan " + "a" * 300, "next loop"):
        out = plugin._slash(arg, platform="cli")
        assert out.startswith("CheckYourself:"), out


def test_slash_answers_even_when_an_operation_raises(plugin, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("/home/someone/secret-path")
    monkeypatch.setattr(plugin, "status", boom)
    out = plugin._slash("status", platform="telegram")
    assert out == "CheckYourself hit an unexpected RuntimeError; see the Hermes log."


def test_slash_accepts_quoted_folder_and_any_case_deep(plugin, project):
    (project / "my app").mkdir()
    assert plugin._slash('scan "my app" --DEEP', platform="cli").startswith("my app:")


@pytest.mark.parametrize("key", ["allow_slash_scan_on_gateway", "inject_on_ship_talk"])
def test_string_booleans_fall_back_to_the_default(plugin, project, key):
    plugin._ctx = FakeCtx({"scan_root": str(project), key: "false" if key == "inject_on_ship_talk" else "true"})
    assert plugin._bool_cfg(key) is plugin.DEFAULTS[key]


def test_string_true_does_not_open_chat_scans(plugin, project, monkeypatch):
    monkeypatch.setattr(plugin, "run_cli", lambda *a, **k: pytest.fail("CLI must not run"))
    plugin._ctx = FakeCtx({"scan_root": str(project), "allow_slash_scan_on_gateway": "true"})
    assert "off on chat platforms" in plugin._slash("scan app", platform="telegram")


def test_empty_scan_root_uses_the_session_pinned_folder(plugin, project, tmp_path, monkeypatch):
    from agent import runtime_cwd

    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.setenv("TERMINAL_CWD", str(other))
    plugin._ctx = FakeCtx({"scan_root": ""})
    token = runtime_cwd.set_session_cwd(str(project))
    try:
        assert plugin._root() == project.resolve()
    finally:
        runtime_cwd.reset_session_cwd(token)
    assert plugin._root() == other.resolve()


def test_redact_keeps_urls_whole(plugin):
    assert plugin._redact("see https://example.com/a/b") == "see https://example.com/a/b"
    assert plugin._redact("at /srv/x/y/z.py") == "at …/z.py"


def test_status_ages_read_as_time(plugin):
    assert plugin._ago(30) == "just now"
    assert plugin._ago(90) == "1 min ago"
    assert plugin._ago(86400 * 2) == "2 d ago"


def test_next_shows_rollback(plugin):
    out = plugin._fmt_next({"ok": True, "project": "app", "reading": "r", "batch": [
        {"finding_id": "X", "severity": "P1", "fix_summary": "f", "verification": "v", "rollback": "git revert"}]})
    assert "roll back: git revert" in out


# --- CLI result handling (review round 2) ------------------------------------------

def _fake_cli(plugin, tmp_path, monkeypatch, body):
    f = tmp_path / "fake_cli.py"
    f.write_text(body, encoding="utf-8")
    monkeypatch.setattr(plugin, "CLI_PATH", f)
    monkeypatch.setattr(plugin, "_vendor_problem", lambda: None)


def test_nonzero_exit_is_an_error_even_with_json(plugin, tmp_path, monkeypatch):
    _fake_cli(plugin, tmp_path, monkeypatch, "import sys,json\nprint(json.dumps({'findings': []}))\nsys.stderr.write('crashed late\\n')\nsys.exit(3)\n")
    res = plugin.run_cli([], tmp_path)
    assert res == {"ok": False, "error": "CheckYourself failed (exit 3: crashed late)"}


def test_error_envelope_is_an_error(plugin, tmp_path, monkeypatch):
    _fake_cli(plugin, tmp_path, monkeypatch, "import json\nprint(json.dumps({'error': 'bad path', 'code': 2}))\n")
    res = plugin.run_cli([], tmp_path)
    assert res == {"ok": False, "error": "CheckYourself refused: bad path"}


def test_oversized_output_is_stopped_while_streaming(plugin, tmp_path, monkeypatch):
    monkeypatch.setattr(plugin, "STDOUT_MAX", 64 * 1024)
    _fake_cli(plugin, tmp_path, monkeypatch, "import sys,time\nwhile True:\n    sys.stdout.write('x' * 65536); sys.stdout.flush()\n")
    plugin._ctx = FakeCtx({"timeout_seconds": 30})
    res = plugin.run_cli([], tmp_path)
    assert res["ok"] is False and "larger than" in res["error"]


def test_scan_reports_counts_status_and_incomplete(plugin, monkeypatch):
    findings = [{"id": f"F{i}", "severity": "P2", "title": "t"} for i in range(12)]
    findings[0].update(status="suppressed", suppression={"reason": "reviewed"})
    data = {"findings": findings, "files_scanned": 3, "counts": {"P2": 12},
            "scan_limits": {"incomplete": True, "symlinks_skipped": 2, "files_unreadable": 0}}
    calls = []

    def fake(args, root):
        calls.append(args)
        if args[0] == "scan":
            return {"ok": True, "data": data}
        snap = Path(args[args.index("--findings") + 1])
        assert json.loads(snap.read_text())["findings"] == findings  # this run's own findings
        return {"ok": True, "data": {"score": 50}}

    monkeypatch.setattr(plugin, "run_cli", fake)
    res = plugin.scan("app")
    assert res["finding_count"] == 12 and res["findings_shown"] == 10
    assert res["incomplete"] is True and res["skipped"] == {"symlinks_skipped": 2}
    sup = [f for f in res["findings"] if f["id"] == "F0"][0]
    assert sup["status"] == "suppressed" and sup["suppression"] == {"reason": "reviewed"}
    snap = Path(calls[1][calls[1].index("--findings") + 1])
    assert not snap.exists()
    text = plugin._fmt_scan(res)
    assert "incomplete scan" in text and "symlinks skipped 2" in text and "Showing 10 of 12" in text and "(suppressed)" in text


@pytest.mark.parametrize("raw", ["scan --help", "next -h", "scan app help"])
def test_subcommand_help(plugin, monkeypatch, raw):
    monkeypatch.setattr(plugin, "run_cli", lambda *a, **k: pytest.fail("CLI must not run"))
    assert plugin._slash(raw, platform="cli").startswith("Usage")


@pytest.mark.parametrize("raw", [None, 3, ["scan"], {"x": 1}])
def test_slash_non_string_args_show_help(plugin, raw):
    assert plugin._slash(raw, platform="cli").startswith("Usage")


def test_next_shows_scan_age(plugin):
    out = plugin._fmt_next({"ok": True, "project": "app", "scan_age_seconds": 7200,
                            "batch": [{"severity": "P1", "finding_id": "F1", "fix_summary": "s", "verification": "v"}],
                            "reading": "r"})
    assert "from the scan 2 h ago" in out


def test_clipped_slash_output_does_not_point_at_a_tool_result(plugin):
    out = plugin._clip("line\n" * 2000)
    assert "tool result" not in out and "Ask the agent" in out
