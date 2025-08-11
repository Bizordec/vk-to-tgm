from __future__ import annotations

import re
from functools import partial
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import AfterValidator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from re import Pattern


DIGITS_PATTERN = re.compile(r"^[0-9]+$")
SERVER_URL_PATTERN = re.compile(r"^https?://.+$")
TGM_CHANNEL_USERNAME_PATTERN = re.compile(r"^[a-zA-Z][\w\d]{3,30}[a-zA-Z\d]$")
TGM_CHANNEL_ID_PATTERN = re.compile(r"^-100[0-9]+$")
TGM_BOT_TOKEN_PATTERN = re.compile(r"^.+:.+$")

VttLanguage = Literal["en", "ru"]


class NotMatchedPatternError(ValueError):
    def __init__(self, pattern: Pattern[str]) -> None:
        super().__init__(f"Value does not match pattern '{pattern.pattern}'")


def _check_env(value: str | int | None, pattern: Pattern[str]) -> str | int | None:
    if value and not pattern.match(str(value)):
        raise NotMatchedPatternError(pattern)
    return value


def pattern_validator(pattern: Pattern[str]) -> AfterValidator:
    return AfterValidator(partial(_check_env, pattern=pattern))


Numeric = Annotated[str, pattern_validator(DIGITS_PATTERN)]
ChannelId = Annotated[str, pattern_validator(TGM_CHANNEL_ID_PATTERN)]
ChannelName = Annotated[str, pattern_validator(TGM_CHANNEL_USERNAME_PATTERN)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    VK_KATE_TOKEN: str = ""

    VK_COMMUNITY_ID: Numeric = ""
    VK_COMMUNITY_TOKEN: str = ""

    VK_SERVER_TITLE: str = "vk-to-tgm"
    SERVER_URL: Annotated[str, pattern_validator(SERVER_URL_PATTERN)] = ""

    TGM_API_ID: Numeric = ""
    TGM_API_HASH: str = ""

    TGM_BOT_TOKEN: Annotated[str, pattern_validator(TGM_BOT_TOKEN_PATTERN)] = ""
    TGM_BOT_SESSION: str = ""

    TGM_CLIENT_PHONE: str = ""
    TGM_CLIENT_SESSION: str = ""

    TGM_CHANNEL_ID: ChannelId = ""
    TGM_CHANNEL_USERNAME: ChannelName = ""
    TGM_PL_CHANNEL_ID: ChannelId = ""
    TGM_PL_CHANNEL_USERNAME: ChannelName = ""

    VTT_LANGUAGE: VttLanguage = "en"
    VTT_IGNORE_ADS: bool = True

    NGINX_SERVER_NAME: str = ""
    NGINX_HTTPS_PORT: Numeric = "443"
    SSL_EMAIL: str = ""
