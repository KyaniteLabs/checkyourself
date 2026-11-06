"""Real MCP gate tests. Test receipts are synthetic, never production evidence."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gate', ROOT / 'hermes-plugin/evidence_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def make_evidence(root):
    import subprocess
    import sys
    (root / 'test_roundtrip.py').write_text('import json\ndef test_roundtrip():\n    assert json.loads(json.dumps({"answer": 42})) == {"answer": 42}\n')
    config = root / '.checkyourself/challenges.json'
    config.parent.mkdir()
    config.write_text(json.dumps({'schema': 'checkyourself-challenges/1', 'challenges': {'S11': {'command': [os.environ.get('CHECKYOURSELF_TEST_PYTHON', sys.executable), '-m', 'pytest', '-q'], 'timeout_s': 30, 'success': {'exit_zero': True, 'regex_match': r'\b1 passed\b'}, 'output_kind': 'text'}}}))
    proc = subprocess.run([sys.executable, str(ROOT / 'hermes-plugin/tools/checkyourself.py'), 'challenge', str(root), '--surface', 'S11', '--format', 'json'], capture_output=True, text=True, check=True, env={})
    receipt = json.loads(proc.stdout)['receipts'][0]
    coverage = {'schema': 'checkyourself-coverage/1', 'surfaces': [{'id': 'S11', 'surface': 'Tests, quality gates, and regression coverage', 'category': 'C5', 'status': 'Pass', 'evidence_reviewed': [receipt['captured_output']], 'evidence_receipts': [receipt], 'missing_evidence': [], 'not_applicable_reason': ''}]}
    (root / 'findings.json').write_text('{"findings": []}')
    (root / 'coverage.json').write_text(json.dumps(coverage))
    return {'findings': 'findings.json', 'coverage': 'coverage.json', 'claim': 'Fixture coverage is verified'}


class GateTests(unittest.TestCase):
    def test_real_mcp_block_pass_tamper(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'CHECKYOURSELF_SCAN_ROOT': tmp, 'CHECKYOURSELF_ALLOW_CHALLENGES': '1'}):
            root = Path(tmp)
            self.assertEqual(gate.completion_gate('kanban_complete', {})['action'], 'block')
            evidence = make_evidence(root)
            args = {'metadata': {'checkyourself': evidence}}
            result = gate.evidence_score(evidence)
            self.assertTrue(result['allowed'], result)
            self.assertIsNone(gate.completion_gate('kanban_complete', args))
            coverage = json.loads((root / 'coverage.json').read_text())
            (root / coverage['surfaces'][0]['evidence_receipts'][0]['captured_output']).write_text('{}')
            self.assertFalse(gate.evidence_score(evidence)['allowed'])
            self.assertEqual(gate.completion_gate('kanban_complete', args)['action'], 'block')

    def test_estimate_and_unknown_never_pass(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'CHECKYOURSELF_SCAN_ROOT': tmp, 'CHECKYOURSELF_ALLOW_CHALLENGES': '1'}):
            root = Path(tmp)
            (root / 'findings.json').write_text('{"findings": []}')
            (root / 'coverage.json').write_text(json.dumps(gate.mcp_call('coverage_emit', {}, root)))
            result = json.loads(gate.tool_handler({'findings': 'findings.json', 'coverage': 'coverage.json', 'claim': 'done'}))
            self.assertFalse(result['allowed'])

    def test_fail_closed_and_unrelated_tools(self):
        self.assertIsNone(gate.completion_gate('read_file', {}))
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(gate.completion_gate('kanban_complete', {})['action'], 'block')
            self.assertFalse(json.loads(gate.tool_handler({}))['allowed'])
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'CHECKYOURSELF_SCAN_ROOT': tmp, 'CHECKYOURSELF_ALLOW_CHALLENGES': '1'}):
            for name in ('../outside.json', '/etc/passwd'):
                self.assertEqual(gate.completion_gate('kanban_complete', {'metadata': {'checkyourself': {'findings': name, 'coverage': name, 'claim': 'done'}}})['action'], 'block')

    def test_source_change_and_opt_in_block(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'CHECKYOURSELF_SCAN_ROOT': tmp, 'CHECKYOURSELF_ALLOW_CHALLENGES': '1'}):
            root = Path(tmp)
            evidence = make_evidence(root)
            (root / 'test_roundtrip.py').write_text('def test_changed():\n    assert False\n')
            self.assertFalse(gate.evidence_score(evidence)['allowed'])
            os.environ['CHECKYOURSELF_ALLOW_CHALLENGES'] = '0'
            self.assertFalse(json.loads(gate.tool_handler(evidence))['allowed'])
            os.environ['CHECKYOURSELF_ALLOW_CHALLENGES'] = '1'
            (root / 'outside').symlink_to('/etc/passwd')
            self.assertFalse(json.loads(gate.tool_handler(dict(evidence, findings='outside')))['allowed'])

    def test_timeout_and_engine_errors_block(self):
        with patch.object(gate, 'evidence_score', side_effect=TimeoutError):
            self.assertEqual(gate.completion_gate('kanban_complete', {})['action'], 'block')

    def test_registration_is_pure(self):
        calls = []
        class Context:
            def __getattr__(self, key):
                return lambda *a, **kw: calls.append(key)
        with patch('subprocess.Popen', side_effect=AssertionError('I/O during register')):
            gate.register(Context())
        self.assertEqual(calls, ['register_tool', 'register_hook', 'register_command', 'register_cli_command'])


if __name__ == '__main__':
    unittest.main()
