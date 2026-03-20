"""
End-to-end test: write → search → verify result.

Requires Ollama running locally with mxbai-embed-large.
Skip automatically if Ollama is not available.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ollama_available() -> bool:
    import httpx

    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
class TestE2E:
    @pytest.fixture
    def live_client(self, tmp_path, monkeypatch):
        import chromadb
        import muninn_chroma as mc
        import muninn_project as mp

        client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
        # DATA_DIR is evaluated at import time in muninn_chroma, so setenv won't
        # affect an already-imported module. Patch get_client directly instead.
        monkeypatch.setattr(mc, "get_client", lambda: client)
        monkeypatch.setattr(mp, "detect_project_name", lambda: "e2e-test")
        return client

    def test_write_then_search_returns_entry(self, live_client):
        from muninn import handle_memory_write, handle_memory_search

        written = handle_memory_write(
            text="We use JWT tokens for all API authentication. RS256 algorithm.",
            memory_type="decision",
            tags="auth,jwt",
        )
        assert "id" in written

        results = handle_memory_search("JWT authentication token", top_k=3)
        assert len(results) > 0
        assert any("JWT" in r["document"] for r in results)

    def test_write_multiple_search_returns_most_relevant(self, live_client):
        from muninn import handle_memory_write, handle_memory_search

        handle_memory_write("Database uses PostgreSQL with pgvector", "decision", "db")
        handle_memory_write("JWT RS256 for authentication", "decision", "auth")
        handle_memory_write("React frontend with Vite build", "decision", "frontend")

        results = handle_memory_search("auth token security", top_k=1)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert (
            "JWT" in results[0]["document"] or "auth" in results[0]["document"].lower()
        ), f"Unexpected top result: {results[0]['document']!r}"
