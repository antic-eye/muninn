"""Unit tests for symbol formatter functions in muninn.py."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from muninn import (
    format_symbol_index_result,
    format_symbol_search_results,
    format_symbol_delete_file_result,
    format_symbol_wipe_result,
)


class TestFormatSymbolIndexResult:
    def test_basic(self):
        result = {"count": 3, "file": "auth/jwt.py", "project": "myproject"}
        md = format_symbol_index_result(result)
        assert "✅" in md
        assert "3" in md
        assert "auth/jwt.py" in md

    def test_single_symbol(self):
        result = {"count": 1, "file": "models.py", "project": "p"}
        md = format_symbol_index_result(result)
        assert "1 symbol" in md  # confirms singular form


class TestFormatSymbolSearchResults:
    def test_empty(self):
        md = format_symbol_search_results([])
        assert md == "_No symbols matched your query._"

    def test_single_result_full_metadata(self):
        results = [
            {
                "id": "abc123",
                "document": "function validate_jwt in auth/jwt.py",
                "metadata": {
                    "kind": "function",
                    "name": "validate_jwt",
                    "file": "auth/jwt.py",
                    "line": 42,
                    "signature": "def validate_jwt(token: str) -> dict",
                    "docstring": "Validates a JWT token.",
                    "callers": "login_handler",
                },
                "distance": 0.06,
            }
        ]
        md = format_symbol_search_results(results)
        assert "validate_jwt" in md
        assert "auth/jwt.py" in md
        assert "42" in md
        assert "score: 0.94" in md
        assert "function" in md

    def test_result_without_optional_fields(self):
        results = [
            {
                "id": "xyz",
                "document": "class MyClass in models.py",
                "metadata": {
                    "kind": "class",
                    "name": "MyClass",
                    "file": "models.py",
                    "line": 1,
                    "signature": "",
                    "docstring": "",
                    "callers": "",
                },
                "distance": 0.2,
            }
        ]
        md = format_symbol_search_results(results)
        assert "MyClass" in md
        assert "models.py" in md

    def test_multiple_results_separated(self):
        results = [
            {
                "id": f"id{i}",
                "document": f"function func{i} in file{i}.py",
                "metadata": {
                    "kind": "function",
                    "name": f"func{i}",
                    "file": f"file{i}.py",
                    "line": i,
                    "signature": "",
                    "docstring": "",
                    "callers": "",
                },
                "distance": 0.1 * i,
            }
            for i in range(1, 4)
        ]
        md = format_symbol_search_results(results)
        assert "3" in md
        assert "func1" in md and "func2" in md and "func3" in md
        assert "---" in md
        assert md.count("---") == 2  # 3 results → 2 separators


class TestFormatSymbolDeleteFileResult:
    def test_deleted_some(self):
        result = {"deleted": 5, "file": "auth/jwt.py", "project": "p"}
        md = format_symbol_delete_file_result(result)
        assert "🗑️" in md
        assert "5" in md
        assert "auth/jwt.py" in md

    def test_deleted_zero(self):
        result = {"deleted": 0, "file": "ghost.py", "project": "p"}
        md = format_symbol_delete_file_result(result)
        assert "0 symbols" in md
        assert "ghost.py" in md


class TestFormatSymbolWipeResult:
    def test_wiped(self):
        result = {"wiped": True, "project": "myproject", "entries_deleted": 42}
        md = format_symbol_wipe_result(result)
        assert "💥" in md
        assert "42" in md
        assert "myproject" in md
