"""Unit tests for symbol handler functions in muninn.py."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import chromadb
import muninn_chroma as mc
import muninn_embed as me
import muninn_project as mp


@pytest.fixture
def fake_client(tmp_path, monkeypatch):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    monkeypatch.setattr(mc, "get_client", lambda: client)
    return client


@pytest.fixture
def fake_embedding(monkeypatch):
    monkeypatch.setattr(me, "get_embedding", lambda text: [0.1] * 1024)


@pytest.fixture
def project(monkeypatch):
    monkeypatch.setattr(mp, "detect_project_name", lambda: "test-project")


class TestHandleSymbolIndex:
    def test_indexes_single_symbol(self, fake_client, fake_embedding, project):
        from muninn import handle_symbol_index

        result = handle_symbol_index(
            [
                {
                    "name": "validate_jwt",
                    "kind": "function",
                    "file": "auth/jwt.py",
                    "line": 42,
                    "signature": "def validate_jwt(token: str) -> dict",
                    "docstring": "Validates a JWT token.",
                    "callers": ["login_handler"],
                }
            ]
        )
        assert result["count"] == 1
        assert result["file"] == "auth/jwt.py"

    def test_indexes_multiple_symbols(self, fake_client, fake_embedding, project):
        from muninn import handle_symbol_index

        symbols = [
            {"name": "ClassA", "kind": "class", "file": "foo.py", "line": 1},
            {"name": "method_b", "kind": "method", "file": "foo.py", "line": 10},
        ]
        result = handle_symbol_index(symbols)
        assert result["count"] == 2

    def test_upsert_overwrites_existing(self, fake_client, fake_embedding, project):
        from muninn import handle_symbol_index, handle_symbol_search

        sym = {
            "name": "my_func",
            "kind": "function",
            "file": "a.py",
            "line": 1,
            "docstring": "original",
        }
        handle_symbol_index([sym])
        sym2 = {**sym, "docstring": "updated docstring"}
        handle_symbol_index([sym2])
        results = handle_symbol_search("my_func", top_k=5)
        # should still only have 1 entry (upsert, not duplicate)
        assert len(results) == 1

    def test_raises_on_missing_required_fields(
        self, fake_client, fake_embedding, project
    ):
        from muninn import handle_symbol_index

        with pytest.raises((KeyError, ValueError)):
            handle_symbol_index([{"kind": "function"}])  # missing name and file
