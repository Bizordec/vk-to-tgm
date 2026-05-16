from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import questionary
from telethon.types import Channel as TelethonChannel
from telethon.types import InputPeerChannel

from app.config import TGM_CHANNEL_ID_PATTERN, TGM_CHANNEL_USERNAME_PATTERN
from app.console import console
from app.prompt import EnvTextPrompt

if TYPE_CHECKING:
    from telethon import TelegramClient


class Channel(ABC):
    def __init__(
        self,
        client: TelegramClient,
        name: str,
        channel_id: str,
    ) -> None:
        self._client = client
        self._name = name
        self._channel_id = channel_id

    @property
    @abstractmethod
    def channel_type(self) -> str: ...

    @abstractmethod
    async def prompt_name(self) -> str: ...

    @abstractmethod
    async def prompt_id(self) -> str: ...

    @property
    def name(self) -> str:
        return self._name

    @property
    def channel_id(self) -> str:
        return self._channel_id

    async def prompt_is_public(self) -> bool:
        return bool(
            await questionary.confirm(f"Is your {self.channel_type} Telegram channel public?").unsafe_ask_async(),
        )

    async def is_channel_valid(self, entity: str | int) -> bool:
        invalid_msg = (
            f"[prompt.invalid]{self.channel_type} Telegram channel is invalid. "
            "If your channel is private, make sure to add your bot as an admin."
        )

        console.print(f"Checking if {self.channel_type} Telegram channel is valid...")

        try:
            channel_entity = await self._client.get_input_entity(peer=entity)
        except ValueError:
            console.print(invalid_msg)
            return False

        console.print(f"{self.channel_type} Telegram channel is valid.")

        match channel_entity:
            case InputPeerChannel() as channel:
                self._channel_id = f"-100{channel.channel_id}"
            case TelethonChannel() as channel:
                self._channel_id = f"-100{channel.id}"
            case _:
                console.print(invalid_msg)
                return False

        return True

    async def prompt_all(self) -> None:
        is_public = await self.prompt_is_public()
        while True:
            if is_public:
                self._name = await self.prompt_name()
            else:
                self._channel_id = await self.prompt_id()

            if await self.is_channel_valid(
                entity=self._name if is_public else int(self._channel_id),
            ):
                break

            self._name = ""
            self._channel_id = ""


class MainChannel(Channel):
    @property
    def channel_type(self) -> str:
        return "Main"

    async def prompt_name(self) -> str:
        return await EnvTextPrompt.ask(
            name="TGM_CHANNEL_USERNAME",
            default=self._name,
            description="Main Telegram channel name.",
            pattern=TGM_CHANNEL_USERNAME_PATTERN,
        )

    async def prompt_id(self) -> str:
        return await EnvTextPrompt.ask(
            name="TGM_CHANNEL_ID",
            default=self._channel_id,
            description="""
            Main Telegram channel ID.
            It can be obtained, for example, by sending a message to this bot: https://t.me/username_to_id_bot
            """,
            pattern=TGM_CHANNEL_ID_PATTERN,
        )


class PlaylistChannel(Channel):
    @property
    def channel_type(self) -> str:
        return "Playlist"

    async def prompt_name(self) -> str:
        return await EnvTextPrompt.ask(
            name="TGM_PL_CHANNEL_USERNAME",
            default=self._name,
            description="Playlist Telegram channel name.",
            pattern=TGM_CHANNEL_USERNAME_PATTERN,
        )

    async def prompt_id(self) -> str:
        return await EnvTextPrompt.ask(
            name="TGM_PL_CHANNEL_ID",
            default=self._channel_id,
            description="""
            Playlist Telegram channel ID.
            You cant get it, for example, by sending message to this bot: https://t.me/username_to_id_bot
            """,
            pattern=TGM_CHANNEL_ID_PATTERN,
        )
