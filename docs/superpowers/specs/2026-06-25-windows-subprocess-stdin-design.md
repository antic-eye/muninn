# Windows subprocess stdin Deadlock — Design

**Status:** Proposed
**Date:** 2026-06-25
**Affects:** `muninn-remembers` ≤ 0.1.6 on Windows hosts

---

## Problem

On Windows, calling `memory_write` (and any other tool that triggers a git lookup) hangs until the OpenCode MCP client times out with `-32001`. On macOS/Linux the same code path returns in milliseconds. The asymmetric symptom — reads succeed, writes hang — is the diagnostic key.

### Root cause

Muninn shells out to `git` in three places using `subprocess.check_output(...)`:

| File | Line | Command | Trigger |
| --- | --- | --- | --- |
| `src/muninn_mcp/project.py` | 27 | `git rev-parse --show-toplevel` | every tool call without `MUNINN_PROJECT` env var |
| `src/muninn_mcp/server.py` | 526 | `git rev-parse --abbrev-ref HEAD` | every write (`handle_memory_write`) |
| `src/muninn_mcp/server.py` | 534 | `git rev-parse --short HEAD` | every write (`handle_memory_write`) |

Each call passes `stderr=subprocess.DEVNULL` but **does not** redirect `stdin`. When `stdin` is unspecified, the child process inherits the parent's stdin handle. The MCP stdio transport keeps that pipe open for the lifetime of the server.

| Platform | Inherited stdin behaviour | Outcome |
| --- | --- | --- |
| macOS / Linux | `git rev-parse` does not read stdin; the OS lets the inherited pipe handle dangle harmlessly | exits in ~10ms |
| Windows | Windows pipe-handle inheritance semantics cause `git` to block on the inherited handle until it sees EOF | deadlocks until the MCP client gives up |

The parent (Muninn) is blocked in `check_output` waiting for `git`, which never returns. The MCP request hangs, OpenCode times out.

### Why reads worked but writes didn't (on Windows)

- `handle_memory_search` / `handle_memory_list` / `handle_memory_delete` only call `detect_project_name()` → which hits git **unless** `MUNINN_PROJECT` is set. Users who set `MUNINN_PROJECT` unknowingly bypassed the read-side deadlock.
- `handle_memory_write` additionally calls `_git_info()` unconditionally → both `_git_info` calls hit git regardless of env vars → always deadlocks on Windows.

This matches the user-reported asymmetry exactly.

---

## Fix

Pass `stdin=subprocess.DEVNULL` on every `subprocess.check_output` call that spawns `git`. This is the canonical, documented mitigation for the "child inherits parent stdin and blocks" Python subprocess footgun.

```python
subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"],
    stderr=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL,
)
```

### Why this fix and not others

- **Why not `timeout=`?** A timeout converts a hang into a slow failure, but write latency would jump from ms to seconds on every Windows write. Wrong layer.
- **Why not `CREATE_NO_WINDOW` / `startupinfo`?** Those address console-window flashing, not handle inheritance. Doesn't fix the deadlock.
- **Why not `close_fds=True`?** It already defaults to `True` in Python 3.7+, but on Windows it has no effect on the standard handles (stdin/stdout/stderr) — only on extra inheritable handles. Doesn't fix the deadlock.
- **Why not vendor `pygit2` / `dulwich`?** Adds a heavyweight dependency for two `rev-parse` calls. The one-line fix is strictly better.
- **Why not skip git entirely on Windows?** Loses branch/commit tagging for Windows users. Unnecessary regression.

### Scope decision

The fix is narrow on purpose: only the three sites that currently spawn `git`. We do not introduce a wrapper helper unless additional `subprocess` call sites appear later. The existing code uses `subprocess.check_output` directly, and changing one keyword argument per site is clearer than indirection.

---

## Verification strategy

1. **Unit tests assert the `stdin` kwarg is passed.** Extend the existing `tests/test_muninn_project.py` patches so they assert the call was made with `stdin=subprocess.DEVNULL`. Add an analogous test file for `_git_info()` in `src/muninn_mcp/server.py`.
2. **Regression test for the asymmetric symptom.** Confirm that `handle_memory_write` does not raise when `_git_info` returns `("", "")` (e.g. outside a git repo), so the fix preserves the existing graceful-fallback behaviour.
3. **Manual Windows smoke test (out of band).** The user who reported the bug can re-run `memory_write` from OpenCode on Windows after `pip install muninn-remembers==<new>` and confirm the call returns in ms.

---

## Release

This is a defect fix that affects Windows users. Bump patch version `0.1.6 → 0.1.7` and let the existing CI workflow publish to PyPI on GitHub release (per commit `a4fe2e0`).

---

## Out of scope

- Refactoring subprocess calls into a helper module (only three sites; not worth the indirection today).
- Adding a global subprocess monkeypatch in the launcher (the upstream fix is cleaner and survives future call sites).
- Replacing `git` shell-outs with a library (`pygit2`, `dulwich`) — disproportionate.
- Reporting upstream: this *is* the upstream fix.
