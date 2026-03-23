#!/usr/bin/env python3
# /// script
# dependencies = ["mcp[cli]", "chromadb", "httpx"]
# ///
"""
muninn.py — MCP server entry point for Muninn per-project memory.

Usage (via uv run):
    uv run muninn.py

MCP tools exposed (project-scoped):
    memory_write          Write a memory entry
    memory_search         Semantic search
    memory_list           List recent memories (paginated)
    memory_delete         Delete by ID
    memory_wipe_project   Delete ALL memories for a project
    memory_list_projects  List all known projects

MCP tools exposed (global scope):
    global_memory_write   Write a cross-project memory entry
    global_memory_search  Semantic search across global memories
    global_memory_list    List global memories (paginated)
    global_memory_delete  Delete a global entry by ID
    global_memory_wipe    Delete ALL global memories
"""

from __future__ import annotations

import datetime
import subprocess
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

import muninn_chroma as mc
import muninn_embed as me
import muninn_project as mp

mcp = FastMCP("muninn")


# ---------------------------------------------------------------------------
# Handler functions (pure Python, testable without MCP server)
# ---------------------------------------------------------------------------


def handle_memory_write(
    text: str,
    memory_type: str,
    tags: str,
    source: str = "manual",
) -> dict[str, Any]:
    project = mp.detect_project_name()
    collection_name = mp.sanitise_collection_name(project)
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)

    entry_id = str(uuid.uuid4())
    embedding = me.get_embedding(text)

    git_branch, git_commit = _git_info()
    metadata = {
        "project": project,
        "type": memory_type,
        "session_date": datetime.date.today().isoformat(),
        "tags": tags,
        "source": source,
        "git_branch": git_branch,
        "git_commit": git_commit,
    }

    mc.upsert_memory(col, entry_id, text, embedding, metadata)
    return {"id": entry_id, "project": project, "type": memory_type}


def handle_memory_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    project = mp.detect_project_name()
    collection_name = mp.sanitise_collection_name(project)
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)
    query_embedding = me.get_embedding(query)
    return mc.query_memory(col, query_embedding, top_k=top_k)


def handle_memory_list(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    project = mp.detect_project_name()
    collection_name = mp.sanitise_collection_name(project)
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)
    return mc.list_memories(col, limit=limit, offset=offset)


def handle_memory_delete(entry_id: str) -> dict[str, Any]:
    project = mp.detect_project_name()
    collection_name = mp.sanitise_collection_name(project)
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)
    try:
        mc.delete_memory(col, entry_id)
    except mc.MemoryNotFoundError:
        return {"deleted": False, "id": entry_id, "error": "not found"}
    return {"deleted": True, "id": entry_id}


def handle_memory_wipe_project(
    project_name: str, confirm: bool = False
) -> dict[str, Any]:
    if not confirm:
        raise ValueError("Set confirm=True to wipe all memories for a project.")
    collection_name = mp.sanitise_collection_name(project_name)
    client = mc.get_client()
    count = mc.wipe_collection(client, collection_name)
    return {"wiped": True, "project": project_name, "entries_deleted": count}


def handle_memory_list_projects() -> list[str]:
    client = mc.get_client()
    collections = client.list_collections()
    return [
        c.name.removeprefix("muninn_")
        for c in collections
        if c.name.startswith("muninn_")
    ]


# ---------------------------------------------------------------------------
# Global memory handlers
# ---------------------------------------------------------------------------


def handle_global_memory_write(
    text: str,
    memory_type: str,
    tags: str,
    source: str = "manual",
) -> dict[str, Any]:
    collection_name = mp.GLOBAL_COLLECTION_NAME
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)

    entry_id = str(uuid.uuid4())
    embedding = me.get_embedding(text)

    metadata = {
        "project": mp.GLOBAL_PROJECT_NAME,
        "type": memory_type,
        "session_date": datetime.date.today().isoformat(),
        "tags": tags,
        "source": source,
    }

    mc.upsert_memory(col, entry_id, text, embedding, metadata)
    return {"id": entry_id, "project": mp.GLOBAL_PROJECT_NAME, "type": memory_type}


def handle_global_memory_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    collection_name = mp.GLOBAL_COLLECTION_NAME
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)
    query_embedding = me.get_embedding(query)
    return mc.query_memory(col, query_embedding, top_k=top_k)


def handle_global_memory_list(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    collection_name = mp.GLOBAL_COLLECTION_NAME
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)
    return mc.list_memories(col, limit=limit, offset=offset)


def handle_global_memory_delete(entry_id: str) -> dict[str, Any]:
    collection_name = mp.GLOBAL_COLLECTION_NAME
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)
    try:
        mc.delete_memory(col, entry_id)
    except mc.MemoryNotFoundError:
        return {"deleted": False, "id": entry_id, "error": "not found"}
    return {"deleted": True, "id": entry_id}


