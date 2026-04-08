"""Tests for the muninn-remembers CLI entry point."""

import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def test_install_creates_skill_directories(tmp_path):
    """install subcommand copies each skill directory to the target location."""
    from muninn_mcp.cli import _install_skills

    target = tmp_path / ".config" / "opencode" / "skills"
    _install_skills(target=target)

    assert (target / "memory-read" / "SKILL.md").exists()
    assert (target / "memory-write" / "SKILL.md").exists()
    assert (target / "symbol-search" / "SKILL.md").exists()


def test_install_creates_target_directory_if_missing(tmp_path):
    """install creates the target directory if it does not exist."""
    from muninn_mcp.cli import _install_skills

    target = tmp_path / "does" / "not" / "exist"
    assert not target.exists()
    _install_skills(target=target)
    assert target.exists()


def test_install_overwrites_existing_files(tmp_path):
    """install overwrites existing SKILL.md files without error."""
    from muninn_mcp.cli import _install_skills

    target = tmp_path / "skills"
    target.mkdir(parents=True)
    existing = target / "memory-read" / "SKILL.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("old content")

    _install_skills(target=target)

    assert existing.read_text() != "old content"


def test_unknown_subcommand_exits_with_error(capsys):
    """Unknown subcommands print an error and exit 1 instead of starting the server."""
    from muninn_mcp.cli import main

    with patch.object(sys, "argv", ["muninn-remembers", "badcommand"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Unknown command" in captured.err
    assert "badcommand" in captured.err
