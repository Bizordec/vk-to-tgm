from __future__ import annotations

import re
from functools import partial
from typing import TYPE_CHECKING, Annotated, Literal

from aiohttp import ClientSession
from pydantic import AfterValidator, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from telethon import TelegramClient
from telethon.sessions import StringSession
from vkbottle import API, AiohttpClient, VKAPIError
from vkbottle_types.codegen.methods.groups import GroupsCategory

from app.syncify import async_to_sync

if TYPE_CHECKING:
    from re import Pattern
    from typing import Self


SERVER_URL_PATTERN = re.compile(r"^https?://.+$")
TGM_CHANNEL_USERNAME_PATTERN = re.compile(r"^[a-zA-Z][\w\d]{3,30}[a-zA-Z\d]$")
TGM_CHANNEL_ID_PATTERN = re.compile(r"^-100[0-9]+$")
TGM_BOT_TOKEN_PATTERN = re.compile(r"^.+:.+$")

KATE_USER_AGENT = "KateMobileAndroid/56 lite-460 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en)"


VttLanguage = Literal["en", "ru"]


class NotMatchedPatternError(ValueError):
    def __init__(self, pattern: Pattern[str]) -> None:
        super().__init__(f"Value does not match pattern '{pattern.pattern}'")


def _check_env(value: str | int | None, pattern: Pattern[str]) -> str | int | None:
    if value is not None and not pattern.match(str(value)):
        raise NotMatchedPatternError(pattern)
    return value


def pattern_validator(pattern: Pattern[str]) -> AfterValidator:
    return AfterValidator(partial(_check_env, pattern=pattern))


ChannelId = Annotated[str, pattern_validator(TGM_CHANNEL_ID_PATTERN)]
ChannelName = Annotated[str, pattern_validator(TGM_CHANNEL_USERNAME_PATTERN)]


@async_to_sync
async def check_vk_kate_token(value: str) -> str:
    vk_api = API(
        token=value,
        http_client=AiohttpClient(
            session=ClientSession(headers={"User-agent": KATE_USER_AGENT}),
        ),
    )
    try:
        await vk_api.request("audio.get", data={})
    except VKAPIError as error:
        raise ValueError(f"[{value}] {error.error_msg}") from error

    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    VK_KATE_TOKEN: Annotated[str, AfterValidator(check_vk_kate_token)]

    VK_COMMUNITY_ID: int
    VK_COMMUNITY_TOKEN: str

    VK_SERVER_TITLE: str = Field(default="vk-to-tgm", min_length=1, max_length=14)

    SERVER_URL: Annotated[str, pattern_validator(SERVER_URL_PATTERN)]

    TGM_API_ID: int
    TGM_API_HASH: str

    TGM_BOT_TOKEN: Annotated[str, pattern_validator(TGM_BOT_TOKEN_PATTERN)]
    TGM_BOT_SESSION: str

    TGM_CLIENT_PHONE: str
    TGM_CLIENT_SESSION: str

    TGM_CHANNEL_ID: Annotated[int, pattern_validator(TGM_CHANNEL_ID_PATTERN)]
    TGM_PL_CHANNEL_ID: Annotated[int | None, pattern_validator(TGM_CHANNEL_ID_PATTERN)] = None

    VTT_LANGUAGE: VttLanguage = "en"
    VTT_IGNORE_ADS: bool = True

    @model_validator(mode="after")
    @async_to_sync
    async def check_vk_community(self) -> Self:
        vk_groups = GroupsCategory(API(token=self.VK_COMMUNITY_TOKEN, http_client=AiohttpClient()))
        try:
            token_permissions = await vk_groups.get_token_permissions()
            await vk_groups.get_callback_servers(group_id=self.VK_COMMUNITY_ID)
        except VKAPIError as error:
            error_msg = error.error_msg
            raise ValueError(
                f"Could not verify VK community token: {error_msg}",
            ) from error

        if not token_permissions.mask & 262144:
            raise ValueError("VK community token does not have 'manage' permission")

        return self

    @model_validator(mode="after")
    @async_to_sync
    async def check_tgm_bot(self) -> Self:
        client = TelegramClient(
            StringSession(string=self.TGM_BOT_SESSION),
            self.TGM_API_ID,
            self.TGM_API_HASH,
        )
        values = self.model_dump()
        async with await client.start(bot_token=self.TGM_BOT_TOKEN):
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

        return self

    @model_validator(mode="after")
    @async_to_sync
    async def check_tgm_user(self) -> Self:
        client = TelegramClient(
            StringSession(string=self.TGM_CLIENT_SESSION),
            self.TGM_API_ID,
            self.TGM_API_HASH,
        )
        values = self.model_dump()
        async with await client.start(phone=lambda: self.TGM_CLIENT_PHONE):
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

        return self
