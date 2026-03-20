import os
import subprocess
from unittest.mock import patch, MagicMock
import pytest

# Add parent dir to path so we can import muninn_project
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from muninn_project import detect_project_name, sanitise_collection_name


class TestDetectProjectName:
    def test_env_var_override_wins(self, monkeypatch):
        monkeypatch.setenv("MUNINN_PROJECT", "my-override")
        assert detect_project_name() == "my-override"

    def test_git_root_used_when_no_env(self, monkeypatch):
        monkeypatch.delenv("MUNINN_PROJECT", raising=False)
        with patch(
            "subprocess.check_output", return_value=b"/home/user/projects/my-repo\n"
        ):
            assert detect_project_name() == "my-repo"

    def test_falls_back_to_cwd_basename(self, monkeypatch, tmp_path):
        monkeypatch.delenv("MUNINN_PROJECT", raising=False)
        (tmp_path / "some-project").mkdir(exist_ok=True)
        monkeypatch.chdir(tmp_path / "some-project")
        with patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(128, "git"),
        ):
            name = detect_project_name()
            assert name == "some-project"

    def test_env_var_empty_string_falls_through(self, monkeypatch):
        monkeypatch.setenv("MUNINN_PROJECT", "")
        with patch("subprocess.check_output", return_value=b"/home/user/foo\n"):
            assert detect_project_name() == "foo"


class TestSanitiseCollectionName:
    def test_prefix_added(self):
        assert sanitise_collection_name("my-repo").startswith("muninn_")

    def test_special_chars_replaced(self):
        result = sanitise_collection_name("my repo/v2!")
        assert " " not in result
        assert "/" not in result
        assert "!" not in result

    def test_truncated_to_63_chars(self):
        long_name = "a" * 100
        result = sanitise_collection_name(long_name)
        assert len(result) <= 63

    def test_known_input(self):
        assert sanitise_collection_name("opencode-skills") == "muninn_opencode-skills"
