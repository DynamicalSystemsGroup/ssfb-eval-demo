"""Tests for model_client.py — ModelClient ABC and OllamaClient.

All tests mock requests.post — no running Ollama instance needed.
"""

import pytest

from apollo_eval.model_client import ModelClient, OllamaClient


class TestModelClientABC:
    # Req: ModelClient is abstract and cannot be instantiated directly
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ModelClient()


class TestOllamaClientDefaults:
    # Req: Ollama API base URL configurable via OLLAMA_BASE_URL env var
    def test_default_base_url(self):
        client = OllamaClient()
        assert client.base_url == "http://localhost:11434"

    def test_env_override_base_url(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://remote:8080")
        client = OllamaClient()
        assert client.base_url == "http://remote:8080"

    def test_explicit_base_url(self):
        client = OllamaClient(base_url="http://custom:9999")
        assert client.base_url == "http://custom:9999"

    # Req: Model name configurable via OLLAMA_MODEL env var
    def test_default_model(self):
        client = OllamaClient()
        assert client.model == "llama3.2:1b"

    def test_env_override_model(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "llama3:8b")
        client = OllamaClient()
        assert client.model == "llama3:8b"

    def test_explicit_model(self):
        client = OllamaClient(model="gemma:2b")
        assert client.model == "gemma:2b"


class TestOllamaClientComplete:
    # Req: complete() sends correct payload to /api/chat
    def test_sends_correct_payload(self, monkeypatch):
        captured = {}

        class FakeResponse:
            status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                return {"message": {"content": "response text"}}

        def fake_post(url, json=None, **kwargs):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

        monkeypatch.setattr("apollo_eval.model_client.requests.post", fake_post)
        client = OllamaClient(base_url="http://test:1234", model="test-model")
        client.complete([], "Hello")

        assert captured["url"] == "http://test:1234/api/chat"
        assert captured["json"]["model"] == "test-model"
        assert captured["json"]["stream"] is False
        assert captured["json"]["messages"] == [{"role": "user", "content": "Hello"}]

    # Req: complete() builds message list from history + prompt
    def test_builds_messages_from_history(self, monkeypatch):
        captured = {}

        class FakeResponse:
            status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                return {"message": {"content": "turn 3 response"}}

        def fake_post(url, json=None, **kwargs):
            captured["json"] = json
            return FakeResponse()

        monkeypatch.setattr("apollo_eval.model_client.requests.post", fake_post)
        client = OllamaClient()

        history = [("prompt 1", "response 1"), ("prompt 2", "response 2")]
        client.complete(history, "prompt 3")

        expected_messages = [
            {"role": "user", "content": "prompt 1"},
            {"role": "assistant", "content": "response 1"},
            {"role": "user", "content": "prompt 2"},
            {"role": "assistant", "content": "response 2"},
            {"role": "user", "content": "prompt 3"},
        ]
        assert captured["json"]["messages"] == expected_messages

    # Req: complete() returns response content string
    def test_returns_content(self, monkeypatch):
        class FakeResponse:
            status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                return {"message": {"content": "The answer is 42."}}

        monkeypatch.setattr("apollo_eval.model_client.requests.post", lambda *a, **k: FakeResponse())
        client = OllamaClient()
        result = client.complete([], "What is the answer?")
        assert result == "The answer is 42."

    # Req: complete() raises on HTTP errors
    def test_raises_on_http_error(self, monkeypatch):
        class FakeResponse:
            status_code = 500
            def raise_for_status(self):
                raise Exception("500 Server Error")

        monkeypatch.setattr("apollo_eval.model_client.requests.post", lambda *a, **k: FakeResponse())
        client = OllamaClient()
        with pytest.raises(Exception, match="500"):
            client.complete([], "Hello")

    # Req: complete() works with empty history (first turn)
    def test_empty_history(self, monkeypatch):
        captured = {}

        class FakeResponse:
            status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                return {"message": {"content": "first response"}}

        def fake_post(url, json=None, **kwargs):
            captured["json"] = json
            return FakeResponse()

        monkeypatch.setattr("apollo_eval.model_client.requests.post", fake_post)
        client = OllamaClient()
        result = client.complete([], "First prompt")

        assert len(captured["json"]["messages"]) == 1
        assert result == "first response"
