# Muninn

<img src="logo.svg" alt="Muninn logo" width="120" align="right" />

> *Muninn (Old Norse: "memory") is one of Odin's two ravens — the raven of memory.*

Muninn is a semantic memory layer for OpenCode. It gives AI coding sessions persistent, searchable memory — so you never have to re-explain your project from scratch.

## What it does

- **Session resumption** — load prior context at the start of every session
- **Decision tracking** — record architectural decisions with their rationale
- **Pattern memory** — save code conventions that apply across the project
- **Semantic search** — find relevant memories by meaning, not exact keywords
- **Global memory** — store cross-project knowledge (infra procedures, tool patterns, auth flows) that persists across all projects

Memory is stored locally in `~/.config/opencode/muninn/chroma/` using ChromaDB (embedded). Each project gets its own isolated collection. A special `__global__` collection holds cross-project knowledge.

---

## Prerequisites

1. **uv** — [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
2. **Ollama** with `mxbai-embed-large` — can be local or remote:
   - **Local:** `ollama pull mxbai-embed-large && ollama serve`
   - **Remote:** any Ollama-compatible endpoint (e.g. Mimir) — set `MUNINN_OLLAMA_URL` and optionally `MUNINN_OLLAMA_TOKEN`

---

## Installation

### 1. Add MCP server to opencode.json

Edit `~/.opencode/opencode.json` and add the `muninn` entry under `"mcp"`:

```json
"muninn": {
  "type": "local",
  "command": [
    "uv", "run",
    "/path/to/opencode/skills/muninn/shared/muninn.py"
  ],
  "environment": {
    "MUNINN_OLLAMA_URL": "http://localhost:11434",
    "MUNINN_DATA_DIR": "/Users/your-username/.config/opencode/muninn"
  },
  "enabled": true
}
```

> **No `--with` flags needed.** `muninn.py` uses [PEP 723](https://peps.python.org/pep-0723/) inline script metadata — `uv` reads the `# /// script` block at the top of the file and installs `mcp[cli]`, `chromadb`, and `httpx` automatically.

Replace `/path/to/opencode/skills/` with the actual path to your skills repository.

### 2. Symlink the skills

```bash
ln -s /path/to/opencode/skills/muninn/memory-read ~/.config/opencode/skills/memory-read
ln -s /path/to/opencode/skills/muninn/memory-write ~/.config/opencode/skills/memory-write
```

### 3. Restart OpenCode

After updating `opencode.json`, restart OpenCode to pick up the new MCP server.

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

```json
"muninn": {
  "type": "local",
  "command": [
    "uv", "run",
    "/path/to/opencode/skills/muninn/shared/muninn.py"
  ],
  "environment": {
    "MUNINN_OLLAMA_URL": "https://your-mimir-host/v1",
    "MUNINN_OLLAMA_TOKEN": "your-bearer-token",
    "MUNINN_DATA_DIR": "/Users/your-username/.config/opencode/muninn"
  },
  "enabled": true
}
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

---

## Skills

Two companion skills guide the agent:

- **memory-read** — Load project context + global context at session start
- **memory-write** — Save decisions, summaries, next steps, and cross-project knowledge

---

## Verify it works

After installation, in an OpenCode session:

```
memory_list_projects()
```

If Muninn is connected, this returns a (possibly empty) list. If you see an error, check that:
1. `uv` is on your PATH
2. Ollama is reachable: `curl $MUNINN_OLLAMA_URL/api/tags` (or `curl http://localhost:11434/api/tags` for local)
3. The path in `opencode.json` points to the correct `muninn.py`

---

## Project detection

Muninn auto-detects the current project using this priority order:

1. `MUNINN_PROJECT` env var (explicit override)
2. `git rev-parse --show-toplevel` → basename
3. `os.getcwd()` → basename

---

## Data location

All memory data lives at `~/.config/opencode/muninn/chroma/`. To back up your memories, copy this directory. To start fresh for a project, use `memory_wipe_project`.
