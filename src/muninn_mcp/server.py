"""
server.py — MCP server entry point for Muninn per-project memory.
(src/muninn_mcp/server.py)

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
import hashlib
import subprocess
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import chroma as mc
from . import embed as me
from . import project as mp

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
        if c.name.startswith("muninn_") and "__symbols" not in c.name
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
# Symbol index helpers (private)
# ---------------------------------------------------------------------------


def _symbol_id(project: str, file: str, name: str, kind: str) -> str:
    raw = f"{project}:{file}:{name}:{kind}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _symbol_document(sym: dict[str, Any]) -> str:
    kind = sym.get("kind", "symbol")
    name = sym.get("name", "")
    file = sym.get("file", "")
    docstring = sym.get("docstring", "")
    signature = sym.get("signature", "")
    callers = sym.get("callers", [])
    callers_str = ", ".join(callers) if isinstance(callers, list) else str(callers)
    parts = [f"{kind} {name} in {file}"]
    if docstring:
        parts.append(f"— {docstring}")
    parts.append(f"Signature: {signature or 'N/A'}.")
    if callers_str:
        parts.append(f"Called by: {callers_str}.")
    return " ".join(parts)


def _build_symbol_metadata(
    sym: dict[str, Any], project: str, today: str
) -> tuple[str, str, dict[str, Any]]:
    """Extract and normalise fields from a symbol dict for indexing.

    Returns (entry_id, document, metadata).
    """
    name = sym["name"]  # raises KeyError if missing — intentional
    kind = sym["kind"]  # raises KeyError if missing — intentional
    file = sym["file"]  # raises KeyError if missing — intentional
    line = sym.get("line", 0)
    signature = sym.get("signature", "")
    docstring = sym.get("docstring", "")
    callers = sym.get("callers", [])
    callers_str = ", ".join(callers) if isinstance(callers, list) else str(callers)

    entry_id = _symbol_id(project, file, name, kind)
    document = _symbol_document(sym)
    metadata = {
        "kind": kind,
        "name": name,
        "file": file,
        "line": line,
        "signature": signature,
        "docstring": docstring,
        "callers": callers_str,
        "project": project,
        "indexed_at": today,
    }
    return entry_id, document, metadata


# ---------------------------------------------------------------------------
# Symbol handlers (pure Python, testable without MCP server)
# ---------------------------------------------------------------------------


def handle_symbol_index(symbols: list[dict[str, Any]]) -> dict[str, Any]:
    """Upsert one or more symbols into the project's symbol collection."""
    if not symbols:
        raise ValueError("symbols list must not be empty")
    project = mp.detect_project_name()
    collection_name = mp.symbol_collection_name(project)
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)

    today = datetime.date.today().isoformat()
    for sym in symbols:
        entry_id, document, metadata = _build_symbol_metadata(sym, project, today)
        embedding = me.get_embedding(document)
        mc.upsert_memory(col, entry_id, document, embedding, metadata)

    primary_file = symbols[0]["file"]
    return {"count": len(symbols), "file": primary_file, "project": project}


def handle_symbol_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Semantic search over the project's symbol collection."""
    project = mp.detect_project_name()
    collection_name = mp.symbol_collection_name(project)
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)
    query_embedding = me.get_embedding(query)
    return mc.query_memory(col, query_embedding, top_k=top_k)


def handle_symbol_delete_file(file_path: str) -> dict[str, Any]:
    """Delete all symbols indexed for a given file path."""
    project = mp.detect_project_name()
    collection_name = mp.symbol_collection_name(project)
    client = mc.get_client()
    col = mc.get_collection(client, collection_name)
    deleted = mc.delete_symbols_by_file(col, file_path)
    return {"deleted": deleted, "file": file_path, "project": project}


def handle_symbol_wipe(confirm: bool = False) -> dict[str, Any]:
    """Delete the entire symbol index for the current project."""
    if not confirm:
        raise ValueError("Set confirm=True to wipe the symbol index.")
    project = mp.detect_project_name()
    collection_name = mp.symbol_collection_name(project)
    client = mc.get_client()
    count = mc.wipe_collection(client, collection_name)
    return {"wiped": True, "project": project, "entries_deleted": count}


