#!/usr/bin/env python3
# /// script
# dependencies = ["mcp[cli]", "chromadb", "httpx"]
# ///
"""
muninn.py — MCP server entry point for Muninn per-project memory.

Usage (via uv run):
    uv run muninn.py

MCP tools exposed:
    memory_write          Write a memory entry
    memory_search         Semantic search
    memory_list           List recent memories (paginated)
    memory_delete         Delete by ID
    memory_wipe_project   Delete ALL memories for a project
    memory_list_projects  List all known projects
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


if __name__ == "__main__":
    mcp.run()
