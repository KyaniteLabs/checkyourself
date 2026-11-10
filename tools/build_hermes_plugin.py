"""Check (or refresh) the plugin's vendored engine against this repository; no network.

The plugin directory may contain only its own files plus a byte-identical copy of the
engine. Any difference, missing file or unlisted extra file fails the check.
"""

import argparse
import hashlib
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
plugin = root / "hermes-plugin"
OWN = {"__init__.py", "evidence_gate.py", "plugin.yaml", "README.md"}
IGNORED_PARTS = {"__pycache__"}


def vendored() -> list:
    names = ["LICENSE", "tools/checkyourself.py"]
    names += sorted(p.relative_to(root).as_posix() for p in (root / "tools/checkyourself").glob("*.py"))
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="refresh the vendored copy from the working tree")
    args = parser.parse_args()
    expected = vendored()
    if args.write:
        shutil.rmtree(plugin / "tools", ignore_errors=True)
        for name in expected:
            (plugin / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, plugin / name)
    errors = []
    for name in expected:
        target = plugin / name
        if not target.is_file() or target.read_bytes() != (root / name).read_bytes():
            errors.append("differs from repository: " + name)
    present = {
        p.relative_to(plugin).as_posix()
        for p in plugin.rglob("*")
        if not p.is_dir() and not IGNORED_PARTS & set(p.relative_to(plugin).parts)
    }
    for extra in sorted(present - set(expected) - OWN):
        errors.append("unlisted file in plugin: " + extra)
    for missing in sorted(OWN - present):
        errors.append("missing plugin file: " + missing)
    if errors:
        print("\n".join(errors))
        return 1
    digest = hashlib.sha256()
    for name in expected:
        digest.update(name.encode() + b"\0" + hashlib.sha256((plugin / name).read_bytes()).digest())
    print("engine copy matches repository: files=%d sha256=%s" % (len(expected), digest.hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
