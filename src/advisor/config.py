"""Settings loaded from environment / .env.

``load_dotenv()`` populates ``os.environ`` from ``.env`` so that both these
Settings *and* the OpenAI client used by Pydantic AI pick up ``OPENAI_API_KEY``.
"""

from __future__ import annotations

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    openai_api_key: str = ""
    advisor_chat_model: str = "gpt-4.1"
    advisor_embed_model: str = "text-embedding-3-small"
    advisor_data_dir: str = "data"
    advisor_backend: str = "json"

    @property
    def chat_model(self) -> str:
        return self.advisor_chat_model

    @property
    def embed_model(self) -> str:
        return self.advisor_embed_model

    @property
    def data_dir(self) -> str:
        return self.advisor_data_dir


settings = Settings()
