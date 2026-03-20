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

    name = Path(os.getcwd()).name
    if not name or name == ".":
        raise RuntimeError("Could not determine a valid project name from any source")
    return name


def sanitise_collection_name(project_name: str) -> str:
    """
    Return a ChromaDB-safe collection name.

    ChromaDB rules: 3-63 chars, alphanumeric + hyphens/underscores,
    must start/end with alphanumeric.

    Raises ValueError if project_name is empty or has no alphanumeric characters.
    """
    if not project_name or not project_name.strip():
        raise ValueError("project_name must not be empty")
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", project_name)
    if not re.search(r"[a-zA-Z0-9]", safe):
        raise ValueError(
            f"project_name contains no alphanumeric characters after sanitisation: {project_name!r}"
        )
    prefixed = f"muninn_{safe}"
    truncated = prefixed[:63].rstrip("_-")
    if len(truncated) < 3:
        raise ValueError(
            f"Sanitised collection name too short after cleaning: {truncated!r}"
        )
    return truncated
