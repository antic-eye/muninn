"""
muninn_mcp/cli.py — Entry point for the muninn-remembers command.

Usage:
    uvx muninn-remembers                    # Start the MCP server (stdio transport)
    uvx muninn-remembers install opencode   # Install skills to ~/.config/opencode/skills/
    uvx muninn-remembers install claude     # Install skills to ~/.claude/commands/
"""

import shutil
import sys
from pathlib import Path


def _install_opencode(target: Path | None = None) -> None:
    """Install skills as OpenCode skill directories (each a folder containing SKILL.md)."""
    if target is None:
        target = Path.home() / ".config" / "opencode" / "skills"
    skills_dir = Path(__file__).parent / "skills"
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        dest = target / skill_dir.name
        dest.mkdir(parents=True, exist_ok=True)
        for f in skill_dir.iterdir():
            shutil.copy2(str(f), str(dest / f.name))
            print(f"Installed: {dest / f.name}")
    print(f"\nSkills installed to: {target}")


def _install_claude(target: Path | None = None) -> None:
    """Install skills as Claude Code slash commands (flat <name>.md files)."""
    if target is None:
        target = Path.home() / ".claude" / "commands"
    target.mkdir(parents=True, exist_ok=True)
    skills_dir = Path(__file__).parent / "skills"
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            dest = target / f"{skill_dir.name}.md"
            shutil.copy2(str(skill_md), str(dest))
            print(f"Installed: {dest}")
    print(f"\nCommands installed to: {target}")


def main() -> None:
    if len(sys.argv) > 1:
        if sys.argv[1] == "install":
            if len(sys.argv) > 2:
                target = sys.argv[2]
                if target == "opencode":
                    _install_opencode()
                elif target == "claude":
                    _install_claude()
                else:
                    print(f"Unknown install target: {target!r}", file=sys.stderr)
                    print("Usage: muninn-remembers install [opencode|claude]", file=sys.stderr)
                    sys.exit(1)
            else:
                print("Usage: muninn-remembers install [opencode|claude]", file=sys.stderr)
                print("  opencode  — install to ~/.config/opencode/skills/", file=sys.stderr)
                print("  claude    — install to ~/.claude/commands/", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Unknown command: {sys.argv[1]!r}", file=sys.stderr)
            print("Usage: muninn-remembers [install opencode|install claude]", file=sys.stderr)
            sys.exit(1)
    else:
        from muninn_mcp.server import mcp
        mcp.run()
