"""
muninn_mcp/cli.py — Entry point for the muninn-remembers command.

Usage:
    uvx muninn-remembers            # Start the MCP server (stdio transport)
    uvx muninn-remembers install    # Copy skill files to ~/.config/opencode/skills/
"""

import shutil
import sys
from pathlib import Path


def _install_skills(target: Path | None = None) -> None:
    """Copy bundled skill directories to *target* (default: ~/.config/opencode/skills/)."""
    if target is None:
        target = Path.home() / ".config" / "opencode" / "skills"
    skills_dir = Path(__file__).parent / "skills"
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        dest = target / skill_dir.name
        dest.mkdir(parents=True, exist_ok=True)
        for f in skill_dir.iterdir():
            shutil.copy2(str(f), str(dest / f.name))
            print(f"Installed: {dest / f.name}")
    print(f"\nSkills installed to: {target}")


def main() -> None:
    if len(sys.argv) > 1:
        if sys.argv[1] == "install":
            _install_skills()
        else:
            print(f"Unknown command: {sys.argv[1]!r}", file=sys.stderr)
            print("Usage: muninn-remembers [install]", file=sys.stderr)
            sys.exit(1)
    else:
        from muninn_mcp.server import mcp
        mcp.run()
