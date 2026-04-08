import pytest
import httpx

from muninn_mcp import embed as muninn_embed


class TestIsOpenAICompat:
    def test_plain_localhost_is_ollama(self):
        assert muninn_embed._is_openai_compat("http://localhost:11434") is False

    def test_url_with_v1_is_openai(self):
        assert muninn_embed._is_openai_compat("https://proxy.example.com/v1") is True

    def test_url_without_v1_is_ollama(self):
        assert muninn_embed._is_openai_compat("https://proxy.example.com") is False

    def test_case_insensitive(self):
        assert muninn_embed._is_openai_compat("https://proxy.example.com/V1") is True


class TestGetEmbedding:
    def test_returns_list_of_floats(self, respx_mock):
        """Happy path: native Ollama returns a valid embedding."""
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


class TestOpenAICompatPath:
    def test_openai_compat_url_calls_v1_embeddings(self, monkeypatch, respx_mock):
        """When OLLAMA_URL contains /v1, the OpenAI-compat endpoint is used."""
        monkeypatch.setattr(muninn_embed, "OLLAMA_URL", "https://proxy.example.com/v1")
        fake_vector = [0.2] * 1024
        respx_mock.post("https://proxy.example.com/v1/embeddings").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [{"embedding": fake_vector}],
                    "model": "mxbai-embed-large:latest",
                },
            )
        )
        result = muninn_embed.get_embedding("hello proxy")
        assert result == fake_vector

    def test_openai_compat_without_trailing_v1_appends_it(
        self, monkeypatch, respx_mock
    ):
        """If URL has no /v1 suffix but /v1 appears mid-path it still works."""
        monkeypatch.setattr(muninn_embed, "OLLAMA_URL", "https://mimir.example.com/v1")
        fake_vector = [0.3] * 512
        respx_mock.post("https://mimir.example.com/v1/embeddings").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [{"embedding": fake_vector}],
                    "model": "mxbai-embed-large:latest",
                },
            )
        )
        result = muninn_embed.get_embedding("test")
        assert result == fake_vector

    def test_openai_compat_raises_on_http_error(self, monkeypatch, respx_mock):
        monkeypatch.setattr(muninn_embed, "OLLAMA_URL", "https://proxy.example.com/v1")
        respx_mock.post("https://proxy.example.com/v1/embeddings").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        with pytest.raises(muninn_embed.EmbeddingError, match="404"):
            muninn_embed.get_embedding("test")

    def test_openai_compat_raises_on_malformed_response(self, monkeypatch, respx_mock):
        monkeypatch.setattr(muninn_embed, "OLLAMA_URL", "https://proxy.example.com/v1")
        respx_mock.post("https://proxy.example.com/v1/embeddings").mock(
            return_value=httpx.Response(200, json={"unexpected": "shape"})
        )
        with pytest.raises(
            muninn_embed.EmbeddingError, match="Unexpected OpenAI-compat"
        ):
            muninn_embed.get_embedding("test")
