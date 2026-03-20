# Muninn

<img src="logo.svg" alt="Muninn logo" width="120" align="right" />

> *Muninn (Old Norse: "memory") is one of Odin's two ravens — the raven of memory.*

Muninn is a per-project semantic memory layer for OpenCode. It gives AI coding sessions persistent, searchable memory — so you never have to re-explain your project from scratch.

## What it does

- **Session resumption** — load prior context at the start of every session
- **Decision tracking** — record architectural decisions with their rationale
- **Pattern memory** — save code conventions that apply across the project
- **Semantic search** — find relevant memories by meaning, not exact keywords

Memory is stored locally in `~/.config/opencode/muninn/chroma/` using ChromaDB (embedded). Each project gets its own isolated collection.

---

## Prerequisites

1. **uv** — [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
2. **Ollama** running locally with `mxbai-embed-large`:
   ```bash
   ollama pull mxbai-embed-large
   ollama serve  # should already be running
   ```

---

## Installation

### 1. Add MCP server to opencode.json

Edit `~/.opencode/opencode.json` and add the `muninn` entry under `"mcp"`:

```json
"muninn": {
  "type": "local",
  "command": [
    "uv", "run",
    "--with", "mcp[cli]",
    "--with", "chromadb",
    "--with", "httpx",
    "/path/to/opencode/skills/muninn/shared/muninn.py"
  ],
  "environment": {
    "MUNINN_OLLAMA_URL": "http://localhost:11434",
    "MUNINN_DATA_DIR": "/Users/your-username/.config/opencode/muninn"
  },
  "enabled": true
}
```

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
| `MUNINN_OLLAMA_URL` | `http://localhost:11434` | Ollama base URL |
| `MUNINN_EMBED_MODEL` | `mxbai-embed-large:latest` | Ollama embedding model |
| `MUNINN_DATA_DIR` | `~/.config/opencode/muninn` | ChromaDB storage path |
| `MUNINN_TOP_K` | `5` | Default number of search results |
| `MUNINN_PROJECT` | *(auto-detected)* | Override project name |

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `memory_write` | Write a memory entry (text, type, tags) |
| `memory_search` | Semantic search across project memories |
| `memory_list` | List recent memories (paginated) |
| `memory_delete` | Delete a memory entry by ID |
| `memory_wipe_project` | Delete ALL memories for a project (requires `confirm=True`) |
| `memory_list_projects` | List all projects that have stored memories |

---

## Skills

Two companion skills guide the agent:

- **memory-read** — Load project context at session start
- **memory-write** — Save decisions, summaries, and next steps

---

## Verify it works

After installation, in an OpenCode session:

```
memory_list_projects()
```

If Muninn is connected, this returns a (possibly empty) list. If you see an error, check that:
1. `uv` is on your PATH
2. Ollama is running: `curl http://localhost:11434/api/tags`
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
