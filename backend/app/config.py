"""
Application settings loaded from environment / .env via pydantic-settings.

Required env vars:
  DATABASE_URL  — SQLAlchemy connection string (e.g. postgresql://...)
  WSIP_TOKENS   — JSON object mapping token strings to user dicts,
                  e.g. '{"admin-token": {"roles": ["admin"], "user_id": "..."}}'
"""

import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings model; values are read from env vars or .env at import time."""

    database_url: str
    wsip_tokens: str  # raw JSON string — parsed on access

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def token_map(self) -> dict[str, dict]:
        """Parse WSIP_TOKENS JSON into a token → user-dict mapping."""
        return json.loads(self.wsip_tokens)


settings = Settings()
