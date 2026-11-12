"""File-tree walking, stack detection, gitignore handling, and inventory helpers."""

from __future__ import annotations

from pathlib import Path
import fnmatch
import json
import os
from typing import Dict, List, Optional, Tuple
from .constants import DEPENDENCY_HINTS, ENV_EXAMPLE_NAMES, IGNORED_DIRS, RISK_PATH_HINTS, STACK_FILES
from .util import read_text, redact_sensitive_text, rel


DEFAULT_MAX_FILES = 6000


def keep_dir(parent: Path, name: str) -> bool:
    if name in IGNORED_DIRS:
        return False
    if name.startswith(".") and name != ".github":
        return False
    # Never descend symlinked directories: they can escape the project tree.
    return not (parent / name).is_symlink()


def iter_files(root: Path, limit: int = DEFAULT_MAX_FILES) -> Tuple[List[Path], dict]:
    root = root.resolve()
    files: List[Path] = []
    stats = {
        "max_files": limit,
        "truncated": False,
        "files_beyond_limit": 0,
        "symlinks_skipped": 0,
        "symlink_dirs_skipped": 0,
        "files_oversized": 0,
        "files_unreadable": 0,
        "content_truncated": 0,
        "skipped_files": [],
        "oversized_files": [],
        "unreadable_files": [],
        "truncated_files": [],
        "incomplete": False,
    }
    for dirpath, dirnames, filenames in os.walk(root):
        parent = Path(dirpath)
        # Sorting dirnames keeps walk order deterministic across filesystems.
        kept_dirnames = []
        for dirname in sorted(dirnames):
            if dirname in IGNORED_DIRS or (dirname.startswith(".") and dirname != ".github"):
                continue
            if (parent / dirname).is_symlink():
                stats["symlink_dirs_skipped"] += 1
                stats["skipped_files"].append(rel(root, parent / dirname))
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames
        for name in sorted(filenames):
            p = parent / name
            if p.is_symlink():
                stats["symlinks_skipped"] += 1
                stats["skipped_files"].append(rel(root, p))
                continue
            try:
                real = p.resolve(strict=True)
                real.relative_to(root)
                if real.stat().st_size > 2_000_000:
                    stats["files_oversized"] += 1
                    stats["oversized_files"].append(rel(root, p))
                    continue
            except ValueError:
                # Resolves outside the scanned tree (e.g. via a parent link).
                stats["symlinks_skipped"] += 1
                stats["skipped_files"].append(rel(root, p))
                continue
            except RuntimeError:
                # Symlink loops can make Path.resolve fail without an OSError.
                stats["symlinks_skipped"] += 1
                stats["skipped_files"].append(rel(root, p))
                continue
            except OSError:
                stats["files_unreadable"] += 1
                stats["unreadable_files"].append(rel(root, p))
                continue
            if len(files) >= limit:
                stats["truncated"] = True
                stats["files_beyond_limit"] += 1
                stats["truncated_files"].append(rel(root, p))
                continue
            files.append(p)
    stats["skipped_files"] = sorted(set(stats["skipped_files"]))
    stats["oversized_files"] = sorted(set(stats["oversized_files"]))
    stats["unreadable_files"] = sorted(set(stats["unreadable_files"]))
    stats["truncated_files"] = sorted(set(stats["truncated_files"]))
    stats["incomplete"] = bool(
        stats["truncated"]
        or stats["symlinks_skipped"]
        or stats["symlink_dirs_skipped"]
        or stats["files_oversized"]
        or stats["files_unreadable"]
    )
    return files, stats


def detect_stack(root: Path) -> Tuple[List[str], Dict[str, str], Dict[str, List[str]]]:
    signals: List[str] = []
    scripts: Dict[str, str] = {}
    deps_found: Dict[str, List[str]] = {}

    for key, label in STACK_FILES.items():
        if (root / key).exists():
            signals.append(f"{label}: `{key}`")

    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(read_text(package_json))
            if not isinstance(data, dict):
                signals.append("package.json exists but must contain a JSON object")
                data = {}
            if isinstance(data.get("scripts"), dict):
                scripts = {str(k): redact_sensitive_text(str(v)) for k, v in sorted(data["scripts"].items())}
            deps: Dict[str, str] = {}
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                if isinstance(data.get(section), dict):
                    deps.update(data[section])
            for dep, label in DEPENDENCY_HINTS.items():
                if dep in deps:
                    deps_found.setdefault(label, []).append(dep)
        except (ValueError, UnicodeError):
            signals.append("package.json exists but could not be parsed")

    py_manifests = ["pyproject.toml", "requirements.txt", "Pipfile"]
    py_text = "\n".join(read_text(root / f) for f in py_manifests if (root / f).exists()).lower()
    for dep, label in DEPENDENCY_HINTS.items():
        if dep.lower() in py_text:
            deps_found.setdefault(label, []).append(dep)

    return sorted(signals), scripts, deps_found


def parse_gitignore_patterns(text: str) -> List[str]:
    patterns: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip(" \t")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(r"\#"):
            line = line[1:]
        patterns.append(line)
    return patterns


def gitignore_entries(root: Path) -> List[str]:
    gi = root / ".gitignore"
    return parse_gitignore_patterns(read_text(gi)) if gi.exists() else []


