import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    wsip_tokens: str  # raw JSON string — parsed on access

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def token_map(self) -> dict[str, dict]:
        return json.loads(self.wsip_tokens)


settings = Settings()
