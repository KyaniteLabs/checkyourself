#!/usr/bin/env python3
"""CheckYourself local CLI and thin MCP wrapper — compatibility launcher.

The implementation now lives in the tools/checkyourself/ package (engine
modules split by verb behind a re-export facade). This launcher keeps the
documented `python3 tools/checkyourself.py <verb>` entry working verbatim
for the CLI, the npm bin wrapper, CI, and file-path module loaders.

Standard library only. No network. No telemetry. Secret values are never printed.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.checkyourself import *  # noqa: F401,F403 — full facade re-export
from tools.checkyourself import main

if __name__ == "__main__":
    raise SystemExit(main())
