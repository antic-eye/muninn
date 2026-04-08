"""Unit tests for symbol handler functions in muninn.py."""

import pytest
import chromadb
from muninn_mcp import chroma as mc
from muninn_mcp import embed as me
from muninn_mcp import project as mp


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
        from muninn_mcp.server import handle_symbol_index

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
        from muninn_mcp.server import handle_symbol_index

        symbols = [
            {"name": "ClassA", "kind": "class", "file": "foo.py", "line": 1},
            {"name": "method_b", "kind": "method", "file": "foo.py", "line": 10},
        ]
        result = handle_symbol_index(symbols)
        assert result["count"] == 2

    def test_upsert_overwrites_existing(self, fake_client, fake_embedding, project):
        from muninn_mcp.server import handle_symbol_index, handle_symbol_search

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
        assert results[0]["metadata"]["docstring"] == "updated docstring"

    def test_raises_on_missing_required_fields(
        self, fake_client, fake_embedding, project
    ):
        from muninn_mcp.server import handle_symbol_index

        with pytest.raises((KeyError, ValueError)):
            handle_symbol_index([{"kind": "function"}])  # missing name and file


class TestHandleSymbolSearch:
    def test_returns_empty_list_when_no_symbols(
        self, fake_client, fake_embedding, project
    ):
        from muninn_mcp.server import handle_symbol_search

        results = handle_symbol_search("validate jwt", top_k=5)
        assert results == []

    def test_returns_results_after_indexing(self, fake_client, fake_embedding, project):
        from muninn_mcp.server import handle_symbol_index, handle_symbol_search

        handle_symbol_index(
            [
                {
                    "name": "validate_jwt",
                    "kind": "function",
                    "file": "auth/jwt.py",
                    "line": 42,
                    "signature": "def validate_jwt(token: str) -> dict",
                    "docstring": "Validates a JWT token and returns decoded payload.",
                    "callers": ["login_handler"],
                }
            ]
        )
        results = handle_symbol_search("JWT validation", top_k=5)
        assert len(results) >= 1
        assert results[0]["metadata"]["name"] == "validate_jwt"

    def test_result_has_expected_keys(self, fake_client, fake_embedding, project):
        from muninn_mcp.server import handle_symbol_index, handle_symbol_search

        handle_symbol_index(
            [
                {
                    "name": "MyClass",
                    "kind": "class",
                    "file": "models.py",
                    "line": 1,
                }
            ]
        )
        results = handle_symbol_search("MyClass", top_k=5)
        assert len(results) == 1
        r = results[0]
        assert "id" in r
        assert "document" in r
        assert "metadata" in r
        assert "distance" in r


class TestHandleSymbolDeleteFile:
    def test_deletes_symbols_for_file(self, fake_client, fake_embedding, project):
        from muninn_mcp.server import handle_symbol_index, handle_symbol_delete_file

        handle_symbol_index(
            [
                {
                    "name": "func_a",
                    "kind": "function",
                    "file": "auth/jwt.py",
                    "line": 1,
                },
                {
                    "name": "func_b",
                    "kind": "function",
                    "file": "auth/jwt.py",
                    "line": 10,
                },
                {"name": "func_c", "kind": "function", "file": "other.py", "line": 5},
            ]
        )
        result = handle_symbol_delete_file("auth/jwt.py")
        assert result["deleted"] == 2
        assert result["file"] == "auth/jwt.py"

    def test_returns_zero_when_file_not_indexed(
        self, fake_client, fake_embedding, project
    ):
        from muninn_mcp.server import handle_symbol_delete_file

        result = handle_symbol_delete_file("nonexistent.py")
        assert result["deleted"] == 0


class TestHandleSymbolWipe:
    def test_wipe_requires_confirm(self, fake_client, fake_embedding, project):
        from muninn_mcp.server import handle_symbol_wipe

        with pytest.raises(ValueError, match="confirm=True"):
            handle_symbol_wipe(confirm=False)

    def test_wipe_deletes_all_symbols(self, fake_client, fake_embedding, project):
        from muninn_mcp.server import handle_symbol_index, handle_symbol_wipe

        handle_symbol_index(
            [
                {"name": "a", "kind": "function", "file": "x.py", "line": 1},
                {"name": "b", "kind": "function", "file": "x.py", "line": 2},
            ]
        )
        result = handle_symbol_wipe(confirm=True)
        assert result["wiped"] is True
        assert result["entries_deleted"] == 2

    def test_wipe_empty_index_returns_zero(self, fake_client, fake_embedding, project):
        from muninn_mcp.server import handle_symbol_wipe

        result = handle_symbol_wipe(confirm=True)
        assert result["wiped"] is True
        assert result["entries_deleted"] == 0
