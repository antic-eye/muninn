import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGetEmbedding:
    def test_returns_list_of_floats(self, respx_mock):
        """Happy path: Ollama returns a valid embedding."""
        import httpx
        import respx

        fake_vector = [0.1] * 1024
        with respx.mock:
            respx.post("http://localhost:11434/api/embed").mock(
                return_value=httpx.Response(200, json={"embeddings": [fake_vector]})
            )
            from muninn_embed import get_embedding

            result = get_embedding("hello world")
            assert isinstance(result, list)
            assert len(result) == 1024
            assert all(isinstance(v, float) for v in result)

    def test_raises_on_http_error(self, respx_mock):
        import httpx
        import respx

        with respx.mock:
            respx.post("http://localhost:11434/api/embed").mock(
                return_value=httpx.Response(500, text="Internal Server Error")
            )
            from muninn_embed import get_embedding, EmbeddingError

            with pytest.raises(EmbeddingError):
                get_embedding("test")

    def test_env_var_overrides_base_url(self, monkeypatch, respx_mock):
        import httpx
        import respx

        monkeypatch.setenv("MUNINN_OLLAMA_URL", "http://custom-host:11434")
        fake_vector = [0.5] * 1024
        with respx.mock:
            respx.post("http://custom-host:11434/api/embed").mock(
                return_value=httpx.Response(200, json={"embeddings": [fake_vector]})
            )
            import importlib
            import muninn_embed

            importlib.reload(muninn_embed)
            result = muninn_embed.get_embedding("hello")
            assert result == fake_vector
