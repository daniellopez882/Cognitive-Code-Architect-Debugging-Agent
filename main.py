#!/usr/bin/env python3
"""
Entry point.

The repository previously carried two divergent copies of the same system: a
394-line tree at the root (graph.py, state.py, agents/, utils/) and a
1422-line tree under src/. They were not in sync, the README documented
`python main.py` while CI ran `python src/main.py`, and only the src/ tree
imported successfully -- the root tree needed a dependency that was never
installed.

The root duplicates are gone. This shim keeps the documented invocation
working and delegates to the one implementation.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC))

from main import cli

if __name__ == "__main__":
    cli()