def _gitignore_pattern_matches(pattern: str, path: str) -> bool:
    rule = pattern[1:] if pattern.startswith("!") else pattern
    if rule.startswith(r"\!"):
        rule = rule[1:]
    directory_only = rule.endswith("/")
    anchored = rule.startswith("/")
    rule = rule.strip("/")
    candidate = path.replace(os.sep, "/")
    if candidate.startswith("./"):
        candidate = candidate[2:]
    candidate = candidate.lstrip("/")
    if not rule or not candidate:
        return False
    if "/" not in rule:
        segments = candidate.split("/")
        if directory_only:
            segments = segments[:-1]
        if anchored:
            return bool(segments) and fnmatch.fnmatchcase("/".join(segments), rule)
        return any(fnmatch.fnmatchcase(segment, rule) for segment in segments)
    parts = candidate.split("/")
    candidates = ["/".join(parts[:index]) for index in range(1, len(parts))]
    if not directory_only:
        candidates.append(candidate)
    if not anchored:
        candidates.extend(
            "/".join(value.split("/")[index:])
            for value in list(candidates)
            for index in range(1, len(value.split("/")))
        )
    return any(fnmatch.fnmatchcase(value, rule) for value in candidates)


def gitignore_ignores_path(patterns: List[str], path: str) -> bool:
    ignored = False
    for pattern in patterns:
        if _gitignore_pattern_matches(pattern, path):
            ignored = not pattern.startswith("!")
    return ignored


def is_env_example_name(name: str) -> bool:
    lower = name.lower()
    return (
        lower in ENV_EXAMPLE_NAMES
        or (lower.startswith((".env.", "env.")) and lower.endswith((".example", ".sample", ".template")))
        or (lower.endswith(".env") and any(token in lower for token in ("example", "sample", "template")))
    )


def classify_env_file(name: str) -> Optional[str]:
    """Classify a file name as an 'example' env file, a 'real' one, or neither."""
    lower = name.lower()
    if is_env_example_name(lower):
        return "example"
    if lower == ".env" or lower.startswith(".env.") or lower.endswith(".env"):
        return "real"
    return None


def is_placeholder_secret_value(value: str) -> bool:
    lower = value.lower().strip("\"'")
    placeholder_tokens = (
        "your_",
        "replace",
        "placeholder",
        "example",
        "sample",
        "changeme",
        "change_me",
        "dummy",
        "fake",
        "redacted",
    )
    return any(token in lower for token in placeholder_tokens)


def find_tests(root: Path, files: List[Path]) -> List[str]:
    test_dirs = {"test", "tests", "spec", "specs", "__tests__", "playwright", "cypress", "e2e"}
    test_extensions = {".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".java", ".rb", ".rs"}
    tests: List[str] = []
    for p in files:
        rp = rel(root, p)
        lower = rp.lower()
        suffix = p.suffix.lower()
        if suffix not in test_extensions:
            continue
        parts = [part.lower() for part in Path(lower).parts]
        stem = p.stem.lower()
        in_test_dir = any(part in test_dirs for part in parts[:-1])
        conventional_name = (
            stem in {"test", "spec"}
            or stem.startswith("test_")
            or stem.endswith("_test")
            or stem.endswith(".test")
            or stem.endswith(".spec")
            or (suffix == ".java" and stem.startswith("test"))
        )
        if in_test_dir or conventional_name:
            tests.append(rp)
    return sorted(set(tests))[:100]


def find_ci(root: Path) -> List[str]:
    ci: List[str] = []
    wf = root / ".github" / "workflows"
    if wf.exists():
        ci.extend(sorted(rel(root, p) for p in wf.glob("*") if p.is_file()))
    for f in (".gitlab-ci.yml", "azure-pipelines.yml", ".circleci/config.yml", "Jenkinsfile"):
        if (root / f).exists():
            ci.append(f)
    return sorted(set(ci))


def _segment_hit(needle: str, segment: str) -> bool:
    """Match a risk hint against one path segment on word boundaries.

    Substring matching produced noise (`rapid/` matched `api`, `user-agent.ts`
    matched `agent`), so hints only match whole segments, simple plurals, and
    boundary-delimited prefixes.
    """
    if segment in (needle, needle + "s", needle + "es"):
        return True
    return segment.startswith((needle + ".", needle + "-", needle + "_", needle + "s.", needle + "es."))


def path_hints(root: Path, files: List[Path]) -> Dict[str, List[str]]:
    hints: Dict[str, List[str]] = {}
    for p in files:
        rp = rel(root, p)
        segments = [s.lower() for s in Path(rp).parts]
        for needle, label in RISK_PATH_HINTS:
            if any(_segment_hit(needle, segment) for segment in segments):
                hints.setdefault(label, []).append(rp)
    return {k: sorted(set(v))[:40] for k, v in sorted(hints.items())}


def tree_sample(root: Path, max_lines: int = 140) -> List[str]:
    lines: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        parent = Path(dirpath)
        dirnames[:] = sorted(d for d in dirnames if keep_dir(parent, d))
        cur = parent
        depth = len(cur.relative_to(root).parts) if cur != root else 0
        if depth > 3:
            dirnames[:] = []
            continue
        indent = "  " * depth
        lines.append("." if cur == root else f"{indent}{cur.name}/")
        for name in sorted(filenames)[:20]:
            lines.append(f"{indent}  {name}")
        if len(lines) >= max_lines:
            lines.append("...truncated...")
            return lines
    return lines
