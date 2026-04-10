"""Tests for the muninn-remembers CLI entry point."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def test_install_opencode_creates_skill_directories(tmp_path):
    """install opencode copies each skill as a subdirectory with SKILL.md."""
    from muninn_mcp.cli import _install_opencode

    target = tmp_path / "skills"
    _install_opencode(target=target)

    assert (target / "memory-read" / "SKILL.md").exists()
    assert (target / "memory-write" / "SKILL.md").exists()
    assert (target / "symbol-search" / "SKILL.md").exists()


def test_install_opencode_creates_target_directory_if_missing(tmp_path):
    """install opencode creates the target directory if it does not exist."""
    from muninn_mcp.cli import _install_opencode

    target = tmp_path / "does" / "not" / "exist"
    assert not target.exists()
    _install_opencode(target=target)
    assert target.exists()


def test_install_opencode_overwrites_existing_files(tmp_path):
    """install opencode overwrites existing SKILL.md files without error."""
    from muninn_mcp.cli import _install_opencode

    target = tmp_path / "skills"
    existing = target / "memory-read" / "SKILL.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("old content")

    _install_opencode(target=target)

    assert existing.read_text() != "old content"


def test_install_claude_creates_flat_command_files(tmp_path):
    """install claude copies each skill as a flat <name>.md file."""
    from muninn_mcp.cli import _install_claude

    target = tmp_path / "commands"
    _install_claude(target=target)

    assert (target / "memory-read.md").exists()
    assert (target / "memory-write.md").exists()
    assert (target / "symbol-search.md").exists()


def test_install_claude_creates_target_directory_if_missing(tmp_path):
    """install claude creates the target directory if it does not exist."""
    from muninn_mcp.cli import _install_claude

    target = tmp_path / "does" / "not" / "exist"
    assert not target.exists()
    _install_claude(target=target)
    assert target.exists()


def test_install_claude_file_content_matches_skill_md(tmp_path):
    """install claude copies SKILL.md content verbatim."""
    from muninn_mcp.cli import _install_claude
    from muninn_mcp import cli as cli_module

    target = tmp_path / "commands"
    _install_claude(target=target)

    source = Path(cli_module.__file__).parent / "skills" / "memory-read" / "SKILL.md"
    assert (target / "memory-read.md").read_text() == source.read_text()


def test_install_no_target_shows_usage_and_exits(capsys):
    """bare 'install' with no target prints usage with both options and exits 1."""
    from muninn_mcp.cli import main

    with patch.object(sys, "argv", ["muninn-remembers", "install"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "opencode" in captured.err
    assert "claude" in captured.err


def test_install_unknown_target_exits_with_error(capsys):
    """install with an unknown target exits 1 with an error message."""
    from muninn_mcp.cli import main

    with patch.object(sys, "argv", ["muninn-remembers", "install", "vscode"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
    assert "vscode" in capsys.readouterr().err


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


def test_main_server_start_catches_chromadb_import_error(capsys, monkeypatch):
    """main() exits 1 with a clear message when chromadb.api.rust is not importable.

    This guards against a race condition where the venv is partially populated
    (e.g. during a concurrent `uv sync`) and the Rust backend module is missing.
    """
    from muninn_mcp import cli as cli_module

    def _broken_import(name, *args, **kwargs):
        if name == "muninn_mcp.server":
            raise ModuleNotFoundError("No module named 'chromadb.api.rust'")
        return original_import(name, *args, **kwargs)

    original_import = (
        __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__
    )

    monkeypatch.setattr("builtins.__import__", _broken_import)

    with patch.object(sys, "argv", ["muninn-remembers"]):
        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "chromadb" in captured.err.lower()
    assert "uv sync" in captured.err