# ---------------------------------------------------------------------------
# MCP tool registrations
# ---------------------------------------------------------------------------


@mcp.tool()
def memory_write(text: str, memory_type: str = "note", tags: str = "") -> str:
    """
    Write a memory entry for the current project.

    Args:
        text: The content to remember (decision, summary, code pattern, etc.)
        memory_type: One of: summary, decision, next-steps, code-pattern, note
        tags: Comma-separated tags, e.g. "auth,refactor,jira"
    """
    result = handle_memory_write(text, memory_type, tags)
    return format_write_result(result, tags=tags)


@mcp.tool()
def memory_search(query: str, top_k: int = 5) -> str:
    """
    Semantic search across memories for the current project.

    Args:
        query: Natural language search query
        top_k: Number of results to return (default 5)
    """
    results = handle_memory_search(query, top_k)
    return format_search_results(results)


@mcp.tool()
def memory_list(limit: int = 20, offset: int = 0) -> str:
    """
    List memory entries for the current project in insertion order.

    Args:
        limit: Max entries to return (default 20)
        offset: Pagination offset (default 0)
    """
    results = handle_memory_list(limit, offset)
    return format_list_results(results, offset=offset)


@mcp.tool()
def memory_delete(entry_id: str) -> str:
    """
    Delete a specific memory entry by its ID.

    Args:
        entry_id: The UUID of the entry to delete
    """
    result = handle_memory_delete(entry_id)
    return format_delete_result(result)


@mcp.tool()
def memory_wipe_project(project_name: str, confirm: bool = False) -> str:
    """
    Delete ALL memory entries for a named project. DESTRUCTIVE.

    Args:
        project_name: The project name (as returned by memory_list_projects)
        confirm: Must be True to proceed
    """
    result = handle_memory_wipe_project(project_name, confirm)
    return format_wipe_result(result)


@mcp.tool()
def memory_list_projects() -> str:
    """List all projects that have stored memories."""
    projects = handle_memory_list_projects()
    return format_projects_list(projects)


# ---------------------------------------------------------------------------
# Global memory MCP tool registrations
# ---------------------------------------------------------------------------


@mcp.tool()
def global_memory_write(text: str, memory_type: str = "note", tags: str = "") -> str:
    """
    Write a cross-project memory entry (global scope).

    Use this for knowledge that applies across projects: infrastructure procedures,
    CLI tool patterns, authentication flows, workflow conventions, etc.

    Args:
        text: The content to remember
        memory_type: One of: summary, decision, next-steps, code-pattern, note
        tags: Comma-separated tags, e.g. "openshift,auth,infra"
    """
    result = handle_global_memory_write(text, memory_type, tags)
    return format_write_result(result, tags=tags)


@mcp.tool()
def global_memory_search(query: str, top_k: int = 5) -> str:
    """
    Semantic search across global (cross-project) memories.

    Args:
        query: Natural language search query
        top_k: Number of results to return (default 5)
    """
    results = handle_global_memory_search(query, top_k)
    return format_search_results(results)


@mcp.tool()
def global_memory_list(limit: int = 20, offset: int = 0) -> str:
    """
    List global memory entries in insertion order.

    Args:
        limit: Max entries to return (default 20)
        offset: Pagination offset (default 0)
    """
    results = handle_global_memory_list(limit, offset)
    return format_list_results(results, offset=offset)


@mcp.tool()
def global_memory_delete(entry_id: str) -> str:
    """
    Delete a specific global memory entry by its ID.

    Args:
        entry_id: The UUID of the entry to delete
    """
    result = handle_global_memory_delete(entry_id)
    return format_delete_result(result)


@mcp.tool()
def global_memory_wipe(confirm: bool = False) -> str:
    """
    Delete ALL global memory entries. DESTRUCTIVE.

    Args:
        confirm: Must be True to proceed
    """
    result = handle_global_memory_wipe(confirm)
    return format_wipe_result(result)


# ---------------------------------------------------------------------------
# Symbol index MCP tool registrations
# ---------------------------------------------------------------------------


