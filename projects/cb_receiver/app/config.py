from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VttLanguage = Literal["en", "ru"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    VK_COMMUNITY_ID: int
    VK_COMMUNITY_TOKEN: str

    VK_SERVER_TITLE: str = "vk-to-tgm"
    SERVER_URL: str
    VK_SERVER_SECRET: str = secrets.token_hex(25)

    VTT_IGNORE_ADS: bool = True

    @field_validator("SERVER_URL")
    @classmethod
    def add_trailing_slash(cls, val: str) -> str:
        return val if val.endswith("/") else f"{val}/"


@lru_cache
def get_settings() -> Settings:  # pragma: no cover
    return Settings()
