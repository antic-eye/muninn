---
name: memory-write
description: "Use when saving project context, decisions, or session summaries to Muninn — at context compaction, PR creation, session end, or on demand when the user says 'remember this'"
---

# Muninn — Memory Write

## Overview

Write structured memory entries to the current project's vector store.
Uses the `memory_write` MCP tool.

## Prerequisites

Verify the MCP server is responding:
```bash
# Check that muninn MCP tools are available — if not, see README for setup
```

## When to Write

| Trigger | Action |
|---------|--------|
| Context window > 80% | Write `summary` + `next-steps` |
| PR created or merged | Write `summary` of what was built |
| Session ends (user says "done", "bye", "wrap up") | Write `summary` + `next-steps` |
| User says "remember this" / "save this" | Write `note` with the stated content |
| Architectural/design decision made | Write `decision` |
| New code pattern established | Write `code-pattern` |
| Cross-project knowledge acquired (infra, tools, auth, workflows) | Write to `global_memory_write` instead |

## Memory Types

| Type | When to use | What to include |
|------|------------|-----------------|
| `summary` | End of work block | Files changed, features built, bugs fixed |
| `decision` | When a trade-off is resolved | What was decided, why, alternatives rejected |
| `next-steps` | When stopping mid-task | Exact next action, current state, blockers |
| `code-pattern` | When convention is established | Pattern name, example, where it applies |
| `note` | Everything else | Verbatim or summarised content |

## Writing a Memory

```
memory_write(
  text="<clear, self-contained text>",
  memory_type="<type from table above>",
  tags="<comma-separated keywords>"
)
```

### Good text examples

**summary:**
```
Built the ChromaDB helper module (muninn_chroma.py). Functions: get_collection,
upsert_memory, query_memory, list_memories, delete_memory, wipe_collection.
All 6 unit tests passing. Branch: feat/muninn-chroma-module.
```

**decision:**
```
Decided to use ChromaDB embedded mode (not HTTP server) because it requires zero
infrastructure and data lives at ~/.config/opencode/muninn/chroma/. Rejected
docker-based ChromaDB to avoid daemon dependency.
```

**next-steps:**
```
Next: implement muninn.py MCP server (Task 4). muninn_chroma.py done,
muninn_embed.py done, muninn_project.py done. Start with FastMCP registration,
then wire handler functions.
```

## Writing a Global Memory

Use `global_memory_write` when knowledge applies **across projects** — not just the current one.

Examples of global knowledge:
- How to log in to OpenShift / Kubernetes clusters
- VPN or SSH tunnel setup steps
- Preferred CLI flags for frequently used tools
- Organisation-wide workflow conventions
- Authentication procedures (SSO, token renewal, etc.)

```
global_memory_write(
  text="<self-contained, reusable procedure or pattern>",
  memory_type="<type>",
  tags="<infra,tool-name,category>"
)
```

### Good global text examples

**note (infra procedure):**
```
OpenShift login: oc login --token=$(oc whoami -t) --server=https://api.cluster.example.com:6443
If token expired, go to the OpenShift console → top-right menu → Copy login command.
```

**note (tool pattern):**
```
To port-forward a Kubernetes service: kubectl port-forward svc/<name> <local>:<remote> -n <namespace>
Use --address 0.0.0.0 to expose to the local network.
```

## Tags to Always Include

- Jira ticket keys if work is tracked (e.g. `PEAI-123`)
- Files changed (e.g. `muninn_chroma,muninn_embed`)
- Feature area (e.g. `auth,refactor,testing`)

## After Writing

Confirm to the user:
> "Memory saved ✓ (type: {type}, id: {id[:8]}…)"