def handle_global_memory_wipe(confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        raise ValueError("Set confirm=True to wipe all global memories.")
    collection_name = mp.GLOBAL_COLLECTION_NAME
    client = mc.get_client()
    count = mc.wipe_collection(client, collection_name)
    return {
        "wiped": True,
        "project": mp.GLOBAL_PROJECT_NAME,
        "entries_deleted": count,
    }


# ---------------------------------------------------------------------------
# MCP tool registrations
# ---------------------------------------------------------------------------


@mcp.tool()
def memory_write(
    text: str, memory_type: str = "note", tags: str = ""
) -> dict[str, Any]:
    """
    Write a memory entry for the current project.

    Args:
        text: The content to remember (decision, summary, code pattern, etc.)
        memory_type: One of: summary, decision, next-steps, code-pattern, note
        tags: Comma-separated tags, e.g. "auth,refactor,jira"
    """
    return handle_memory_write(text, memory_type, tags)


@mcp.tool()
def memory_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Semantic search across memories for the current project.

    Args:
        query: Natural language search query
        top_k: Number of results to return (default 5)
    """
    return handle_memory_search(query, top_k)


@mcp.tool()
def memory_list(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """
    List memory entries for the current project in insertion order.

    Args:
        limit: Max entries to return (default 20)
        offset: Pagination offset (default 0)
    """
    return handle_memory_list(limit, offset)


@mcp.tool()
def memory_delete(entry_id: str) -> dict[str, Any]:
    """
    Delete a specific memory entry by its ID.

    Args:
        entry_id: The UUID of the entry to delete
    """
    return handle_memory_delete(entry_id)


@mcp.tool()
def memory_wipe_project(project_name: str, confirm: bool = False) -> dict[str, Any]:
    """
    Delete ALL memory entries for a named project. DESTRUCTIVE.

    Args:
        project_name: The project name (as returned by memory_list_projects)
        confirm: Must be True to proceed
    """
    return handle_memory_wipe_project(project_name, confirm)


@mcp.tool()
def memory_list_projects() -> list[str]:
    """List all projects that have stored memories."""
    return handle_memory_list_projects()


# ---------------------------------------------------------------------------
# Global memory MCP tool registrations
# ---------------------------------------------------------------------------


@mcp.tool()
def global_memory_write(
    text: str, memory_type: str = "note", tags: str = ""
) -> dict[str, Any]:
    """
    Write a cross-project memory entry (global scope).

    Use this for knowledge that applies across projects: infrastructure procedures,
    CLI tool patterns, authentication flows, workflow conventions, etc.

    Args:
        text: The content to remember
        memory_type: One of: summary, decision, next-steps, code-pattern, note
        tags: Comma-separated tags, e.g. "openshift,auth,infra"
    """
    return handle_global_memory_write(text, memory_type, tags)


@mcp.tool()
def global_memory_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Semantic search across global (cross-project) memories.

    Args:
        query: Natural language search query
        top_k: Number of results to return (default 5)
    """
    return handle_global_memory_search(query, top_k)


@mcp.tool()
def global_memory_list(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """
    List global memory entries in insertion order.

    Args:
        limit: Max entries to return (default 20)
        offset: Pagination offset (default 0)
    """
    return handle_global_memory_list(limit, offset)


@mcp.tool()
def global_memory_delete(entry_id: str) -> dict[str, Any]:
    """
    Delete a specific global memory entry by its ID.

    Args:
        entry_id: The UUID of the entry to delete
    """
    return handle_global_memory_delete(entry_id)


@mcp.tool()
def global_memory_wipe(confirm: bool = False) -> dict[str, Any]:
    """
    Delete ALL global memory entries. DESTRUCTIVE.

    Args:
        confirm: Must be True to proceed
    """
    return handle_global_memory_wipe(confirm)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git_info() -> tuple[str, str]:
    """Return (branch, short_commit) or empty strings if not in a git repo."""
    try:
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        commit = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        return branch, commit
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "", ""


# ---------------------------------------------------------------------------
# Markdown formatters — convert handler output to human-readable strings
# ---------------------------------------------------------------------------


def format_write_result(result: dict[str, Any], tags: str = "") -> str:
    entry_id = result["id"][:8] + "…"
    project = result.get("project", "unknown")
    memory_type = result.get("type", "note")
    tag_str = f" · tags: `{tags}`" if tags else ""
    return f"✅ Memory saved — **{memory_type}** · `{entry_id}` · project: `{project}`{tag_str}"


def format_search_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "_No memories matched your query._"
    n = len(results)
    lines = [f"### 🔍 Memory Search — {n} result{'s' if n != 1 else ''}\n"]
    for i, r in enumerate(results, 1):
        meta = r.get("metadata") or {}
        memory_type = meta.get("type", "note")
        date = meta.get("session_date", "")
        tags = meta.get("tags", "")
        distance = r.get("distance", 0.0)
        score = 1.0 - distance
        document = r.get("document", "")
        tag_part = f" · tags: `{tags}`" if tags else ""
        lines.append(
            f"**{i}.** `{memory_type}` · {date}{tag_part} · score: {score:.2f}"
        )
        lines.append(f"> {document}")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_list_results(results: list[dict[str, Any]], offset: int = 0) -> str:
    if not results:
        return f"_No memories found (offset {offset})._"
    n = len(results)
    lines = [
        f"### 📋 Memories — {n} entr{'y' if n == 1 else 'ies'} (offset {offset})\n"
    ]
    for i, r in enumerate(results, 1):
        meta = r.get("metadata") or {}
        memory_type = meta.get("type", "note")
        date = meta.get("session_date", "")
        tags = meta.get("tags", "")
        document = r.get("document", "")
        tag_part = f" · tags: `{tags}`" if tags else ""
        lines.append(f"**{i}.** `{memory_type}` · {date}{tag_part}")
        lines.append(f"> {document}")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_delete_result(result: dict[str, Any]) -> str:
    entry_id = result["id"][:8] + "…"
    if result.get("deleted"):
        return f"🗑️ Deleted memory `{entry_id}`"
    error = result.get("error", "unknown error")
    return f"⚠️ Memory `{entry_id}` not found — nothing deleted. ({error})"


def format_wipe_result(result: dict[str, Any]) -> str:
    project = result.get("project", "unknown")
    count = result.get("entries_deleted", 0)
    return (
        f"💥 Wiped **{project}** — {count} entr{'y' if count == 1 else 'ies'} deleted."
    )


def format_projects_list(projects: list[str]) -> str:
    if not projects:
        return "_No projects found._"
    lines = ["### 📁 Projects with memories\n"]
    for p in projects:
        lines.append(f"- `{p}`")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
