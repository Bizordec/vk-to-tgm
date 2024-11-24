from __future__ import annotations

import re
from functools import partial
from typing import TYPE_CHECKING, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings

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


def check_env(value: str, pattern: Pattern[str]) -> str:
    if value and not pattern.match(value):
        raise NotMatchedPatternError(pattern)
    return value


class Settings(BaseSettings):
    VK_KATE_TOKEN: str = ""
    VK_OFFICIAL_TOKEN: str = ""

    VK_COMMUNITY_ID: str = ""
    VK_COMMUNITY_TOKEN: str = ""

    VK_SERVER_TITLE: str = "vk-to-tgm"
    SERVER_URL: str = ""

    TGM_API_ID: str = ""
    TGM_API_HASH: str = ""

    TGM_BOT_TOKEN: str = ""
    TGM_BOT_SESSION: str = ""

    TGM_CLIENT_PHONE: str = ""
    TGM_CLIENT_SESSION: str = ""

    TGM_CHANNEL_ID: str = ""
    TGM_CHANNEL_USERNAME: str = ""
    TGM_PL_CHANNEL_ID: str = ""
    TGM_PL_CHANNEL_USERNAME: str = ""

    VTT_LANGUAGE: VttLanguage = "en"
    VTT_IGNORE_ADS: bool = True

    _check_server_url = field_validator("SERVER_URL")(
        partial(check_env, pattern=SERVER_URL_PATTERN),
    )

    _check_digits = field_validator(
        "VK_COMMUNITY_ID",
        "TGM_API_ID",
        "TGM_CLIENT_PHONE",
    )(partial(check_env, pattern=DIGITS_PATTERN))

    _check_tgm_bot_token = field_validator("TGM_BOT_TOKEN")(
        partial(check_env, pattern=TGM_BOT_TOKEN_PATTERN),
    )

    _check_tgm_channel_name = field_validator("TGM_CHANNEL_USERNAME", "TGM_PL_CHANNEL_USERNAME")(
        partial(check_env, pattern=TGM_CHANNEL_USERNAME_PATTERN),
    )

    _check_tgm_id = field_validator("TGM_CHANNEL_ID", "TGM_PL_CHANNEL_ID")(
        partial(check_env, pattern=TGM_CHANNEL_ID_PATTERN),
    )
