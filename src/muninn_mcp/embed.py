"""
muninn_embed.py — Ollama embedding via HTTP for Muninn.

Env vars:
    MUNINN_OLLAMA_URL    Ollama base URL (default: http://localhost:11434)
    MUNINN_EMBED_MODEL   Embedding model  (default: mxbai-embed-large:latest)
    MUNINN_OLLAMA_TOKEN  Bearer token for authenticated Ollama endpoints (optional)

API auto-detection:
    If MUNINN_OLLAMA_URL contains "/v1" the OpenAI-compatible endpoint
    (POST /v1/embeddings) is used.  Otherwise the native Ollama endpoint
    (POST /api/embed) is used.  This lets Muninn work transparently with
    both a local Ollama instance and proxies such as Mimir that only expose
    the OpenAI-compatible surface.
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


def _is_openai_compat(base_url: str) -> bool:
    """Return True when *base_url* points to an OpenAI-compatible proxy.

    Detection rule: the URL already contains '/v1' (case-insensitive).
    Local Ollama never includes '/v1' in its base URL; proxies that only
    expose the OpenAI-compatible surface do.
    """
    return "/v1" in base_url.lower()


class EmbeddingError(RuntimeError):
    """Raised when the Ollama embedding call fails."""


def _call_ollama(base_url: str, model: str, text: str, headers: dict) -> list[float]:
    """Call the native Ollama /api/embed endpoint."""
    url = f"{base_url}/api/embed"
    payload = {"model": model, "input": text}
    response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    try:
        return data["embeddings"][0]
    except (KeyError, IndexError) as exc:
        raise EmbeddingError(f"Unexpected Ollama response shape: {data}") from exc


def _call_openai_compat(
    base_url: str, model: str, text: str, headers: dict
) -> list[float]:
    """Call an OpenAI-compatible /v1/embeddings endpoint."""
    # Normalise: strip a trailing /v1 so we can append it ourselves.
    clean_base = base_url.rstrip("/")
    if not clean_base.endswith("/v1"):
        clean_base = f"{clean_base}/v1"
    url = f"{clean_base}/embeddings"
    payload = {"model": model, "input": text}
    response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    try:
        return data["data"][0]["embedding"]
    except (KeyError, IndexError) as exc:
        raise EmbeddingError(
            f"Unexpected OpenAI-compat response shape: {data}"
        ) from exc


def get_embedding(text: str) -> list[float]:
    """
    Return an embedding vector for *text*.

    Automatically selects between the native Ollama API and the
    OpenAI-compatible API based on MUNINN_OLLAMA_URL (see module docstring).

    Raises EmbeddingError on non-2xx HTTP responses or malformed payloads.
    """
    headers = _build_headers()
    try:
        if _is_openai_compat(OLLAMA_URL):
            return _call_openai_compat(OLLAMA_URL, EMBED_MODEL, text, headers)
        return _call_ollama(OLLAMA_URL, EMBED_MODEL, text, headers)
    except httpx.HTTPStatusError as exc:
        raise EmbeddingError(
            f"Ollama returned {exc.response.status_code} for embed request"
        ) from exc
    except httpx.RequestError as exc:
        raise EmbeddingError(f"Cannot reach Ollama at {OLLAMA_URL}: {exc}") from exc
