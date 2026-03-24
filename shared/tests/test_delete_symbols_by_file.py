"""Tests for delete_symbols_by_file ChromaDB helper."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import chromadb
import muninn_chroma as mc


@pytest.fixture
def col(tmp_path):
    """Return a fresh ChromaDB collection."""
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    return mc.get_collection(client, "test_symbols")


class TestDeleteSymbolsByFile:
    def test_deletes_matching_entries(self, col):
        col.add(
            ids=["id1", "id2", "id3"],
            documents=["doc1", "doc2", "doc3"],
            embeddings=[[0.1] * 1024, [0.2] * 1024, [0.3] * 1024],
            metadatas=[
                {"file": "auth/jwt.py"},
                {"file": "auth/jwt.py"},
                {"file": "other/file.py"},
            ],
        )
        deleted = mc.delete_symbols_by_file(col, "auth/jwt.py")
        assert deleted == 2
        assert col.count() == 1

    def test_returns_zero_when_no_match(self, col):
        col.add(
            ids=["id1"],
            documents=["doc1"],
            embeddings=[[0.1] * 1024],
            metadatas=[{"file": "other/file.py"}],
        )
        deleted = mc.delete_symbols_by_file(col, "nonexistent.py")
        assert deleted == 0
        assert col.count() == 1

    def test_empty_collection_returns_zero(self, col):
        deleted = mc.delete_symbols_by_file(col, "auth/jwt.py")
        assert deleted == 0
