from __future__ import annotations

import json
from functools import lru_cache
from typing import Iterable, Iterator

import requests

from ..config import settings


class OllamaClient:
    def __init__(self, host: str, preferred_model: str, timeout_seconds: int = 90):
        self.host = host.rstrip("/")
        self.preferred_model = preferred_model
        self.timeout_seconds = timeout_seconds

    @lru_cache(maxsize=1)
    def available_models(self, timeout_seconds: float = 10) -> list[str]:
        response = requests.get(f"{self.host}/api/tags", timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        models = []
        for item in payload.get("models", []):
            name = item.get("name") or item.get("model")
            if name:
                models.append(name)
        return models

    def is_available(self, timeout_seconds: float = 2.0) -> bool:
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=timeout_seconds)
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def choose_model(self, timeout_seconds: float = 10) -> str:
        models = self.available_models(timeout_seconds=timeout_seconds)
        candidates = [self.preferred_model, "llama3:latest", "llama3:8b", "mistral:latest", "mistral"]
        for candidate in candidates:
            if candidate in models:
                return candidate
        return models[0] if models else self.preferred_model

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
        timeout_seconds: int | None = None,
        resolve_model: bool = True,
    ) -> dict | Iterator[str]:
        active_model = model or (self.choose_model() if resolve_model else self.preferred_model)
        request_timeout = timeout_seconds if timeout_seconds is not None else self.timeout_seconds
        payload = {
            "model": active_model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": 0.25,
                "top_p": 0.9,
            },
        }
        response = requests.post(f"{self.host}/api/chat", json=payload, timeout=request_timeout, stream=stream)
        response.raise_for_status()

        if not stream:
            data = response.json()
            return data

        def iterator() -> Iterator[str]:
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                try:
                    data = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                chunk = (data.get("message") or {}).get("content") or ""
                if chunk:
                    yield chunk
                if data.get("done"):
                    break

        return iterator()


ollama_client = OllamaClient(
    host=settings.ollama_host,
    preferred_model=settings.ollama_chat_model,
    timeout_seconds=settings.request_timeout_seconds,
)
