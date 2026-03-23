"""
Unit tests for Markdown formatter functions in muninn.py.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from muninn import (
    format_write_result,
    format_search_results,
    format_list_results,
    format_delete_result,
    format_wipe_result,
    format_projects_list,
)


class TestFormatWriteResult:
    def test_basic(self):
        result = {"id": "abc12345-xxxx", "project": "myproject", "type": "decision"}
        md = format_write_result(result, tags="auth,jwt")
        assert "✅" in md
        assert "decision" in md
        assert "abc12345" in md
        assert "myproject" in md
        assert "auth,jwt" in md

    def test_no_tags(self):
        result = {"id": "abc12345-xxxx", "project": "p", "type": "note"}
        md = format_write_result(result, tags="")
        assert "✅" in md
        assert "note" in md


class TestFormatSearchResults:
    def test_empty(self):
        md = format_search_results([])
        assert "No memories" in md or "0" in md

    def test_single_result(self):
        results = [
            {
                "id": "abc12345",
                "document": "We decided to use JWT",
                "metadata": {
                    "type": "decision",
                    "session_date": "2026-03-20",
                    "tags": "auth",
                },
                "distance": 0.1,
            }
        ]
        md = format_search_results(results)
        assert "decision" in md
        assert "We decided to use JWT" in md
        assert "2026-03-20" in md

    def test_multiple_results(self):
        results = [
            {
                "id": f"id{i}",
                "document": f"doc {i}",
                "metadata": {"type": "note", "session_date": "2026-01-01", "tags": ""},
                "distance": 0.2,
            }
            for i in range(3)
        ]
        md = format_search_results(results)
        assert "3" in md or md.count("**") >= 3


class TestFormatListResults:
    def test_empty(self):
        md = format_list_results([], offset=0)
        assert "No memories" in md or "0" in md

    def test_with_entries(self):
        entries = [
            {
                "id": "id1",
                "document": "Some memory",
                "metadata": {
                    "type": "summary",
                    "session_date": "2026-03-01",
                    "tags": "foo",
                },
            }
        ]
        md = format_list_results(entries, offset=0)
        assert "summary" in md
        assert "Some memory" in md

    def test_offset_shown(self):
        md = format_list_results([], offset=10)
        assert "10" in md


class TestFormatDeleteResult:
    def test_deleted(self):
        md = format_delete_result({"deleted": True, "id": "abc12345-xxxx"})
        assert "🗑️" in md or "Deleted" in md
        assert "abc12345" in md

    def test_not_found(self):
        md = format_delete_result(
            {"deleted": False, "id": "abc12345-xxxx", "error": "not found"}
        )
        assert "⚠️" in md or "not found" in md.lower()


class TestFormatWipeResult:
    def test_wiped(self):
        md = format_wipe_result(
            {"wiped": True, "project": "myproject", "entries_deleted": 5}
        )
        assert "myproject" in md
        assert "5" in md


class TestFormatProjectsList:
    def test_empty(self):
        md = format_projects_list([])
        assert "No projects" in md or "0" in md or "_" in md

    def test_with_projects(self):
        md = format_projects_list(["alpha", "beta"])
        assert "alpha" in md
        assert "beta" in md
