"""
Tests for global memory handler functions.
These test the business logic of each global tool without spinning up the MCP server.
"""

import os
import sys
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


class TestGlobalMemoryHandlers:
    def test_handle_global_memory_write_returns_id(self, fake_client, fake_embedding):
        from muninn import handle_global_memory_write

        result = handle_global_memory_write(
            text="To log in to OpenShift: oc login --token=<token> --server=<url>",
            memory_type="note",
            tags="openshift,auth,infra",
        )
        assert "id" in result
        assert result["project"] == "__global__"

    def test_handle_global_memory_search_returns_results(
        self, fake_client, fake_embedding
    ):
        from muninn import handle_global_memory_write, handle_global_memory_search

        handle_global_memory_write(
            text="OpenShift login procedure",
            memory_type="note",
            tags="openshift",
        )
        results = handle_global_memory_search(query="openshift", top_k=5)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_handle_global_memory_list_returns_list(self, fake_client, fake_embedding):
        from muninn import handle_global_memory_write, handle_global_memory_list

        handle_global_memory_write(
            text="Some global knowledge", memory_type="note", tags=""
        )
        result = handle_global_memory_list(limit=10, offset=0)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_handle_global_memory_delete(self, fake_client, fake_embedding):
        from muninn import handle_global_memory_write, handle_global_memory_delete

        written = handle_global_memory_write(
            text="to delete", memory_type="note", tags=""
        )
        result = handle_global_memory_delete(entry_id=written["id"])
        assert result["deleted"] is True

    def test_handle_global_memory_delete_not_found(self, fake_client, fake_embedding):
        from muninn import handle_global_memory_delete

        result = handle_global_memory_delete(entry_id="nonexistent-id")
        assert result["deleted"] is False
        assert result["error"] == "not found"

    def test_handle_global_memory_wipe_requires_confirm(
        self, fake_client, fake_embedding
    ):
        from muninn import handle_global_memory_wipe

        with pytest.raises(ValueError, match="confirm=True"):
            handle_global_memory_wipe(confirm=False)

    def test_handle_global_memory_wipe_with_confirm(self, fake_client, fake_embedding):
        from muninn import handle_global_memory_write, handle_global_memory_wipe

        handle_global_memory_write(text="to be wiped", memory_type="note", tags="")
        result = handle_global_memory_wipe(confirm=True)
        assert result["wiped"] is True
        assert result["entries_deleted"] >= 1

    def test_global_memory_is_isolated_from_project_memory(
        self, fake_client, fake_embedding, monkeypatch
    ):
        """Global collection must not bleed into project memory and vice versa."""
        import muninn_project as mp

        monkeypatch.setattr(mp, "detect_project_name", lambda: "some-project")
        from muninn import (
            handle_memory_write,
            handle_memory_search,
            handle_global_memory_write,
            handle_global_memory_search,
        )

        handle_memory_write(text="project-only data", memory_type="note", tags="")
        handle_global_memory_write(text="global-only data", memory_type="note", tags="")

        project_results = handle_memory_search(query="global-only data", top_k=5)
        global_results = handle_global_memory_search(query="project-only data", top_k=5)

        project_texts = [r["document"] for r in project_results]
        global_texts = [r["document"] for r in global_results]

        assert not any("global-only" in t for t in project_texts)
        assert not any("project-only" in t for t in global_texts)
