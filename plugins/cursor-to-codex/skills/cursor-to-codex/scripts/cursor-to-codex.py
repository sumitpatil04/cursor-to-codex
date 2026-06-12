#!/usr/bin/env python3
"""Thin entry-point shim for the cursor-to-codex migrator.

Ensures the bundled ``scripts/`` directory is importable, then delegates to
``cli.main``. Run directly with no install required:

    python3 cursor-to-codex.py --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
