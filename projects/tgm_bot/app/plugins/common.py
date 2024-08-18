from typing import TypeAlias

from telethon import events
from telethon.client.telegramclient import TelegramClient
from telethon.events.common import EventCommon
from telethon.tl.custom.button import Button

from app.config import _, settings
from app.state_manager import State, state_manager
from app.utils import is_current_state, is_user_authorized

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
        "\nvk.com/wall{owner_id}_{id}"
        "\nm.vk.com/wall{owner_id}_{id}"
        "\nhttps://vk.com/wall{owner_id}_{id}"
        "\nhttps://m.vk.com/wall{owner_id}_{id}"
    )
    + (
        "\nvk.com/music/album/{owner_id}_{id}"
        "\nvk.com/music/playlist/{owner_id}_{id}"
        "\nm.vk.com/audio?act=audio_playlist{owner_id}_{id}"
        "\nhttps://vk.com/music/album/{owner_id}_{id}"
        "\nhttps://vk.com/music/playlist/{owner_id}_{id}"
        "\nhttps://m.vk.com/audio?act=audio_playlist{owner_id}_{id}"
    )
    if settings.TGM_PL_CHANNEL_ID
    else ""
)


# Somewhat fixed type for NewMessage event
Event: TypeAlias = events.NewMessage.Event | events.CallbackQuery.Event


def is_user_chat(event: EventCommon) -> bool:
    return event.is_private or False


async def add_initial_event_handlers(bot: TelegramClient) -> None:
    @bot.on(events.NewMessage(pattern="/start", func=is_user_chat))
    async def start(event: Event) -> None:
        await event.respond(HELLO)
        if not await is_user_authorized(event):
            raise events.StopPropagation

        state_manager.set_info(event.sender_id, State.WAITING_FOR_LINK)
        await event.respond(WAITING_FOR_LINK)
        raise events.StopPropagation

    @bot.on(events.NewMessage(pattern="/cancel"))
    async def cancel(event: Event) -> None:
        state_manager.set_info(event.sender_id, State.WAITING_FOR_LINK)
        await event.edit(buttons=Button.clear())
        await event.respond(CANCELLED)
        raise events.StopPropagation

    @bot.on(events.CallbackQuery(data=b"cancel"))
    async def btn_cancel(event: events.CallbackQuery.Event) -> None:
        state_manager.set_info(event.sender_id, State.WAITING_FOR_LINK)
        await event.edit(buttons=Button.clear())
        await event.respond(CANCELLED)
        raise events.StopPropagation

    @bot.on(events.NewMessage(func=lambda e: is_current_state(e, State.WAITING_FOR_CHOISE)))
    async def waiting_for_choice(event: Event) -> None:
        if not await is_user_authorized(event):
            raise events.StopPropagation

        data = state_manager.get_info(event.sender_id)[1]
        await event.respond(CLICK_BUTTON, reply_to=data["choice_message"])
        raise events.StopPropagation


async def add_last_event_handlers(bot: TelegramClient) -> None:
    @bot.on(events.NewMessage(func=lambda e: is_current_state(e, State.WAITING_FOR_LINK)))
    async def incorrect_link(event: Event) -> None:
        if not await is_user_authorized(event):
            raise events.StopPropagation

        await event.respond(INCORRECT_LINK)
        raise events.StopPropagation
