# /// script
# dependencies = ["httpx"]
# ///
"""
muninn_embed.py — Ollama embedding via HTTP for Muninn.

Env vars:
    MUNINN_OLLAMA_URL    Ollama base URL (default: http://localhost:11434)
    MUNINN_EMBED_MODEL   Embedding model  (default: mxbai-embed-large:latest)
    MUNINN_OLLAMA_TOKEN  Bearer token for authenticated Ollama endpoints (optional)
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


class EmbeddingError(RuntimeError):
    """Raised when the Ollama embedding call fails."""


def get_embedding(text: str) -> list[float]:
    """
    Return a 1024-dimensional embedding vector for *text* using Ollama.

    Raises EmbeddingError on non-2xx HTTP responses or malformed payloads.
    """
    url = f"{OLLAMA_URL}/api/embed"
    payload = {"model": EMBED_MODEL, "input": text}

    try:
        response = httpx.post(url, json=payload, headers=_build_headers(), timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise EmbeddingError(
            f"Ollama returned {exc.response.status_code} for embed request"
        ) from exc
    except httpx.RequestError as exc:
        raise EmbeddingError(f"Cannot reach Ollama at {OLLAMA_URL}: {exc}") from exc

    data = response.json()
    try:
        return data["embeddings"][0]
    except (KeyError, IndexError) as exc:
        raise EmbeddingError(f"Unexpected Ollama response shape: {data}") from exc
