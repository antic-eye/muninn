import subprocess
from unittest.mock import patch, MagicMock
import pytest

from muninn_mcp.project import (
    detect_project_name,
    sanitise_collection_name,
    GLOBAL_PROJECT_NAME,
    GLOBAL_COLLECTION_NAME,
)


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

    def test_falls_back_to_cwd_when_git_not_installed(self, monkeypatch, tmp_path):
        monkeypatch.delenv("MUNINN_PROJECT", raising=False)
        (tmp_path / "some-project").mkdir(exist_ok=True)
        monkeypatch.chdir(tmp_path / "some-project")
        with patch("subprocess.check_output", side_effect=FileNotFoundError):
            assert detect_project_name() == "some-project"


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
        assert result[-1].isalnum(), "Collection name must not end with _ or -"

    def test_known_input(self):
        assert sanitise_collection_name("opencode-skills") == "muninn_opencode-skills"

    def test_trailing_underscore_stripped(self):
        # 55 'a's + '!!' → after sanitise = 55 'a's + '__' → truncated to 63 = ends in '_'
        # Should be stripped
        result = sanitise_collection_name("a" * 55 + "!!")
        assert result[-1].isalnum(), f"Expected alphanumeric end, got: {result[-1]!r}"

    def test_empty_project_name_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            sanitise_collection_name("")

    def test_all_special_chars_raises(self):
        with pytest.raises(ValueError, match="no alphanumeric"):
            sanitise_collection_name("!!!")

    def test_truncated_ends_with_alnum(self):
        long_name = "a" * 100
        result = sanitise_collection_name(long_name)
        assert len(result) <= 63
        assert result[-1].isalnum()


def test_global_constants_exist():
    assert GLOBAL_PROJECT_NAME == "__global__"
    assert GLOBAL_COLLECTION_NAME == "muninn___global"
    assert GLOBAL_COLLECTION_NAME == sanitise_collection_name(GLOBAL_PROJECT_NAME), (
        "GLOBAL_COLLECTION_NAME must match what sanitise_collection_name produces"
    )
