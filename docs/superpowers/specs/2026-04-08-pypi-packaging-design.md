# PyPI Packaging Design for muninn-mcp

**Date:** 2026-04-08  
**Status:** Approved

## Goal

Publish Muninn to PyPI as `muninn-mcp` so users can run the MCP server via `uvx muninn-mcp` and install companion skills via `uvx muninn-mcp install`, eliminating the need to clone the repo and manage absolute paths.

---

## Repository Layout

```
muninn/
  src/
    muninn_mcp/
      __init__.py
      server.py          # MCP tool registrations (from shared/muninn.py)
      chroma.py          # ChromaDB helpers (from shared/muninn_chroma.py)
      embed.py           # Embedding client (from shared/muninn_embed.py)
      project.py         # Project detection (from shared/muninn_project.py)
      cli.py             # Entry point: starts server or runs install subcommand
      skills/            # Bundled copies of skill files
        memory-read
        memory-write
        symbol-search
  tests/                 # Moved from shared/tests/
  pyproject.toml
  .github/
    workflows/
      publish.yml
```

The existing `shared/` directory is replaced by the `src/muninn_mcp/` package. Internal imports change from `import muninn_chroma as mc` to `from muninn_mcp import chroma as mc` (or relative imports).

---

## `pyproject.toml`

```toml
[project]
name = "muninn-mcp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["mcp[cli]", "chromadb", "httpx"]

[project.scripts]
muninn-mcp = "muninn_mcp.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/muninn_mcp"]
```

The PEP 723 `# /// script` block in `muninn.py` is removed — dependencies are now declared in `pyproject.toml`.

---

## CLI Entry Point (`cli.py`)

`muninn_mcp.cli:main` is the single entry point:

- **No arguments / server mode** (`uvx muninn-mcp`): calls FastMCP's `mcp.run()`, starting the MCP server over stdio — identical behaviour to current `uv run muninn.py`.
- **Install subcommand** (`uvx muninn-mcp install`): copies bundled skill files from `src/muninn_mcp/skills/` to `~/.config/opencode/skills/`, printing each file installed. Creates the target directory if it does not exist.

---

## opencode.json Change

Users update their config from:

```json
"command": ["uv", "run", "/absolute/path/to/shared/muninn.py"]
```

to:

```json
"command": ["uvx", "muninn-mcp"]
```

---

## GitHub Actions — Automated Publishing

File: `.github/workflows/publish.yml`

Triggers on `v*` tag pushes. Uses OIDC trusted publishing — no API secrets stored in GitHub.

```yaml
on:
  push:
    tags: ["v*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

To publish a release: `git tag v0.1.0 && git push --tags`.

---

## PyPI One-Time Setup (manual, done by maintainer)

1. Create account at pypi.org
2. Register the project name `muninn-mcp` (happens automatically on first successful publish)
3. In pypi.org → Account → Publishing → add a Trusted Publisher:
   - Owner: `antic-eye`
   - Repository: `muninn` (or whatever the public repo name is)
   - Workflow: `publish.yml`
   - Environment: *(leave blank)*

After this, the GitHub Actions workflow can publish without any stored secrets.

---

## Tests

Existing tests in `shared/tests/` move to `tests/` at the repo root. Import paths update to match the new package structure. No new tests are required beyond what exists.

---

## Out of Scope

- Changing any MCP tool behaviour or semantics
- Publishing skills to a registry (skills remain file-based, installed via `uvx muninn-mcp install`)
- Supporting Python < 3.10
