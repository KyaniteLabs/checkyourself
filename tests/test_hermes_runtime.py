"""Real runtime integration, intentionally run separately with isolated HERMES_HOME."""
import os
from pathlib import Path
import runpy
import unittest


@unittest.skipUnless(os.environ.get('CHECKYOURSELF_RUNTIME_TEST') == '1', 'requires isolated real Hermes runtime')
class RuntimeIntegration(unittest.TestCase):
    def test_native_gate_and_tool(self):
        runpy.run_path(str(Path(__file__).resolve().parents[1] / 'demo/native_demo.py'), run_name='__main__')
