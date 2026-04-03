"""LLM client abstraction for the evaluation system.

ModelClient is the ABC; OllamaClient targets a local Ollama instance.
Each trajectory run gets a fresh client instance — no shared state between runs.
"""

import os
from abc import ABC, abstractmethod

import requests


class ModelClient(ABC):
    """Abstract base class for LLM completion."""

    @abstractmethod
    def complete(self, history: list[tuple[str, str]], prompt: str) -> str:
        """Return model response given conversation history and a new prompt.

        history: list of (user_prompt, assistant_response) pairs from prior turns
        prompt: the current turn's prompt u_t
        Returns: response text y_t
        """
        ...


class OllamaClient(ModelClient):
    """ModelClient targeting a local Ollama instance via /api/chat.

    Configuration via constructor args or environment variables:
      OLLAMA_BASE_URL — default http://localhost:11434
      OLLAMA_MODEL    — default qwen2.5:7b
    """

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or os.environ.get(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2:1b")

    def complete(self, history: list[tuple[str, str]], prompt: str) -> str:
        messages = []
        for user_msg, assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
