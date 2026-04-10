# Muninn

<img src="logo.svg" alt="Muninn logo" width="120" align="right" />

> *Muninn (Old Norse: "memory") is one of Odin's two ravens — the raven of memory.*

Muninn is a semantic memory layer for OpenCode. It gives AI coding sessions persistent, searchable memory — so you never have to re-explain your project from scratch.

[![CodeQL Advanced](https://github.com/antic-eye/muninn/actions/workflows/codeql.yml/badge.svg)](https://github.com/antic-eye/muninn/actions/workflows/codeql.yml)
[![Pylint](https://github.com/antic-eye/muninn/actions/workflows/pylint.yml/badge.svg?branch=main)](https://github.com/antic-eye/muninn/actions/workflows/pylint.yml)
[![Publish to PyPI](https://github.com/antic-eye/muninn/actions/workflows/publish.yml/badge.svg)](https://github.com/antic-eye/muninn/actions/workflows/publish.yml)

## What it does

- **Session resumption** — load prior context at the start of every session
- **Decision tracking** — record architectural decisions with their rationale
- **Pattern memory** — save code conventions that apply across the project
- **Semantic search** — find relevant memories by meaning, not exact keywords
- **Global memory** — store cross-project knowledge (infra procedures, tool patterns, auth flows) that persists across all projects
- **Symbol index** — index code symbols (functions, classes, methods) and search them semantically so the AI can navigate large codebases without re-reading files

Memory is stored locally in `~/.config/opencode/muninn/chroma/` using ChromaDB (embedded). Each project gets its own isolated collection. A special `__global__` collection holds cross-project knowledge.

---

## Prerequisites

1. **uv** — [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
2. **Ollama** with `mxbai-embed-large` — can be local or remote:
   - **Local:** `ollama pull mxbai-embed-large && ollama serve`
   - **Remote:** any Ollama-compatible endpoint (e.g. Mimir) — set `MUNINN_OLLAMA_URL` and optionally `MUNINN_OLLAMA_TOKEN`

---

## Installation

### OpenCode

**1. Install companion skills**

```bash
uvx muninn-remembers install opencode
```

This copies `memory-read`, `memory-write`, and `symbol-search` to `~/.config/opencode/skills/`.

**2. Add the MCP server to `~/.opencode/opencode.json`**

```json
"muninn": {
  "type": "local",
  "command": ["uvx", "muninn-remembers"],
  "environment": {
    "MUNINN_OLLAMA_URL": "http://localhost:11434",
    "MUNINN_DATA_DIR": "/Users/your-username/.config/opencode/muninn"
  },
  "enabled": true
}
```

**3. Restart OpenCode** to pick up the new MCP server.

---

### Claude Code

**1. Install companion slash commands**

```bash
uvx muninn-remembers install claude
```

This copies `memory-read.md`, `memory-write.md`, and `symbol-search.md` to `~/.claude/commands/`, making them available as `/memory-read`, `/memory-write`, and `/symbol-search` slash commands.

**2. Add the MCP server**

```bash
claude mcp add muninn \
  --env MUNINN_OLLAMA_URL=http://localhost:11434 \
  --env MUNINN_DATA_DIR=/Users/your-username/.config/opencode/muninn \
  -- uvx muninn-remembers
```

**3. Verify** by running `/mcp` in Claude Code — `muninn` should appear in the list.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MUNINN_OLLAMA_URL` | `http://localhost:11434` | Ollama base URL (local or remote) |
| `MUNINN_OLLAMA_TOKEN` | *(unset)* | Bearer token for authenticated Ollama endpoints (e.g. Mimir) |
| `MUNINN_EMBED_MODEL` | `mxbai-embed-large:latest` | Ollama embedding model |
| `MUNINN_DATA_DIR` | `~/.config/opencode/muninn` | ChromaDB storage path |
| `MUNINN_TOP_K` | `5` | Default number of search results |
| `MUNINN_PROJECT` | *(auto-detected)* | Override project name |

### Using a remote Ollama endpoint (e.g. Mimir)

**OpenCode** (`opencode.json`):

```json
"muninn": {
  "type": "local",
  "command": ["uvx", "muninn-remembers"],
  "environment": {
    "MUNINN_OLLAMA_URL": "https://your-mimir-host/v1",
    "MUNINN_OLLAMA_TOKEN": "your-bearer-token",
    "MUNINN_DATA_DIR": "/Users/your-username/.config/opencode/muninn"
  },
  "enabled": true
}
```

**Claude Code**:

```bash
claude mcp add muninn \
  --env MUNINN_OLLAMA_URL=https://your-mimir-host/v1 \
  --env MUNINN_OLLAMA_TOKEN=your-bearer-token \
  --env MUNINN_DATA_DIR=/Users/your-username/.config/opencode/muninn \
  -- uvx muninn-remembers
```

When `MUNINN_OLLAMA_TOKEN` is set, every embedding request includes an `Authorization: Bearer <token>` header.

---

## MCP Tools

### Project-scoped tools

| Tool | Description |
|------|-------------|
| `memory_write` | Write a memory entry (text, type, tags) |
| `memory_search` | Semantic search across project memories |
| `memory_list` | List recent memories (paginated) |
| `memory_delete` | Delete a memory entry by ID |
| `memory_wipe_project` | Delete ALL memories for a project (requires `confirm=True`) |
| `memory_list_projects` | List all projects that have stored memories |

### Global tools (cross-project)

| Tool | Description |
|------|-------------|
| `global_memory_write` | Write a cross-project memory (infra procedures, tool patterns, auth flows, etc.) |
| `global_memory_search` | Semantic search across global memories |
| `global_memory_list` | List global memories (paginated) |
| `global_memory_delete` | Delete a global memory entry by ID |
| `global_memory_wipe` | Delete ALL global memories (requires `confirm=True`) |

### Symbol tools (per-project code index)

| Tool | Description |
|------|-------------|
| `symbol_index` | Index one or more code symbols — name, kind, file, signature, docstring, callers |
| `symbol_search` | Semantic search across indexed symbols by natural-language query |
| `symbol_delete_file` | Remove all symbols belonging to a given file path |
| `symbol_wipe` | Delete the entire symbol index for a project (requires `confirm=True`) |

Each symbol is stored in a dedicated ChromaDB collection named `<project>__symbols`, separate from the memory collection. Symbol entries are keyed by a deterministic ID (`sha1(<project>:<file>:<name>:<kind>)[:16]`), so re-indexing a symbol overwrites the previous entry rather than creating a duplicate.

---

## Skills

Two companion skills guide the agent:

- **memory-read** — Load project context + global context at session start
- **memory-write** — Save decisions, summaries, next steps, and cross-project knowledge
- **symbol-search** — Guide when and how to index code symbols and search them by meaning

---

## Verify it works

After installation, call the `memory_list_projects` tool (in OpenCode or Claude Code):

```
memory_list_projects()
```

This returns a (possibly empty) list if Muninn is connected. If you see an error, check that:
1. `uv` is on your PATH
2. Ollama is reachable: `curl $MUNINN_OLLAMA_URL/api/tags` (or `curl http://localhost:11434/api/tags` for local)
3. The MCP server is registered — run `/mcp` in Claude Code, or check `opencode.json` in OpenCode

---

## Project detection

Muninn auto-detects the current project using this priority order:

1. `MUNINN_PROJECT` env var (explicit override)
2. `git rev-parse --show-toplevel` → basename
3. `os.getcwd()` → basename

---

## Data location

All memory data lives at `~/.config/opencode/muninn/chroma/`. To back up your memories, copy this directory. To start fresh for a project, use `memory_wipe_project`.

---

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
