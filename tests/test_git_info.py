"""Regression tests for muninn_mcp.server._git_info subprocess safety.

The fix that this file guards is documented in
docs/superpowers/specs/2026-06-25-windows-subprocess-stdin-design.md:
every git subprocess call must pass stdin=subprocess.DEVNULL to avoid the
Windows pipe-handle inheritance deadlock that hangs memory_write.
"""

import subprocess
from unittest.mock import patch

from muninn_mcp.server import _git_info


class TestGitInfoSubprocessSafety:
    def test_returns_branch_and_commit(self):
        with patch(
            "subprocess.check_output",
            side_effect=[b"main\n", b"abc1234\n"],
        ):
            assert _git_info() == ("main", "abc1234")

    def test_passes_stdin_devnull_on_every_call(self):
        with patch(
            "subprocess.check_output",
            side_effect=[b"main\n", b"abc1234\n"],
        ) as mock_co:
            _git_info()
            assert mock_co.call_count == 2
            for call in mock_co.call_args_list:
                assert call.kwargs.get("stdin") == subprocess.DEVNULL, (
                    "_git_info must pass stdin=subprocess.DEVNULL on every "
                    "git subprocess call to avoid Windows pipe-handle "
                    "inheritance deadlocks (see "
                    "docs/superpowers/specs/2026-06-25-windows-subprocess-stdin-design.md)"
                )

    def test_returns_empty_on_called_process_error(self):
        with patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(128, "git"),
        ):
            assert _git_info() == ("", "")

    def test_returns_empty_on_file_not_found(self):
        with patch("subprocess.check_output", side_effect=FileNotFoundError):
            assert _git_info() == ("", "")
