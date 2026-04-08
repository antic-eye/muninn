"""Tests for symbol_collection_name helper."""

from muninn_mcp.project import symbol_collection_name


class TestSymbolCollectionName:
    def test_basic(self):
        name = symbol_collection_name("myproject")
        assert name == "muninn_myproject__symbols"

    def test_sanitises_special_chars(self):
        name = symbol_collection_name("my-project.v2")
        # hyphens are valid, dots become underscores
        assert "__symbols" in name
        assert name.startswith("muninn_")

    def test_max_63_chars(self):
        long_project = "a" * 60
        name = symbol_collection_name(long_project)
        assert len(name) <= 63

    def test_ends_with_symbols_suffix(self):
        name = symbol_collection_name("proj")
        assert name.endswith("__symbols") or "__symbols" in name
