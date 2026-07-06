# Windows Subprocess stdin Deadlock — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the Windows `memory_write` deadlock by passing `stdin=subprocess.DEVNULL` to every `git` subprocess call in Muninn, add regression tests, and ship `0.1.7`.

**Design doc:** [`docs/superpowers/specs/2026-06-25-windows-subprocess-stdin-design.md`](../specs/2026-06-25-windows-subprocess-stdin-design.md)

**Architecture:** Surgical one-keyword-argument fix at three known call sites (`detect_project_name` and both `_git_info` calls). No refactor, no new helper, no new dependency. Tests assert the fix is present so it cannot silently regress.

**Tech Stack:** Python 3.10+, `subprocess` stdlib, pytest, unittest.mock

---

### Task 1: Fix `detect_project_name` git call

**Files:**
- Modify: `src/muninn_mcp/project.py`

- [ ] **Step 1: Add `stdin=subprocess.DEVNULL` to the git rev-parse call**

In `detect_project_name()`, change:

```python
raw = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"],
    stderr=subprocess.DEVNULL,
)
```

to:

```python
raw = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"],
    stderr=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL,
)
```

- [ ] **Step 2: Verify**

Run `uv run pytest tests/test_muninn_project.py -v`. Existing tests still pass (they patch `subprocess.check_output` so they don't care about the new kwarg). Confirm with `uv run python -c "from muninn_mcp.project import detect_project_name; print(detect_project_name())"` that the function still returns the repo name.

---

### Task 2: Fix `_git_info` (two call sites)

**Files:**
- Modify: `src/muninn_mcp/server.py`

- [ ] **Step 1: Add `stdin=subprocess.DEVNULL` to both `subprocess.check_output` calls inside `_git_info()`**

In `src/muninn_mcp/server.py`, locate `_git_info()` (around line 522) and update both calls:

```python
branch = (
    subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    .decode()
    .strip()
)
commit = (
    subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    .decode()
    .strip()
)
```

- [ ] **Step 2: Verify**

Run `uv run python -c "from muninn_mcp.server import _git_info; print(_git_info())"` and confirm it returns a `(branch, commit)` tuple for the current repo. Run pylint to confirm no new warnings: `uv run pylint src/muninn_mcp/server.py`.

---

### Task 3: Add regression tests for `stdin` kwarg

**Files:**
- Modify: `tests/test_muninn_project.py`
- Create: `tests/test_git_info.py`

- [ ] **Step 1: Strengthen the existing project-detection test to assert `stdin=DEVNULL` is passed**

In `tests/test_muninn_project.py`, in `TestDetectProjectName::test_git_root_used_when_no_env`, change the `patch` block so the mock object is captured and asserted on:

```python
def test_git_root_used_when_no_env(self, monkeypatch):
    monkeypatch.delenv("MUNINN_PROJECT", raising=False)
    with patch(
        "subprocess.check_output", return_value=b"/home/user/projects/my-repo\n"
    ) as mock_co:
        assert detect_project_name() == "my-repo"
        mock_co.assert_called_once()
        kwargs = mock_co.call_args.kwargs
        assert kwargs.get("stdin") == subprocess.DEVNULL, (
            "detect_project_name must pass stdin=subprocess.DEVNULL to avoid "
            "Windows pipe-handle inheritance deadlocks"
        )
```

- [ ] **Step 2: Add a new test module for `_git_info`**

Create `tests/test_git_info.py`:

```python
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
```

- [ ] **Step 3: Verify**

Run the full test suite:

```
uv run pytest -v
```

All tests pass. The two new `*_passes_stdin_devnull*` / `*stdin_devnull*` tests fail if anyone later regresses the fix.

---

### Task 4: Bump version and prepare release notes

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Bump patch version**

In `pyproject.toml`, change `version = "0.1.6"` to `version = "0.1.7"`.

- [ ] **Step 2: Refresh lockfile**

Run `uv sync` to refresh `uv.lock` (no dependency changes; this just bumps the local project version entry).

- [ ] **Step 3: Verify build still works**

Run `uv build` and confirm `dist/muninn_remembers-0.1.7-py3-none-any.whl` is produced.

---

### Task 5: Commit and release

**Files:** N/A (git/CI operations)

- [ ] **Step 1: Stage and commit the fix**

```
git add src/muninn_mcp/project.py src/muninn_mcp/server.py \
        tests/test_muninn_project.py tests/test_git_info.py \
        pyproject.toml uv.lock \
        docs/superpowers/specs/2026-06-25-windows-subprocess-stdin-design.md \
        docs/superpowers/plans/2026-06-25-windows-subprocess-stdin.md
git commit -m "fix(windows): pass stdin=DEVNULL to git subprocess calls to avoid pipe-inheritance deadlock"
```

- [ ] **Step 2: Tag and create a GitHub release**

Per commit `a4fe2e0`, PyPI publishing is triggered by a GitHub Release (not by tag push). Create release `v0.1.7` from the GitHub UI or via `gh release create v0.1.7 --generate-notes`. CI will publish the wheel to PyPI.

- [ ] **Step 3: Ask the original Windows reporter to validate**

After the wheel is on PyPI, ask the reporter to `pip install --upgrade muninn-remembers` and re-run `memory_write` from OpenCode on Windows. Expected: returns in <100ms, no `-32001` timeout.

---

## Rollback

If any test fails or the Windows reporter still sees a deadlock, the change is contained to four small edits and a version bump. Revert with `git revert <commit>` and re-release as `0.1.8`.
