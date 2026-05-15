from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from telethon import events
from telethon.tl.custom.button import Button

from app.config import _, settings
from app.state_manager import State, state_manager
from app.utils import is_current_state, is_user_authorized

if TYPE_CHECKING:
    from telethon.client.telegramclient import TelegramClient
    from telethon.events.common import EventCommon

HELLO = _("HELLO")
PERMISSION_CHECK_FAILED = _("PERMISSION_CHECK_FAILED")
NO_PERMISSION = _("NO_PERMISSION")
WAITING_FOR_LINK = _("WAITING_FOR_LINK")
CANCELLED = _("CANCELLED")
CLICK_BUTTON = _("CLICK_BUTTON")
INCORRECT_LINK = (
    _("INCORRECT_LINK")
    + (
        ":\n"
        "\nvk.ru/wall{owner_id}_{id}"
        "\nm.vk.ru/wall{owner_id}_{id}"
        "\nhttps://vk.ru/wall{owner_id}_{id}"
        "\nhttps://m.vk.ru/wall{owner_id}_{id}"
    )
    + (
        "\nvk.ru/music/album/{owner_id}_{id}"
        "\nvk.ru/music/playlist/{owner_id}_{id}"
        "\nm.vk.ru/audio?act=audio_playlist{owner_id}_{id}"
        "\nhttps://vk.ru/music/album/{owner_id}_{id}"
        "\nhttps://vk.ru/music/playlist/{owner_id}_{id}"
        "\nhttps://m.vk.ru/audio?act=audio_playlist{owner_id}_{id}"
    )
    if settings.TGM_PL_CHANNEL_ID
    else ""
)


# Somewhat fixed type for NewMessage event
type Event = events.NewMessage.Event | events.CallbackQuery.Event


def is_user_chat(event: EventCommon) -> bool:
    return event.is_private or False


async def add_initial_event_handlers(bot: TelegramClient) -> None:
    @bot.on(events.NewMessage(pattern="/start", func=is_user_chat))  # type: ignore[untyped-decorator]
    async def start(event: Event) -> None:
        logger.info("User {} ran /start", event.sender_id)
        await event.respond(HELLO)
        if not await is_user_authorized(event):
            logger.warning("User {} not authorized, stopping propagation", event.sender_id)
            raise events.StopPropagation

        state_manager.set_info(event.sender_id, State.WAITING_FOR_LINK)
        await event.respond(WAITING_FOR_LINK)
        raise events.StopPropagation

    @bot.on(events.NewMessage(pattern="/cancel"))  # type: ignore[untyped-decorator]
    async def cancel(event: Event) -> None:
        logger.info("User {} cancelled via /cancel", event.sender_id)
        state_manager.set_info(event.sender_id, State.WAITING_FOR_LINK)
        await event.edit(buttons=Button.clear())
        await event.respond(CANCELLED)
        raise events.StopPropagation

    @bot.on(events.CallbackQuery(data=b"cancel"))  # type: ignore[untyped-decorator]
    async def btn_cancel(event: events.CallbackQuery.Event) -> None:
        logger.info("User {} cancelled via button", event.sender_id)
        state_manager.set_info(event.sender_id, State.WAITING_FOR_LINK)
        await event.edit(buttons=Button.clear())
        await event.respond(CANCELLED)
        raise events.StopPropagation

    @bot.on(events.NewMessage(func=lambda e: is_current_state(e, State.WAITING_FOR_CHOISE)))  # type: ignore[untyped-decorator]
    async def waiting_for_choice(event: Event) -> None:
        logger.warning("User {} sent a message while in CHOISE state (expected button click)", event.sender_id)
        if not await is_user_authorized(event):
            logger.warning("User {} not authorized in CHOISE handler, stopping propagation", event.sender_id)
            raise events.StopPropagation

        data = state_manager.get_info(event.sender_id)[1]
        await event.respond(CLICK_BUTTON, reply_to=data["choice_message"])
        raise events.StopPropagation


async def add_last_event_handlers(bot: TelegramClient) -> None:
    @bot.on(events.NewMessage(func=lambda e: is_current_state(e, State.WAITING_FOR_LINK)))  # type: ignore[untyped-decorator]
    async def incorrect_link(event: Event) -> None:
        if not await is_user_authorized(event):
            logger.warning("User {} not authorized for incorrect_link handler", event.sender_id)
            raise events.StopPropagation

        logger.warning("User {} sent an incorrect link: {}", event.sender_id, event.message.message)
        await event.respond(INCORRECT_LINK)
        raise events.StopPropagation
