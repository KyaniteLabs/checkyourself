"""Run with the tested Hermes interpreter; writes only beneath the supplied scratch HOME."""
import json
import os
from pathlib import Path
import shutil
import sys
import time

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / 'tests'))
from test_hermes_plugin import make_evidence

home = Path(os.environ['HERMES_HOME'])
home.mkdir(parents=True, exist_ok=True)
plugin = home / 'plugins/checkyourself-evidence-gate'
shutil.copytree(repo / 'hermes-plugin', plugin, ignore=shutil.ignore_patterns('__pycache__'))
(home / 'config.yaml').write_text('plugins:\n  enabled: [checkyourself-evidence-gate]\n  hook_callback_timeout: 25\n')
root = home / 'demo-project'
root.mkdir()
os.environ['CHECKYOURSELF_SCAN_ROOT'] = str(root)
os.environ['CHECKYOURSELF_ALLOW_CHALLENGES'] = '1'
from hermes_cli import plugins as runtime
manager = runtime.PluginManager()
runtime._plugin_manager = manager
manager.discover_and_load()
loaded = manager._plugins['checkyourself-evidence-gate']
assert loaded.enabled and not loaded.error, loaded.error
start = time.monotonic()
block, _ = runtime._dispatch_pre_tool_call_hooks('kanban_complete', {})
assert block, 'missing evidence was not blocked'
print('1. Attempt completion without evidence -> BLOCKED')
(root / 'findings.json').write_text('{"findings": []}')
(root / 'coverage.json').write_text(json.dumps({'schema': 'checkyourself-coverage/1', 'surfaces': [{'id': 'S11', 'surface': 'Tests, quality gates, and regression coverage', 'category': 'C5', 'status': 'Pass', 'evidence_reviewed': ['test_roundtrip.py'], 'missing_evidence': []}]}))
from tools.registry import registry
entry = registry.get_entry('checkyourself_evidence_score')
assert entry, 'native tool missing'
incomplete = {'findings': 'findings.json', 'coverage': 'coverage.json', 'claim': 'The fixture tests pass'}
failed = json.loads(entry.handler(incomplete))
assert not failed['allowed']
print('   Incomplete claim score:', failed['score']['score'], '-> FAIL')
evidence = make_evidence(root)
block, _ = runtime._dispatch_pre_tool_call_hooks('kanban_complete', {'metadata': {'checkyourself': evidence}})
assert block is None, block
print('2. Execute fixture challenge; add verified S11 evidence -> ALLOWED')
from tools.registry import registry
entry = registry.get_entry('checkyourself_evidence_score')
assert entry, 'native tool missing'
result = json.loads(entry.handler(evidence))
assert result['allowed'], result
print('3. Native tool agrees: C5 full credit; overall production score =', result['score']['score'])
print('4. Demo completion sink -> DONE (simulation; no real board mutation)')
coverage = json.loads((root / 'coverage.json').read_text())
(root / coverage['surfaces'][0]['evidence_receipts'][0]['captured_output']).write_text('{}')
block, _ = runtime._dispatch_pre_tool_call_hooks('kanban_complete', {'metadata': {'checkyourself': evidence}})
assert block, 'tampered evidence was not blocked'
print('5. Tamper with capture -> BLOCKED again')
print('elapsed_seconds=%.3f' % (time.monotonic() - start))
