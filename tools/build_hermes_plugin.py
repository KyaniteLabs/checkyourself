"""Check (or explicitly refresh) the reviewable engine snapshot; no network."""

import argparse
from pathlib import Path
import subprocess

BASE = "b2a5684bf9e5232f2c945060dbac8a76c0517d6a"
root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--write", action="store_true")
args = p.parse_args()
files = subprocess.check_output(
    ["git", "ls-tree", "-r", "--name-only", BASE, "tools", "schemas", "package.json", "LICENSE"], cwd=root, text=True
).splitlines()
for name in files:
    expected = subprocess.check_output(["git", "show", BASE + ":" + name], cwd=root)
    target = root / "hermes-plugin" / name
    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(expected)
    else:
        assert target.read_bytes() == expected, name + " differs from pinned source"
print("engine snapshot matches", BASE, "files=", len(files))
