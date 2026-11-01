"""Behavioral regression for the npm tarball contents.

Security review of PR #48 (2026-11-01) found that `npm pack` run after the
unittest suite ships `tools/checkyourself/__pycache__/*.pyc`: the `files`
allowlist in package.json includes the whole `tools/checkyourself/` subtree,
and npm does not apply `.gitignore` to paths pulled in by the `files` array.

These tests materialize the polluting state a real test run leaves behind
(a compiled `__pycache__` next to the sources), run `npm pack --dry-run`, and
pin both directions of the contract:

* no bytecode (`__pycache__` directories or `.pyc` files) is ever packed;
* every required payload file still is (Python sources, schemas, the bin
  wrapper, the manifest, NOTICE.md, LICENSE).
"""

from __future__ import annotations

import json
import py_compile
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NPM = shutil.which("npm")
PACKAGE_DIR = ROOT / "tools" / "checkyourself"


def required_tarball_paths() -> list[str]:
    """Every tarball path the shipped CLI/MCP surface needs at runtime."""
    paths = [
        "bin/checkyourself.mjs",
        "tools/checkyourself.py",
        "checkyourself.manifest.json",
        "NOTICE.md",
        "LICENSE",
    ]
    paths += [f"tools/checkyourself/{path.name}" for path in sorted(PACKAGE_DIR.glob("*.py"))]
    paths += [f"schemas/{path.name}" for path in sorted((ROOT / "schemas").glob("*.json"))]
    return paths


@unittest.skipUnless(NPM, "npm is required to inspect the packed tarball contents")
class NpmTarballContentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Reproduce the post-unittest working tree: Python bytecode cached next
        # to the sources npm's `files` glob would otherwise sweep in.
        cls.compiled_bytecode = Path(py_compile.compile(str(PACKAGE_DIR / "cli.py"), doraise=True))
        if not cls.compiled_bytecode.exists():  # pragma: no cover - doraise raises instead
            raise AssertionError("py_compile did not produce bytecode to test against")
        cls.tarball_paths = cls._pack_tarball_paths()

    @classmethod
    def _pack_tarball_paths(cls) -> list[str]:
        assert NPM is not None, "guarded by the skipUnless decorator"
        with tempfile.TemporaryDirectory() as cache:
            result = subprocess.run(
                [NPM, "pack", "--dry-run", "--json", "--cache", cache, "--loglevel", "error"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        if result.returncode != 0:
            raise AssertionError(f"npm pack --dry-run failed:\n{result.stdout}\n{result.stderr}")
        try:
            payload = json.loads(result.stdout)
            return [entry["path"] for entry in payload[0]["files"]]
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            raise AssertionError(
                f"npm pack --dry-run did not return a JSON file listing ({exc}):\n{result.stdout[:1000]}"
            ) from exc

    def test_tarball_contains_no_python_bytecode(self) -> None:
        self.assertTrue(
            "__pycache__" in self.compiled_bytecode.parts and self.compiled_bytecode.suffix == ".pyc",
            "test setup must create a real __pycache__/*.pyc before packing",
        )
        leaked = [path for path in self.tarball_paths if "__pycache__" in Path(path).parts or path.endswith(".pyc")]
        self.assertEqual(
            leaked,
            [],
            f"npm tarball ships Python bytecode: {leaked}; package.json files must exclude __pycache__/*.pyc",
        )

    def test_tarball_retains_required_payload(self) -> None:
        packed = set(self.tarball_paths)
        missing = [path for path in required_tarball_paths() if path not in packed]
        self.assertEqual(
            missing,
            [],
            f"npm tarball dropped required payload files: {missing}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
