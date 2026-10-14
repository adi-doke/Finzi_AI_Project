from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"), override=False)


def _normalize_host(value: str | None, default: str) -> str:
    host = (value or default).strip()
    return host[:-1] if host.endswith("/") else host


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    session_cookie_secure: bool
    session_days: int
    ollama_host: str
    ollama_chat_model: str
    ollama_embedding_model: str
    request_timeout_seconds: int
    max_chat_history_messages: int
    max_recent_transactions: int


settings = Settings(
    database_url=(
        os.environ.get("DATABASE_URL")
        or os.environ.get("MYSQL_DATABASE_URL")
        or os.environ.get("MYSQL_URL")
        or "sqlite:///./backend/data/dev_transactions.db"
    ),
    secret_key=os.environ.get("SECRET_KEY", "finzi-dev-secret-key"),
    session_cookie_secure=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
    session_days=int(os.environ.get("SESSION_DAYS", "7")),
    ollama_host=_normalize_host(os.environ.get("OLLAMA_HOST"), "http://127.0.0.1:11434"),
    ollama_chat_model=os.environ.get("OLLAMA_CHAT_MODEL", os.environ.get("OLLAMA_MODEL", "llama3:latest")),
    ollama_embedding_model=os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest"),
    request_timeout_seconds=int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "90")),
    max_chat_history_messages=int(os.environ.get("MAX_CHAT_HISTORY_MESSAGES", "12")),
    max_recent_transactions=int(os.environ.get("MAX_RECENT_TRANSACTIONS", "40")),
)
