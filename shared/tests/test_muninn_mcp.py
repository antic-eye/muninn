"""
Smoke tests for the MCP tool handler functions.
These test the business logic of each tool without spinning up the MCP server.
"""

import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def fake_client(tmp_path, monkeypatch):
    """Patch get_client to return a temp-dir ChromaDB client."""
    import chromadb
    import muninn_chroma as mc

    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    monkeypatch.setattr(mc, "get_client", lambda: client)
    return client


@pytest.fixture
def fake_embedding(monkeypatch):
    """Patch get_embedding to avoid Ollama dependency."""
    import muninn_embed as me

    monkeypatch.setattr(me, "get_embedding", lambda text: [0.1] * 1024)


class TestToolHandlers:
    def test_handle_memory_write_returns_id(
        self, fake_client, fake_embedding, monkeypatch
    ):
        import muninn_project as mp

        monkeypatch.setattr(mp, "detect_project_name", lambda: "test-project")
        from muninn import handle_memory_write

        result = handle_memory_write(
            text="We decided to use JWT for auth",
            memory_type="decision",
            tags="auth,security",
        )
        assert "id" in result
        assert result["project"] == "test-project"

    def test_handle_memory_search_returns_results(
        self, fake_client, fake_embedding, monkeypatch
    ):
        import muninn_project as mp

        monkeypatch.setattr(mp, "detect_project_name", lambda: "test-project")
        from muninn import handle_memory_write, handle_memory_search

        handle_memory_write(text="JWT auth decision", memory_type="decision", tags="")
        results = handle_memory_search(query="auth", top_k=5)
        assert isinstance(results, list)

    def test_handle_memory_list_returns_list(
        self, fake_client, fake_embedding, monkeypatch
    ):
        import muninn_project as mp

        monkeypatch.setattr(mp, "detect_project_name", lambda: "test-project")
        from muninn import handle_memory_write, handle_memory_list

        handle_memory_write(text="some memory", memory_type="note", tags="")
        result = handle_memory_list(limit=10, offset=0)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_handle_memory_delete(self, fake_client, fake_embedding, monkeypatch):
        import muninn_project as mp

        monkeypatch.setattr(mp, "detect_project_name", lambda: "test-project")
        from muninn import handle_memory_write, handle_memory_delete

        written = handle_memory_write(text="to delete", memory_type="note", tags="")
        result = handle_memory_delete(entry_id=written["id"])
        assert result["deleted"] is True

    def test_handle_memory_list_projects(
        self, fake_client, fake_embedding, monkeypatch
    ):
        import muninn_project as mp

        monkeypatch.setattr(mp, "detect_project_name", lambda: "proj-a")
        from muninn import handle_memory_write, handle_memory_list_projects

        handle_memory_write(text="proj-a memory", memory_type="note", tags="")
        projects = handle_memory_list_projects()
        assert any("proj-a" in p for p in projects)
