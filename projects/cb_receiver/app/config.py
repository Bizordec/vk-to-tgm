from __future__ import annotations

import secrets
from typing import Literal

from pydantic import BaseSettings

VttLanguage = Literal["en", "ru"]


class Settings(BaseSettings):
    VK_COMMUNITY_ID: int
    VK_COMMUNITY_TOKEN: str

    VK_SERVER_TITLE: str = "vk-to-tgm"
    SERVER_URL: str
    VK_SERVER_SECRET: str = secrets.token_hex(25)

    VTT_IGNORE_ADS: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
