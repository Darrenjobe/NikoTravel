"""Ὁδηγός backend package.

Fail fast, and readably, on an unsupported interpreter. Without this guard a
too-old Python surfaces as a Pydantic "Unable to evaluate type annotation
'float | None'" traceback, which points at the wrong problem — the annotations
are fine; the interpreter is too old to evaluate them (PEP 604 unions need
3.10+). macOS ships 3.9 with the Command Line Tools, so this is easy to hit.
"""

import sys

MIN_PYTHON = (3, 11)

if sys.version_info < MIN_PYTHON:
    raise RuntimeError(
        f"Ὁδηγός needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ "
        f"(production runs 3.12); this interpreter is "
        f"{sys.version_info.major}.{sys.version_info.minor} at {sys.executable}.\n"
        "\n"
        "On macOS the Command Line Tools Python is 3.9 — install a newer one\n"
        "and rebuild the virtualenv:\n"
        "\n"
        "    brew install python@3.12\n"
        "    cd backend && rm -rf .venv\n"
        "    python3.12 -m venv .venv\n"
        "    source .venv/bin/activate\n"
        "    pip install -r requirements.txt\n"
    )
