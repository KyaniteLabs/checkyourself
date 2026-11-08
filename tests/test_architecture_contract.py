import fnmatch
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchitectureContractTests(unittest.TestCase):
    def test_source_inventory(self):
        policy = json.loads((ROOT / "qa/architecture-paths.json").read_text())
        self.assertEqual(set(policy), {"schema_version", "repo", "paths"})
        self.assertEqual(type(policy["schema_version"]), int)
        self.assertEqual(policy["schema_version"], 1)
        self.assertEqual(policy["repo"], "github.com/KyaniteLabs/checkyourself")
        self.assertTrue(policy["paths"])
        tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
        for item in policy["paths"]:
            with self.subTest(pattern=item["pattern"]):
                self.assertEqual(set(item), {"pattern", "layer", "owner"})
                self.assertIn(item["owner"], {"engineering", "product"})
                self.assertTrue(item["layer"].strip())
                pattern = item["pattern"]
                self.assertFalse(Path(pattern).is_absolute())
                self.assertNotIn("..", Path(pattern).parts)
                matches = [p for p in tracked if fnmatch.fnmatchcase(p, pattern)]
                self.assertTrue(matches, "inventory patterns must match tracked files")
                self.assertTrue(all((ROOT / p).is_file() for p in matches))
        for sensitive in (
            "tools/checkyourself/receipts.py",
            "tools/checkyourself/challenge_run.py",
            "tools/checkyourself/mcp.py",
            ".github/workflows/validate.yml",
            ".forgejo/workflows/ci.yml",
            ".checkyourself/challenges.json",
            ".checkyourself.yml",
            "Dockerfile",
            "package.json",
        ):
            self.assertTrue(any(fnmatch.fnmatchcase(sensitive, item["pattern"]) for item in policy["paths"]), sensitive)

    def test_read_first_and_one_page(self):
        instructions = (ROOT / "AGENTS.md").read_text()
        self.assertIn("Before any card", instructions)
        for name in ("PRODUCT.md", "ARCHITECTURE.md"):
            self.assertIn(name, instructions)
            self.assertTrue((ROOT / name).is_file())
        self.assertLessEqual(len((ROOT / "ARCHITECTURE.md").read_text().split()), 600)
