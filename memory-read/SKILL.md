---
name: memory-read
description: "Use at the start of every development session to load project context from Muninn — recalls last state, decisions, and open next-steps"
---

# Muninn — Memory Read

## Overview

Load project context at session start. Queries both the current project's vector store
and the global (cross-project) vector store, then synthesises a combined session brief.

## When to Use

- **Always** at the start of a development session on a known project
- When the user says "what was I working on?" or "remind me where we left off"
- Before making architectural decisions (check for prior decisions first)

## Protocol

### Step 1: Detect the project

```bash
git rev-parse --show-toplevel 2>/dev/null || pwd
```

Note the project name (basename of the result). This is what Muninn uses automatically.

### Step 2a: Search global memory

```
global_memory_search(query="recent patterns workflows infra tools procedures", top_k=5)
global_memory_list(limit=3)
```

### Step 2b: Search project memory

```
memory_search(query="recent work context decisions next steps", top_k=5)
memory_list(limit=5, offset=0)
```

### Step 3: Synthesise a session brief

Combine the results into a **Session Brief** with these sections:

```
## Session Brief — <project-name>

**Last worked on:** <date of most recent project memory>

**Recent summary:** <2-3 sentences from summary memories>

**Open next steps:**
- <item 1>
- <item 2>

**Key decisions:**
- <decision 1 with rationale>

**Active branch:** <from git_branch metadata if present>

**Global context (cross-project):**
- <relevant global patterns or procedures, if any>
```

If there are no global memories, omit the "Global context" section entirely.

Present the brief to the user *before* asking what to work on.

### Step 4: No memories found

If both calls return empty results, say:
> "No prior memories found for project **{project}**. This appears to be a fresh start.
> I'll automatically save context as we work."

## Search Tips

| Goal | Query to use |
|------|-------------|
| Find why a decision was made | `"decision <topic>"` |
| Find open work | `"next steps todo blockers"` |
| Find a code pattern | `"pattern convention <area>"` |
| Find recent summaries | `memory_list(limit=5)` (no search needed) |
| Find infra/tool procedures | `global_memory_search("openshift vpn login cli")` |
