from __future__ import annotations

import asyncio
import re
from functools import partial
from typing import TYPE_CHECKING, Any, Literal

from aiohttp import ClientSession
from pydantic import BaseSettings, Field, root_validator, validator
from telethon import TelegramClient
from telethon.sessions import StringSession
from vkbottle import API, AiohttpClient, VKAPIError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from re import Pattern


DIGITS_PATTERN = re.compile(r"^[0-9]+$")
SERVER_URL_PATTERN = re.compile(r"^https?://.+$")
TGM_CHANNEL_ID_PATTERN = re.compile(r"^-100[0-9]+$")
TGM_BOT_TOKEN_PATTERN = re.compile(r"^.+:.+$")

TOKENS_UA = {
    "VK_KATE_TOKEN": "KateMobileAndroid/56 lite-460 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en)",
    "VK_OFFICIAL_TOKEN": "VKAndroidApp/5.52-4543 (Android 5.1.1; SDK 22; x86_64; unknown Android SDK built for x86_64; en; 320x240)",
}

VttLanguage = Literal["en", "ru"]


class NotMatchedPatternError(ValueError):
    def __init__(self, pattern: Pattern[str]) -> None:
        super().__init__(f"Value does not match pattern '{pattern.pattern}'")


def check_env(value: str | int | None, pattern: Pattern[str]) -> str | int | None:
    if value is not None and not pattern.match(str(value)):
        raise NotMatchedPatternError(pattern)
    return value


class Settings(BaseSettings):
    VK_KATE_TOKEN: str
    VK_OFFICIAL_TOKEN: str

    VK_COMMUNITY_ID: int
    VK_COMMUNITY_TOKEN: str

    VK_SERVER_TITLE: str = Field(default="vk-to-tgm", min_length=1, max_length=14)
    SERVER_URL: str

    TGM_API_ID: int
    TGM_API_HASH: str

    TGM_BOT_TOKEN: str
    TGM_BOT_SESSION: str

    TGM_CLIENT_PHONE: str
    TGM_CLIENT_SESSION: str

    TGM_CHANNEL_ID: int
    TGM_PL_CHANNEL_ID: int | None = None

    VTT_LANGUAGE: VttLanguage = "en"
    VTT_IGNORE_ADS: bool = True

    _check_server_url = validator("SERVER_URL", allow_reuse=True)(
        partial(check_env, pattern=SERVER_URL_PATTERN),
    )

    _check_digits = validator(
        "TGM_CLIENT_PHONE",
        allow_reuse=True,
    )(partial(check_env, pattern=DIGITS_PATTERN))

    _check_tgm_bot_token = validator("TGM_BOT_TOKEN", allow_reuse=True)(
        partial(check_env, pattern=TGM_BOT_TOKEN_PATTERN),
    )

    _check_tgm_id = validator("TGM_CHANNEL_ID", "TGM_PL_CHANNEL_ID", allow_reuse=True)(
        partial(check_env, pattern=TGM_CHANNEL_ID_PATTERN),
    )

    @staticmethod
    async def _async_check_vk_user_tokens(values: dict) -> None:
        for token_name, user_agent in TOKENS_UA.items():
            vk_api = API(
                token=values[token_name],
                http_client=AiohttpClient(
                    session=ClientSession(headers={"User-agent": user_agent}),
                ),
            )
            try:
                await vk_api.request("audio.get", data={})
            except VKAPIError as error:
                raise ValueError(f"[{token_name}] {error.description}") from error

    @staticmethod
    async def _async_check_vk_community_token(values: dict) -> None:
        token = values["VK_COMMUNITY_TOKEN"]

        vk_api = API(token=token, http_client=AiohttpClient())
        try:
            token_permissions = await vk_api.groups.get_token_permissions()
            await vk_api.groups.get_callback_servers(group_id=values["VK_COMMUNITY_ID"])
        except VKAPIError as error:
            error_msg = error.description
            raise ValueError(
                f"Could not verify VK community token: {error_msg}",
            ) from error

        if not token_permissions.mask & 262144:
            raise ValueError("VK community token does not have 'manage' permission")

    @staticmethod
    async def _async_check_tgm_bot(values: dict) -> None:
        client = TelegramClient(
            StringSession(string=values["TGM_BOT_SESSION"]),
            values["TGM_API_ID"],
            values["TGM_API_HASH"],
        )
        async with await client.start(bot_token=values["TGM_BOT_TOKEN"]):
            for channel_id_key in ("TGM_CHANNEL_ID", "TGM_PL_CHANNEL_ID"):
                channel_id: int = values[channel_id_key]
                if channel_id_key == "TGM_PL_CHANNEL_ID" and channel_id is not None:
                    continue

                try:
                    await client.get_input_entity(channel_id)
                except ValueError:
                    raise ValueError(
                        f"[{channel_id_key}] Telegram channel is invalid. "
                        "If your channel is private, make sure to add your bot as an admin.",
                    ) from None

                permissions = await client.get_permissions(
                    channel_id,
                    user=await client.get_me(input_peer=True),
                )
                str_permissions = []
                if not permissions.post_messages:
                    str_permissions.append("post")
                if not permissions.edit_messages:
                    str_permissions.append("edit")
                if str_permissions:
                    raise ValueError(
                        f"[{channel_id_key}] Bot doesn't have permissions to {' and '.join(str_permissions)} messages.",
                    )

    @staticmethod
    async def _async_check_tgm_user(values: dict) -> None:
        client = TelegramClient(
            StringSession(string=values["TGM_CLIENT_SESSION"]),
            values["TGM_API_ID"],
            values["TGM_API_HASH"],
        )
        async with await client.start(phone=lambda: values["TGM_CLIENT_PHONE"]):
            for channel_id_key in ("TGM_CHANNEL_ID", "TGM_PL_CHANNEL_ID"):
                channel_id = values[channel_id_key]
                if channel_id_key == "TGM_PL_CHANNEL_ID" and channel_id is not None:
                    continue

                try:
                    await client.get_input_entity(channel_id)
                except ValueError:
                    raise ValueError(
                        f"[{channel_id_key}] Telegram channel is invalid. "
                        "If your channel is private, make sure to add your user as an admin.",
                    ) from None

    @classmethod
    def _check_async(
        cls,
        check_func: Callable[[dict], Coroutine[Any, Any, None]],
        values: dict,
    ) -> dict:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(check_func(values))
        else:
            loop.run_until_complete(check_func(values))
        return values

    @root_validator()
    @classmethod
    def check_vk_user_tokens(cls, values: dict) -> dict:
        return cls._check_async(cls._async_check_vk_user_tokens, values)

    @root_validator()
    @classmethod
    def check_vk_community_token(cls, values: dict) -> dict:
        return cls._check_async(cls._async_check_vk_community_token, values)

    @root_validator()
    @classmethod
    def check_tgm_bot(cls, values: dict) -> dict:
        return cls._check_async(cls._async_check_tgm_bot, values)

    @root_validator()
    @classmethod
    def check_tgm_user(cls, values: dict) -> dict:
        return cls._check_async(cls._async_check_tgm_user, values)

    class Config:
        env_file = ".env"
