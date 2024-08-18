import gettext
from typing import Literal

from pydantic import BaseSettings


class Settings(BaseSettings):
    VK_KATE_TOKEN: str
    VK_OFFICIAL_TOKEN: str

    TGM_API_ID: int
    TGM_API_HASH: str

    TGM_BOT_TOKEN: str
    TGM_BOT_SESSION: str

    TGM_CLIENT_PHONE: str
    TGM_CLIENT_SESSION: str

    TGM_CHANNEL_ID: int
    TGM_PL_CHANNEL_ID: int = 0

    VTT_LANGUAGE: Literal["en", "ru"] = "en"

    class Config:
        env_file = ".env"


settings = Settings()

_ = gettext.translation("tgm_bot", "locales", languages=[settings.VTT_LANGUAGE]).gettext
