import gettext
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    VK_KATE_TOKEN: str

    TGM_API_ID: int
    TGM_API_HASH: str

    TGM_BOT_TOKEN: str
    TGM_BOT_SESSION: str

    TGM_CLIENT_PHONE: str
    TGM_CLIENT_SESSION: str

    TGM_CHANNEL_ID: int
    TGM_PL_CHANNEL_ID: int = 0

    TGM_PROXY_TYPE: Literal["socks5", "socks4", "http"] = "socks5"
    TGM_PROXY_ADDR: str | None = None
    TGM_PROXY_PORT: int | None = None
    TGM_PROXY_RDNS: bool = True
    TGM_PROXY_USER: str | None = None
    TGM_PROXY_PASS: str | None = None
    TGM_PROXY_MTPROTO_SECRET: str | None = None
    TGM_PROXY_MTPROTO_CONNECTION: Literal[
        "abridged",
        "intermediate",
        "randomized_intermediate",
    ] = "randomized_intermediate"

    VTT_LANGUAGE: Literal["en", "ru"] = "en"


settings = Settings()

_ = gettext.translation("tgm_bot", "locales", languages=[settings.VTT_LANGUAGE]).gettext
