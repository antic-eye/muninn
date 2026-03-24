# /// script
# dependencies = ["chromadb"]
# ///
"""
muninn_chroma.py — ChromaDB collection helpers for Muninn.
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
    # ChromaDB rejects empty dicts; use None when there are no metadata fields.
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
    """
    Semantic search. Returns a list of result dicts with keys:
    id, document, metadata, distance.
    """
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
    """Return paginated memory entries (chronological by insertion order)."""
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
    """
    Delete all symbol entries for a given file path.

    Returns the count of deleted entries.
    """
    if collection.count() == 0:
        return 0
    results = collection.get(where={"file": file_path}, include=[])
    ids = results["ids"]
    if not ids:
        return 0
    collection.delete(ids=ids)
    return len(ids)
