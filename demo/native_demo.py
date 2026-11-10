"""Drive the evidence gate through a real Hermes runtime. Run with the Hermes interpreter.

Writes only beneath HERMES_HOME, which must be a fresh scratch directory.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time

repo = Path(__file__).resolve().parents[1]
home = Path(os.environ["HERMES_HOME"]).resolve()
home.mkdir(parents=True, exist_ok=True)
if any(home.iterdir()):
    sys.exit("HERMES_HOME must be an empty scratch directory")
for name in ("HERMES_INTERACTIVE", "HERMES_GATEWAY_SESSION", "HERMES_EXEC_ASK", "HERMES_KANBAN_TASK",
             "HERMES_KANBAN_WORKSPACE", "HERMES_KANBAN_BOARD"):
    os.environ.pop(name, None)  # a headless worker: nobody can answer an approval prompt

PLUGIN = "checkyourself-evidence-gate"
TOOL = "checkyourself_evidence_check"
shutil.copytree(repo / "hermes-plugin", home / "plugins" / PLUGIN, ignore=shutil.ignore_patterns("__pycache__"))
config = home / "config.yaml"
config.write_text("plugins:\n  enabled: [%s]\n  hook_callback_timeout: 30\n" % PLUGIN)

# A task workspace with a passing unittest suite as its S11.
ws = home / "worktrees" / "t_demo"
(ws / ".git").mkdir(parents=True)
(ws / "test_fixture.py").write_text(
    "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1 + 1, 2)\n")
(ws / ".checkyourself").mkdir()
(ws / ".checkyourself" / "challenges.json").write_text(json.dumps({"challenges": {"S11": {
    "command": [sys.executable, "-I", "-B", "-m", "unittest", "-q"], "timeout_s": 60,
    "success": {"exit_zero": True}}}}))

from hermes_cli import plugins as runtime  # noqa: E402

manager = runtime.PluginManager()
runtime._plugin_manager = manager
manager.discover_and_load()
loaded = manager._plugins[PLUGIN]
assert loaded.enabled and not loaded.error, loaded.error
cli = manager._cli_commands["evidence-gate"]


def operator(*argv):
    """Run the plugin's registered `hermes evidence-gate` command in-process."""
    import argparse
    parser = argparse.ArgumentParser(prog="hermes evidence-gate")
    cli["setup_fn"](parser)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            cli["handler_fn"](parser.parse_args(list(argv)))
            code = 0
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue()


def worker(on):
    env = {"HERMES_KANBAN_TASK": "t_demo", "HERMES_KANBAN_WORKSPACE": str(ws), "HERMES_KANBAN_BOARD": "demo"}
    for key, value in env.items():
        if on:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


def complete():
    block, _ = runtime._dispatch_pre_tool_call_hooks("kanban_complete", {"summary": "done"})
    return block


start = time.monotonic()
code, out = operator("approve", str(ws))
assert code == 0 and "--confirm" in out, out
digest = json.loads(out[: out.index("\n\nReview")])["digest"]
rule = next(line.strip() for line in out.splitlines() if line.strip().startswith("plugin_rule:"))
worker(True)
code, out = operator("approve", str(ws), "--confirm", digest)
assert code == 2 and "refused" in out, out
print("1. Operator approval from inside a worker -> refused")
worker(False)
code, out = operator("approve", str(ws), "--confirm", digest)
assert code == 0 and "approved" in out, out
print("2. Operator previews, then confirms digest %s... -> approved" % digest[:16])
worker(True)

block = complete()
assert block and "NO_VERDICT" in block, block
print("3. Agent calls kanban_complete with no verdict -> BLOCKED:", block.split(":")[0])

block, _ = runtime._dispatch_pre_tool_call_hooks(TOOL, {"claim": "tests pass"})
assert block and "BLOCKED" in block, block
print("4. Check tool, headless, rule not allowlisted -> BLOCKED by the Hermes approval gate")

config.write_text(config.read_text() + "command_allowlist:\n  - %s\n" % rule)
block, _ = runtime._dispatch_pre_tool_call_hooks(TOOL, {"claim": "tests pass"})
assert block is None, block
print("5. Operator allowlists %s -> approval gate passes" % rule)

from tools.registry import registry  # noqa: E402

entry = registry.get_entry(TOOL)
assert entry, "native tool missing"
result = json.loads(entry.handler({"claim": "tests pass"}))
assert result["state"] == "ALLOWED" and result["completion_allowed_now"], result
print("6. Check runs S11 and the scanner -> %s" % result["state"])

assert complete() is None
print("7. kanban_complete -> ALLOWED (hook executed nothing)")

(ws / "test_fixture.py").write_text((ws / "test_fixture.py").read_text() + "\n# changed after the check\n")
block = complete()
assert block and "STALE_TREE" in block, block
print("8. A workspace file changes -> BLOCKED again (STALE_TREE)")
print("elapsed_seconds=%.3f" % (time.monotonic() - start))
