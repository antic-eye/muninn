import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def chroma_client(tmp_path):
    """Real ChromaDB client backed by a temp directory."""
    import chromadb

    return chromadb.PersistentClient(path=str(tmp_path / "chroma"))


class TestUpsertMemory:
    def test_upsert_stores_document(self, chroma_client):
        from muninn_chroma import upsert_memory, get_collection

        col = get_collection(chroma_client, "muninn_test")
        entry_id = str(uuid.uuid4())
        upsert_memory(
            col, entry_id, "Auth uses JWT tokens", [0.1] * 1024, {"type": "decision"}
        )
        result = col.get(ids=[entry_id])
        assert result["documents"][0] == "Auth uses JWT tokens"

    def test_upsert_is_idempotent(self, chroma_client):
        from muninn_chroma import upsert_memory, get_collection

        col = get_collection(chroma_client, "muninn_test")
        eid = str(uuid.uuid4())
        upsert_memory(col, eid, "original", [0.1] * 1024, {})
        upsert_memory(col, eid, "updated", [0.2] * 1024, {})
        result = col.get(ids=[eid])
        assert result["documents"][0] == "updated"


class TestQueryMemory:
    def test_returns_top_k_results(self, chroma_client):
        from muninn_chroma import upsert_memory, query_memory, get_collection

        col = get_collection(chroma_client, "muninn_test")
        for i in range(5):
            upsert_memory(
                col, str(uuid.uuid4()), f"memory {i}", [float(i) / 10] * 1024, {}
            )
        results = query_memory(col, [0.1] * 1024, top_k=3)
        assert len(results) == 3

    def test_empty_collection_returns_empty(self, chroma_client):
        from muninn_chroma import query_memory, get_collection

        col = get_collection(chroma_client, "muninn_empty")
        results = query_memory(col, [0.1] * 1024, top_k=5)
        assert results == []


class TestDeleteMemory:
    def test_delete_removes_entry(self, chroma_client):
        from muninn_chroma import upsert_memory, delete_memory, get_collection

        col = get_collection(chroma_client, "muninn_test")
        eid = str(uuid.uuid4())
        upsert_memory(col, eid, "to be deleted", [0.1] * 1024, {})
        delete_memory(col, eid)
        result = col.get(ids=[eid])
        assert result["documents"] == []

    def test_delete_nonexistent_raises(self, chroma_client):
        from muninn_chroma import delete_memory, get_collection, MemoryNotFoundError

        col = get_collection(chroma_client, "muninn_test")
        with pytest.raises(MemoryNotFoundError):
            delete_memory(col, "does-not-exist")


class TestListMemories:
    def test_list_returns_all_entries(self, chroma_client):
        from muninn_chroma import upsert_memory, list_memories, get_collection

        col = get_collection(chroma_client, "muninn_list_test")
        for i in range(3):
            upsert_memory(
                col,
                str(uuid.uuid4()),
                f"doc {i}",
                [float(i) / 10] * 1024,
                {"seq": str(i)},
            )
        results = list_memories(col, limit=10, offset=0)
        assert len(results) == 3
        assert all("id" in r and "document" in r and "metadata" in r for r in results)


class TestWipeCollection:
    def test_wipe_returns_count_and_empties_collection(self, chroma_client):
        from muninn_chroma import upsert_memory, wipe_collection, get_collection

        col = get_collection(chroma_client, "muninn_wipe_test")
        for i in range(3):
            upsert_memory(
                col, str(uuid.uuid4()), f"doc {i}", [float(i) / 10] * 1024, {"k": "v"}
            )
        deleted = wipe_collection(chroma_client, "muninn_wipe_test")
        assert deleted == 3
        assert col.count() == 0
