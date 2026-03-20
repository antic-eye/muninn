"""
muninn_project.py — Project name detection for Muninn.

Priority:
  1. MUNINN_PROJECT env var (explicit override)
  2. git rev-parse --show-toplevel  → basename
  3. os.getcwd() → basename
"""

import os
import re
import subprocess
from pathlib import Path


def detect_project_name() -> str:
    """Return the current project name using priority-ordered detection."""
    env = os.environ.get("MUNINN_PROJECT", "").strip()
    if env:
        return env

    try:
        raw = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        )
        return Path(raw.decode().strip()).name
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return Path(os.getcwd()).name


def sanitise_collection_name(project_name: str) -> str:
    """
    Return a ChromaDB-safe collection name.

    ChromaDB rules: 3-63 chars, alphanumeric + hyphens/underscores,
    must start/end with alphanumeric.
    """
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", project_name)
    prefixed = f"muninn_{safe}"
    return prefixed[:63]
