# PyPI Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Muninn repo into a proper Python package (`muninn-mcp`) publishable to PyPI, runnable via `uvx muninn-mcp`, with a `uvx muninn-mcp install` subcommand that copies companion skills to `~/.config/opencode/skills/`.

**Architecture:** Move `shared/*.py` into `src/muninn_mcp/` with relative imports, add `pyproject.toml` (hatchling build backend), expose a `cli.py` entry point, bundle skill directories as package data, migrate tests to `tests/` at the repo root, and add a GitHub Actions workflow for OIDC-based PyPI publishing on `v*` tags.

**Tech Stack:** Python ≥ 3.10, hatchling, uv, pytest, respx (for embed tests), GitHub Actions + pypa/gh-action-pypi-publish

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `pyproject.toml` | Package metadata, deps, entry point, dev deps, pytest config |
| Create | `src/muninn_mcp/__init__.py` | Package marker (empty) |
| Create | `src/muninn_mcp/project.py` | Project name detection + collection name helpers |
| Create | `src/muninn_mcp/chroma.py` | ChromaDB collection helpers |
| Create | `src/muninn_mcp/embed.py` | Ollama embedding HTTP client |
| Create | `src/muninn_mcp/server.py` | MCP tool registrations + handler functions |
| Create | `src/muninn_mcp/cli.py` | Entry point: server mode or `install` subcommand |
| Create | `src/muninn_mcp/skills/memory-read/SKILL.md` | Bundled skill (copy) |
| Create | `src/muninn_mcp/skills/memory-write/SKILL.md` | Bundled skill (copy) |
| Create | `src/muninn_mcp/skills/symbol-search/SKILL.md` | Bundled skill (copy) |
| Create | `tests/__init__.py` | Test package marker |
| Move+fix | `tests/test_muninn_project.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_muninn_chroma.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_muninn_embed.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_muninn_mcp.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_muninn_e2e.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_global_memory.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_format_output.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_symbol_collection_name.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_delete_symbols_by_file.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_symbol_format.py` | From shared/tests/ — update imports |
| Move+fix | `tests/test_symbol_handlers.py` | From shared/tests/ — update imports |
| Create | `tests/test_cli.py` | Tests for cli.py install subcommand |
| Delete | `shared/` | Replaced by src/muninn_mcp/ |
| Create | `.github/workflows/publish.yml` | Publish to PyPI on v* tag push |
| Modify | `README.md` | Update installation instructions |

---

## Task 1: Create pyproject.toml

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Create pyproject.toml**

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

