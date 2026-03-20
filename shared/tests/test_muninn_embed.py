import os
import sys
import pytest
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import muninn_embed


class TestGetEmbedding:
    def test_returns_list_of_floats(self, respx_mock):
        """Happy path: Ollama returns a valid embedding."""
        fake_vector = [0.1] * 1024
        respx_mock.post("http://localhost:11434/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": [fake_vector]})
        )
        result = muninn_embed.get_embedding("hello world")
        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(isinstance(v, float) for v in result)

    def test_raises_on_http_error(self, respx_mock):
        respx_mock.post("http://localhost:11434/api/embed").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(muninn_embed.EmbeddingError):
            muninn_embed.get_embedding("test")

    def test_env_var_overrides_base_url(self, monkeypatch, respx_mock):
        """OLLAMA_URL constant patched directly — no reload, monkeypatch auto-restores."""
        monkeypatch.setattr(muninn_embed, "OLLAMA_URL", "http://custom-host:11434")
        fake_vector = [0.5] * 1024
        respx_mock.post("http://custom-host:11434/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": [fake_vector]})
        )
        result = muninn_embed.get_embedding("hello")
        assert result == fake_vector

    def test_raises_on_connection_error(self, respx_mock):
        """Connection failure raises EmbeddingError (Ollama not running)."""
        respx_mock.post("http://localhost:11434/api/embed").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        with pytest.raises(muninn_embed.EmbeddingError, match="Cannot reach Ollama"):
            muninn_embed.get_embedding("test")