@mcp.tool()
def symbol_index(symbols: list[dict[str, Any]]) -> str:
    """
    Index one or more code symbols into the project's symbol collection.

    Call this when opening or editing a source file. Pass all top-level symbols
    (functions, classes, methods, constants, type aliases) found in the file.

    Args:
        symbols: List of symbol dicts. Each requires: name, kind, file, line.
                 Optional: signature, docstring, callers (list of str).
    """
    result = handle_symbol_index(symbols)
    return format_symbol_index_result(result)


@mcp.tool()
def symbol_search(query: str, top_k: int = 5) -> str:
    """
    Semantic search over the project's symbol index.

    Use before grepping — this is faster and understands intent.
    Examples: "function that validates JWT", "class for user repository"

    Args:
        query: Natural language description of the symbol you're looking for
        top_k: Max results to return (default 5)
    """
    results = handle_symbol_search(query, top_k)
    return format_symbol_search_results(results)


@mcp.tool()
def symbol_delete_file(file_path: str) -> str:
    """
    Remove all indexed symbols for a given file.

    Call this when a file is deleted, renamed, or fully rewritten before re-indexing.

    Args:
        file_path: Relative path to the file (e.g. "auth/jwt.py")
    """
    result = handle_symbol_delete_file(file_path)
    return format_symbol_delete_file_result(result)


@mcp.tool()
def symbol_wipe(confirm: bool = False) -> str:
    """
    Delete the entire symbol index for the current project. DESTRUCTIVE.

    Args:
        confirm: Must be True to proceed
    """
    result = handle_symbol_wipe(confirm)
    return format_symbol_wipe_result(result)


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
    entry_id = (result.get("id") or "????????")[:8] + "…"
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
        score = max(0.0, min(1.0, 1.0 - distance))
        document = r.get("document", "")
        tag_part = f" · tags: `{tags}`" if tags else ""
        lines.append(
            f"**{i}.** `{memory_type}` · {date}{tag_part} · score: {score:.2f}"
        )
        lines.append("> " + document.replace("\n", "\n> "))
        if i < n:
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
        lines.append("> " + document.replace("\n", "\n> "))
        if i < n:
            lines.append("")
            lines.append("---")
            lines.append("")
    return "\n".join(lines).rstrip()


def format_delete_result(result: dict[str, Any]) -> str:
    entry_id = (result.get("id") or "????????")[:8] + "…"
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


def format_symbol_index_result(result: dict[str, Any]) -> str:
    count = result.get("count", 0)
    file = result.get("file", "unknown")
    noun = "symbol" if count == 1 else "symbols"
    return f"✅ Indexed {count} {noun} in `{file}`"


def format_symbol_search_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "_No symbols matched your query._"
    n = len(results)
    lines = [f"### 🔎 Symbol Search — {n} result{'s' if n != 1 else ''}\n"]
    for i, r in enumerate(results, 1):
        meta = r.get("metadata") or {}
        kind = meta.get("kind", "symbol")
        name = meta.get("name", "?")
        file = meta.get("file", "?")
        line = meta.get("line", "?")
        signature = meta.get("signature", "")
        docstring = meta.get("docstring", "")
        distance = r.get("distance", 0.0)
        score = max(0.0, min(1.0, 1.0 - distance))
        lines.append(
            f"**{i}.** `{kind}` **{name}** · {file}:{line} · score: {score:.2f}"
        )
        if signature:
            lines.append(f"> `{signature}`")
        if docstring:
            lines.append(f"> {docstring}")
        if i < n:
            lines.append("")
            lines.append("---")
            lines.append("")
    return "\n".join(lines).rstrip()


def format_symbol_delete_file_result(result: dict[str, Any]) -> str:
    deleted = result.get("deleted", 0)
    file = result.get("file", "unknown")
    noun = "symbol" if deleted == 1 else "symbols"
    return f"🗑️ Removed {deleted} {noun} from `{file}`"


def format_symbol_wipe_result(result: dict[str, Any]) -> str:
    project = result.get("project", "unknown")
    count = result.get("entries_deleted", 0)
    noun = "entry" if count == 1 else "entries"
    return f"💥 Wiped symbol index for **{project}** — {count} {noun} deleted."