[dependency-groups]
dev = ["pytest", "respx"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Verify hatchling is available**

Run: `uv tool install hatchling 2>/dev/null || true`

(hatchling is installed automatically by `uv build` — this step is informational.)

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add pyproject.toml for muninn-mcp package"
```

---

## Task 2: Create package skeleton and module files

**Files:**
- Create: `src/muninn_mcp/__init__.py`
- Create: `src/muninn_mcp/project.py`
- Create: `src/muninn_mcp/chroma.py`
- Create: `src/muninn_mcp/embed.py`

These files are copied from `shared/` with the PEP 723 `# /// script` headers removed. No logic changes.

- [ ] **Step 1: Create the package directory and `__init__.py`**

```bash
mkdir -p src/muninn_mcp
touch src/muninn_mcp/__init__.py
```

- [ ] **Step 2: Create `src/muninn_mcp/project.py`**

Copy `shared/muninn_project.py` verbatim — it has no PEP 723 header and no sibling imports, so no changes are needed:

```python
"""
muninn_mcp/project.py — Project name detection and global-memory constants.

Priority:
  1. MUNINN_PROJECT env var (explicit override)
  2. git rev-parse --show-toplevel  → basename
  3. os.getcwd() → basename
"""

import os
import re
import subprocess
from pathlib import Path


def detect_project_name() -> str:
    """Return the current project name using priority-ordered detection."""
    env = os.environ.get("MUNINN_PROJECT", "").strip()
    if env:
        return env

    try:
        raw = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        )
        return Path(raw.decode().strip()).name
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    name = Path(os.getcwd()).name
    if not name or name == ".":
        raise RuntimeError("Could not determine a valid project name from any source")
    return name


def sanitise_collection_name(project_name: str) -> str:
    """
    Return a ChromaDB-safe collection name.

    ChromaDB rules: 3-63 chars, alphanumeric + hyphens/underscores,
    must start/end with alphanumeric.
    """
    if not project_name or not project_name.strip():
        raise ValueError("project_name must not be empty")
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", project_name)
    if not re.search(r"[a-zA-Z0-9]", safe):
        raise ValueError(
            f"project_name contains no alphanumeric characters after sanitisation: {project_name!r}"
        )
    prefixed = f"muninn_{safe}"
    truncated = prefixed[:63].rstrip("_-")
    if len(truncated) < 3:
        raise ValueError(
            f"Sanitised collection name too short after cleaning: {truncated!r}"
        )
    return truncated


GLOBAL_PROJECT_NAME = "__global__"
GLOBAL_COLLECTION_NAME = sanitise_collection_name(GLOBAL_PROJECT_NAME)


def symbol_collection_name(project_name: str) -> str:
    """Return the ChromaDB collection name for the symbol index of a project."""
    raw = f"{project_name}__symbols"
    return sanitise_collection_name(raw)
```

- [ ] **Step 3: Create `src/muninn_mcp/chroma.py`**

Copy `shared/muninn_chroma.py`, removing the PEP 723 header (first 3 lines):

```python
"""
muninn_mcp/chroma.py — ChromaDB collection helpers for Muninn.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb import Collection


DATA_DIR = Path(
    os.environ.get("MUNINN_DATA_DIR", Path.home() / ".config" / "opencode" / "muninn")
)
DEFAULT_TOP_K = int(os.environ.get("MUNINN_TOP_K", "5"))


class MemoryNotFoundError(KeyError):
    """Raised when a memory entry ID is not found in the collection."""


_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    """Return (or create) the persistent ChromaDB client."""
    global _client
    if _client is None:
        chroma_path = DATA_DIR / "chroma"
        chroma_path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(chroma_path))
    return _client


def get_collection(client: chromadb.ClientAPI, name: str) -> Collection:
    """Get or create a named collection."""
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_memory(
    collection: Collection,
    entry_id: str,
    document: str,
    embedding: list[float],
    metadata: dict[str, Any],
) -> None:
    """Insert or update a memory entry."""
    effective_metadata = metadata if metadata else None
    collection.upsert(
        ids=[entry_id],
        documents=[document],
        embeddings=[embedding],
        metadatas=[effective_metadata],
    )


def query_memory(
    collection: Collection,
    query_embedding: list[float],
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    """Semantic search. Returns list of dicts with keys: id, document, metadata, distance."""
    if top_k <= 0:
        raise ValueError(f"top_k must be positive, got {top_k}")
    count = collection.count()
    if count == 0:
        return []

    effective_k = min(top_k, count)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=effective_k,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for i, doc_id in enumerate(results["ids"][0]):
        output.append(
            {
                "id": doc_id,
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
        )
    return output


def list_memories(
    collection: Collection,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return paginated memory entries."""
    if limit <= 0:
        raise ValueError(f"limit must be positive, got {limit}")
    if offset < 0:
        raise ValueError(f"offset must be non-negative, got {offset}")
    results = collection.get(
        limit=limit,
        offset=offset,
        include=["documents", "metadatas"],
    )
    output = []
    for i, doc_id in enumerate(results["ids"]):
        output.append(
            {
                "id": doc_id,
                "document": results["documents"][i],
                "metadata": results["metadatas"][i],
            }
        )
    return output


def delete_memory(collection: Collection, entry_id: str) -> None:
    """Delete a specific memory entry. Raises MemoryNotFoundError if missing."""
    existing = collection.get(ids=[entry_id])
    if not existing["ids"]:
        raise MemoryNotFoundError(f"No memory entry with id '{entry_id}'")
    collection.delete(ids=[entry_id])


def wipe_collection(client: chromadb.ClientAPI, collection_name: str) -> int:
    """Delete all entries in a collection. Returns count deleted."""
    existing_names = [c.name for c in client.list_collections()]
    if collection_name not in existing_names:
        return 0
    col = client.get_collection(collection_name)
    count = col.count()
    if count > 0:
        all_ids = col.get(include=[])["ids"]
        col.delete(ids=all_ids)
    return count


def delete_symbols_by_file(collection: Collection, file_path: str) -> int:
    """Delete all symbol entries for a given file path. Returns count deleted."""
    if collection.count() == 0:
        return 0
    results = collection.get(where={"file": file_path}, include=[])
    ids = results["ids"]
    if not ids:
        return 0
    collection.delete(ids=ids)
    return len(ids)
```

- [ ] **Step 4: Create `src/muninn_mcp/embed.py`**

Copy `shared/muninn_embed.py`, removing the PEP 723 header (first 3 lines):

```python
"""
muninn_mcp/embed.py — Ollama embedding via HTTP for Muninn.

Env vars:
    MUNINN_OLLAMA_URL    Ollama base URL (default: http://localhost:11434)
    MUNINN_EMBED_MODEL   Embedding model  (default: mxbai-embed-large:latest)
    MUNINN_OLLAMA_TOKEN  Bearer token for authenticated Ollama endpoints (optional)

API auto-detection:
    If MUNINN_OLLAMA_URL contains "/v1" the OpenAI-compatible endpoint
    (POST /v1/embeddings) is used.  Otherwise the native Ollama endpoint
    (POST /api/embed) is used.
"""

import os
import httpx


OLLAMA_URL = os.environ.get("MUNINN_OLLAMA_URL", "http://localhost:11434").rstrip("/")
EMBED_MODEL = os.environ.get("MUNINN_EMBED_MODEL", "mxbai-embed-large:latest")
OLLAMA_TOKEN = os.environ.get("MUNINN_OLLAMA_TOKEN", "")


def _build_headers() -> dict[str, str]:
    """Return HTTP headers for Ollama requests, including auth if configured."""
    headers: dict[str, str] = {}
    if OLLAMA_TOKEN:
        headers["Authorization"] = f"Bearer {OLLAMA_TOKEN}"
    return headers


def _is_openai_compat(base_url: str) -> bool:
    """Return True when base_url points to an OpenAI-compatible proxy."""
    return "/v1" in base_url.lower()


class EmbeddingError(RuntimeError):
    """Raised when the Ollama embedding call fails."""


def _call_ollama(base_url: str, model: str, text: str, headers: dict) -> list[float]:
    """Call the native Ollama /api/embed endpoint."""
    url = f"{base_url}/api/embed"
    payload = {"model": model, "input": text}
    response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    try:
        return data["embeddings"][0]
    except (KeyError, IndexError) as exc:
        raise EmbeddingError(f"Unexpected Ollama response shape: {data}") from exc


def _call_openai_compat(
    base_url: str, model: str, text: str, headers: dict
) -> list[float]:
    """Call an OpenAI-compatible /v1/embeddings endpoint."""
    clean_base = base_url.rstrip("/")
    if not clean_base.endswith("/v1"):
        clean_base = f"{clean_base}/v1"
    url = f"{clean_base}/embeddings"
    payload = {"model": model, "input": text}
    response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    try:
        return data["data"][0]["embedding"]
    except (KeyError, IndexError) as exc:
        raise EmbeddingError(
            f"Unexpected OpenAI-compat response shape: {data}"
        ) from exc


def get_embedding(text: str) -> list[float]:
    """Return an embedding vector for text."""
    headers = _build_headers()
    try:
        if _is_openai_compat(OLLAMA_URL):
            return _call_openai_compat(OLLAMA_URL, EMBED_MODEL, text, headers)
        return _call_ollama(OLLAMA_URL, EMBED_MODEL, text, headers)
    except httpx.HTTPStatusError as exc:
        raise EmbeddingError(
            f"Ollama returned {exc.response.status_code} for embed request"
        ) from exc
    except httpx.RequestError as exc:
        raise EmbeddingError(f"Cannot reach Ollama at {OLLAMA_URL}: {exc}") from exc
```

- [ ] **Step 5: Install the package in editable mode**

Run: `uv pip install -e .`

Expected output: `Successfully installed muninn-mcp-0.1.0`

- [ ] **Step 6: Verify imports work**

Run: `uv run python -c "from muninn_mcp import chroma, embed, project; print('OK')"`

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add src/muninn_mcp/
git commit -m "feat: create muninn_mcp package with chroma/embed/project modules"
```

---

## Task 3: Create server.py

**Files:**
- Create: `src/muninn_mcp/server.py`

This is `shared/muninn.py` with three changes:
1. Remove the shebang line (`#!/usr/bin/env python3`) and PEP 723 block (`# /// script ... # ///`)
2. Change the three sibling imports to relative imports
3. Remove the `if __name__ == "__main__": mcp.run()` block (moved to cli.py)

- [ ] **Step 1: Create `src/muninn_mcp/server.py`**

Start the file with:

```python
"""
muninn_mcp/server.py — MCP server entry point for Muninn.

MCP tools exposed (project-scoped):
    memory_write, memory_search, memory_list, memory_delete,
    memory_wipe_project, memory_list_projects

MCP tools exposed (global scope):
    global_memory_write, global_memory_search, global_memory_list,
    global_memory_delete, global_memory_wipe

Symbol index tools:
    symbol_index, symbol_search, symbol_delete_file, symbol_wipe
"""

from __future__ import annotations

import datetime
import hashlib
import subprocess
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import chroma as mc
from . import embed as me
from . import project as mp

mcp = FastMCP("muninn")
```

Then copy the rest of `shared/muninn.py` starting from the handler functions section (line 44 onward), stopping before `if __name__ == "__main__":` (remove that block entirely).

- [ ] **Step 2: Verify server imports**

Run: `uv run python -c "from muninn_mcp.server import mcp; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/muninn_mcp/server.py
git commit -m "feat: add server.py (MCP tool registrations, adapted from shared/muninn.py)"
```

---

## Task 4: Bundle skill files

**Files:**
- Create: `src/muninn_mcp/skills/memory-read/SKILL.md`
- Create: `src/muninn_mcp/skills/memory-write/SKILL.md`
- Create: `src/muninn_mcp/skills/symbol-search/SKILL.md`

- [ ] **Step 1: Create the skills directory structure**

```bash
mkdir -p src/muninn_mcp/skills/memory-read
mkdir -p src/muninn_mcp/skills/memory-write
mkdir -p src/muninn_mcp/skills/symbol-search
```

- [ ] **Step 2: Copy skill files**

```bash
cp memory-read/SKILL.md src/muninn_mcp/skills/memory-read/SKILL.md
cp memory-write/SKILL.md src/muninn_mcp/skills/memory-write/SKILL.md
cp symbol-search/SKILL.md src/muninn_mcp/skills/symbol-search/SKILL.md
```

- [ ] **Step 3: Verify files are present**

Run: `find src/muninn_mcp/skills -name SKILL.md`

Expected output (3 lines):
```
src/muninn_mcp/skills/memory-read/SKILL.md
src/muninn_mcp/skills/memory-write/SKILL.md
src/muninn_mcp/skills/symbol-search/SKILL.md
```

- [ ] **Step 4: Commit**

```bash
git add src/muninn_mcp/skills/
git commit -m "feat: bundle skill files into package"
```

---

## Task 5: Write test for cli.py, then implement cli.py

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_cli.py`
- Create: `src/muninn_mcp/cli.py`

- [ ] **Step 1: Create `tests/__init__.py`**

```bash
touch tests/__init__.py
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_cli.py`:

```python
"""Tests for the muninn-mcp CLI entry point."""

import shutil
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
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`

Expected: FAIL with `ImportError: cannot import name '_install_skills' from 'muninn_mcp.cli'`

- [ ] **Step 4: Implement `src/muninn_mcp/cli.py`**

```python
"""
muninn_mcp/cli.py — Entry point for the muninn-mcp command.

Usage:
    uvx muninn-mcp            # Start the MCP server (stdio transport)
    uvx muninn-mcp install    # Copy skill files to ~/.config/opencode/skills/
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
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        _install_skills()
    else:
        from muninn_mcp.server import mcp
        mcp.run()
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_cli.py -v`

Expected: 3 tests PASS

- [ ] **Step 6: Verify the entry point works**

Run: `uv run muninn-mcp --help 2>&1 | head -5 || uv run python -c "from muninn_mcp.cli import main; print('OK')"`

Expected: `OK` (the server starts and waits for MCP input; Ctrl-C to stop, or just verify no import error)

- [ ] **Step 7: Commit**

```bash
git add tests/__init__.py tests/test_cli.py src/muninn_mcp/cli.py
git commit -m "feat: add cli.py entry point with install subcommand"
```

---

## Task 6: Migrate tests

**Files:**
- Create/Modify: all files under `tests/` (migrated from `shared/tests/`)

The import mapping for every test file:

| Old import | New import |
|---|---|
| `sys.path.insert(0, ...)` | *(delete this line and the os/sys boilerplate above it)* |
| `import muninn_chroma as mc` | `from muninn_mcp import chroma as mc` |
| `from muninn_chroma import X` | `from muninn_mcp.chroma import X` |
| `import muninn_embed` | `from muninn_mcp import embed as muninn_embed` |
| `import muninn_embed as me` | `from muninn_mcp import embed as me` |
| `import muninn_project as mp` | `from muninn_mcp import project as mp` |
| `from muninn_project import X` | `from muninn_mcp.project import X` |
| `from muninn import X` | `from muninn_mcp.server import X` |
| `import muninn_chroma` (inline, inside test) | `from muninn_mcp import chroma as muninn_chroma` |

Files to migrate (11 files):

- `test_muninn_project.py` — imports from `muninn_project`
- `test_muninn_chroma.py` — imports from `muninn_chroma` (inline, inside test methods)
- `test_muninn_embed.py` — `import muninn_embed`
- `test_muninn_mcp.py` — imports from `muninn`, `muninn_chroma`, `muninn_embed`, `muninn_project`
- `test_muninn_e2e.py` — imports from `muninn`, `muninn_chroma`, `muninn_project`
- `test_global_memory.py` — imports from `muninn`, `muninn_chroma`, `muninn_embed`, `muninn_project`
- `test_format_output.py` — `from muninn import (...)`
- `test_symbol_collection_name.py` — `from muninn_project import symbol_collection_name`
- `test_delete_symbols_by_file.py` — `import muninn_chroma as mc`
- `test_symbol_format.py` — `from muninn import (...)`
- `test_symbol_handlers.py` — imports from `muninn`, `muninn_chroma`, `muninn_embed`, `muninn_project`

- [ ] **Step 1: Copy all test files to `tests/`**

```bash
cp shared/tests/test_muninn_project.py tests/
cp shared/tests/test_muninn_chroma.py tests/
cp shared/tests/test_muninn_embed.py tests/
cp shared/tests/test_muninn_mcp.py tests/
cp shared/tests/test_muninn_e2e.py tests/
cp shared/tests/test_global_memory.py tests/
cp shared/tests/test_format_output.py tests/
cp shared/tests/test_symbol_collection_name.py tests/
cp shared/tests/test_delete_symbols_by_file.py tests/
cp shared/tests/test_symbol_format.py tests/
cp shared/tests/test_symbol_handlers.py tests/
```

- [ ] **Step 2: Update `tests/test_muninn_project.py`**

Remove the `import os`, `import sys`, `sys.path.insert(...)` lines (lines 1, 7, 8, 9).

Change:
```python
from muninn_project import (
    detect_project_name,
    sanitise_collection_name,
    GLOBAL_PROJECT_NAME,
    GLOBAL_COLLECTION_NAME,
)
```
To:
```python
from muninn_mcp.project import (
    detect_project_name,
    sanitise_collection_name,
    GLOBAL_PROJECT_NAME,
    GLOBAL_COLLECTION_NAME,
)
```

- [ ] **Step 3: Update `tests/test_muninn_chroma.py`**

Remove the `sys.path.insert` line (and the `import os`, `import sys` lines above it if they exist solely for path manipulation).

Change every occurrence of:
```python
from muninn_chroma import X
```
To:
```python
from muninn_mcp.chroma import X
```

- [ ] **Step 4: Update `tests/test_muninn_embed.py`**

Remove the `import os`, `import sys`, `sys.path.insert(...)` lines.

Change:
```python
import muninn_embed
```
To:
```python
from muninn_mcp import embed as muninn_embed
```

- [ ] **Step 5: Update `tests/test_muninn_mcp.py`**

Remove `import os`, `import sys`, `sys.path.insert(...)`.

Change every occurrence:
```python
import muninn_chroma as mc   →   from muninn_mcp import chroma as mc
import muninn_embed as me    →   from muninn_mcp import embed as me
import muninn_project as mp  →   from muninn_mcp import project as mp
from muninn import X         →   from muninn_mcp.server import X
```

- [ ] **Step 6: Update `tests/test_muninn_e2e.py`**

Remove `import os`, `import sys`, `sys.path.insert(...)`.

Change:
```python
import muninn_chroma as mc   →   from muninn_mcp import chroma as mc
import muninn_project as mp  →   from muninn_mcp import project as mp
from muninn import X         →   from muninn_mcp.server import X
```

- [ ] **Step 7: Update `tests/test_global_memory.py`**

Remove `import os`, `import sys`, `sys.path.insert(...)`.

Change:
```python
import muninn_chroma as mc   →   from muninn_mcp import chroma as mc
import muninn_embed as me    →   from muninn_mcp import embed as me
import muninn_project as mp  →   from muninn_mcp import project as mp
from muninn import X         →   from muninn_mcp.server import X
```

- [ ] **Step 8: Update `tests/test_format_output.py`**

Remove `import os`, `import sys`, `sys.path.insert(...)`.

Change:
```python
from muninn import (...)
```
To:
```python
from muninn_mcp.server import (...)
```

- [ ] **Step 9: Update `tests/test_symbol_collection_name.py`**

Remove `import os`, `import sys`, `sys.path.insert(...)`.

Change:
```python
from muninn_project import symbol_collection_name
```
To:
```python
from muninn_mcp.project import symbol_collection_name
```

- [ ] **Step 10: Update `tests/test_delete_symbols_by_file.py`**

Remove `import os`, `import sys`, `sys.path.insert(...)`.

Change:
```python
import muninn_chroma as mc
```
To:
```python
from muninn_mcp import chroma as mc
```

- [ ] **Step 11: Update `tests/test_symbol_format.py`**

Remove `import os`, `import sys`, `sys.path.insert(...)`.

Change:
```python
from muninn import (...)
```
To:
```python
from muninn_mcp.server import (...)
```

- [ ] **Step 12: Update `tests/test_symbol_handlers.py`**

Remove `import os`, `import sys`, `sys.path.insert(...)`.

Change:
```python
import muninn_chroma as mc   →   from muninn_mcp import chroma as mc
import muninn_embed as me    →   from muninn_mcp import embed as me
import muninn_project as mp  →   from muninn_mcp import project as mp
from muninn import X         →   from muninn_mcp.server import X
```

- [ ] **Step 13: Run all tests**

Run: `uv run pytest tests/ -v`

Expected: all tests pass (some may be skipped if they require a live Ollama instance)

- [ ] **Step 14: Commit**

```bash
git add tests/
git commit -m "test: migrate tests to tests/ with updated package imports"
```

---

## Task 7: Delete shared/ and verify

**Files:**
- Delete: `shared/` (entire directory)

- [ ] **Step 1: Run full test suite one more time before deleting**

Run: `uv run pytest tests/ -v`

Expected: all tests pass

- [ ] **Step 2: Delete the shared/ directory**

```bash
rm -rf shared/
```

- [ ] **Step 3: Run full test suite again to confirm nothing depended on shared/**

Run: `uv run pytest tests/ -v`

Expected: same results as Step 1 — no new failures

- [ ] **Step 4: Verify the package builds cleanly**

Run: `uv build`

Expected: creates `dist/muninn_mcp-0.1.0-py3-none-any.whl` and `dist/muninn_mcp-0.1.0.tar.gz`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove shared/ directory (replaced by src/muninn_mcp/)"
```

---

## Task 8: GitHub Actions publish workflow

**Files:**
- Create: `.github/workflows/publish.yml`

- [ ] **Step 1: Create the workflow directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create `.github/workflows/publish.yml`**

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*"

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # required for OIDC trusted publishing

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5

      - name: Build package
        run: uv build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/publish.yml
git commit -m "ci: add GitHub Actions workflow to publish muninn-mcp to PyPI on v* tags"
```

---

## Task 9: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the Prerequisites section**

Add `uv` remains a prerequisite. No change needed there.

- [ ] **Step 2: Replace the Installation section**

Find the `## Installation` heading and replace the content with:

```markdown
## Installation

### 1. Install muninn-mcp

```bash
uvx muninn-mcp install
```

This installs the companion skills (`memory-read`, `memory-write`, `symbol-search`) to `~/.config/opencode/skills/`.

### 2. Add MCP server to opencode.json

Edit `~/.opencode/opencode.json` and add the `muninn` entry under `"mcp"`:

```json
"muninn": {
  "type": "local",
  "command": ["uvx", "muninn-mcp"],
  "environment": {
    "MUNINN_OLLAMA_URL": "http://localhost:11434",
    "MUNINN_DATA_DIR": "/Users/your-username/.config/opencode/muninn"
  },
  "enabled": true
}
```

No paths to clone or manage. `uvx` downloads and caches `muninn-mcp` from PyPI automatically.
```

- [ ] **Step 3: Remove or archive the old path-based instructions**

Delete the old `### 2. Symlink the skills` section and any references to `/path/to/opencode/skills/muninn/`.

Also remove the `> **No \`--with\` flags needed.** \`muninn.py\` uses PEP 723...` note — it no longer applies.

- [ ] **Step 4: Update the remote Ollama example**

Update the remote Ollama `opencode.json` example (currently shows `uv run /path/to/...`) to use `uvx muninn-mcp`:

```json
"muninn": {
  "type": "local",
  "command": ["uvx", "muninn-mcp"],
  "environment": {
    "MUNINN_OLLAMA_URL": "https://your-mimir-host/v1",
    "MUNINN_OLLAMA_TOKEN": "your-bearer-token",
    "MUNINN_DATA_DIR": "/Users/your-username/.config/opencode/muninn"
  },
  "enabled": true
}
```

- [ ] **Step 5: Add PyPI one-time setup note**

Add a `## Publishing` section (or `## For maintainers`) at the end of the README:

```markdown
## Publishing

Releases are published to PyPI automatically when a `v*` tag is pushed:

```bash
git tag v0.1.0
git push --tags
```

**One-time PyPI setup (maintainer only):**
1. Create an account at [pypi.org](https://pypi.org)
2. Go to Account → Publishing → Add a Trusted Publisher:
   - Owner: `antic-eye`
   - Repository: your GitHub repo name
   - Workflow: `publish.yml`
   - Environment: *(leave blank)*
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: update README for uvx-based installation"
```

---

## Final verification

- [ ] **Run the full test suite**

Run: `uv run pytest tests/ -v`

Expected: all tests pass

- [ ] **Build the package**

Run: `uv build`

Expected: `dist/muninn_mcp-0.1.0-py3-none-any.whl` created

- [ ] **Smoke test the installed wheel**

```bash
uv tool install dist/muninn_mcp-0.1.0-py3-none-any.whl --force
muninn-mcp install
```

Expected: prints `Installed: ...` lines for each SKILL.md and a final `Skills installed to: ...` line

- [ ] **Commit final state if any cleanup was needed**

```bash
git status  # should be clean
```
