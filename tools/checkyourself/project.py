"""The init verb: starter generated files for a target project."""

from __future__ import annotations

from pathlib import Path
import json
from typing import List
from .constants import TOOL_NAME
from .coverage import coverage_emit
from .errors import CliError
from .output import safe_write_text
from .report import render_markdown
from .scan import scan


def init_project(project: Path, force: bool = False) -> dict:
    project = project.resolve()
    if not project.is_dir():
        raise CliError(f"project root not found: {project}")
    created: List[str] = []
    skipped: List[str] = []
    coverage_path = project / "CHECKYOURSELF_COVERAGE.generated.json"
    context_path = project / "CHECKYOURSELF_PROJECT_CONTEXT.generated.md"
    targets = [
        (coverage_path, json.dumps(coverage_emit(str(project)), indent=2) + "\n"),
        (context_path, render_markdown(project, scan(project))),
    ]
    for path, body in targets:
        if path.exists() and not force:
            skipped.append(str(path))
            continue
        safe_write_text(path, body)
        created.append(str(path))
    return {
        "tool": TOOL_NAME,
        "schema": "checkyourself-init/1",
        "project": str(project),
        "created": created,
        "skipped": skipped,
    }
