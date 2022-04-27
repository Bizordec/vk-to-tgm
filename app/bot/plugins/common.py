import logging
from enum import Enum
from typing import Union

from telethon import events
from telethon.client.telegramclient import TelegramClient
from telethon.errors.rpcbaseerrors import RPCError
from telethon.tl.custom.button import Button
from vkbottle.api.api import API

from app.bot.state_manager import State, StateManager
from app.config import _, settings

logger = logging.getLogger(__name__)

HELLO = _("HELLO")
PERMISSION_CHECK_FAILED = _("PERMISSION_CHECK_FAILED")
NO_PERMISSION = _("NO_PERMISSION")
WAITING_FOR_LINK = _("WAITING_FOR_LINK")
CANCELLED = _("CANCELLED")
CLICK_BUTTON = _("CLICK_BUTTON")


# Somewhat fixed type for NewMessage event
NewMessageEvent = Union[events.NewMessage.Event, events.CallbackQuery.Event]

# The state in which different users are, {user_id: state}
conversation_state: "dict[int, Enum]" = {}

state_manager = StateManager()


def check_is_chat(event: NewMessageEvent):
    return event.is_private


async def check_state(event: NewMessageEvent, expected_state: State):
    if not check_is_chat(event):
        return False
    current_state = state_manager.get_info(event.sender_id)[0]
    return current_state == expected_state


async def check_permission(event: NewMessageEvent):
    sender = event.sender_id
    client: TelegramClient = event.client
    try:
        perm = await client.get_permissions(settings.TGM_CHANNEL_ID, sender)
    except RPCError as error:
        logger.warning(f"Failed to check permissions: {error.message}")
        await event.respond(PERMISSION_CHECK_FAILED, buttons=Button.clear())
        return False
    if perm and perm.post_messages:
        return True
    await event.respond(NO_PERMISSION, buttons=Button.clear())
    return False


async def init(bot: TelegramClient, client: TelegramClient, vk_api: API):
    @bot.on(events.NewMessage(pattern="/start", func=check_is_chat))
    async def start(event: NewMessageEvent):
        await event.respond(HELLO)
        if not await check_permission(event):
            raise events.StopPropagation
        state_manager.set_info(event.sender_id, State.WAITING_FOR_LINK)
        await event.respond(WAITING_FOR_LINK)
        raise events.StopPropagation

    @bot.on(events.NewMessage(pattern="/cancel"))
    async def cancel(event: events.CallbackQuery.Event):
        state_manager.set_info(event.sender_id, State.WAITING_FOR_LINK)
        await event.edit(buttons=Button.clear())
        await event.respond(CANCELLED)
        raise events.StopPropagation

    @bot.on(events.CallbackQuery(data=b"cancel"))
    async def btn_cancel(event: events.CallbackQuery.Event):
        state_manager.set_info(event.sender_id, State.WAITING_FOR_LINK)
        await event.edit(buttons=Button.clear())
        await event.respond(CANCELLED)
        raise events.StopPropagation

    @bot.on(events.NewMessage(func=lambda e: check_state(e, State.WAITING_FOR_CHOISE)))
    async def waiting_for_choice(event: NewMessageEvent):
        if not await check_permission(event):
            raise events.StopPropagation

        data = state_manager.get_info(event.sender_id)[1]
        await event.respond(CLICK_BUTTON, reply_to=data["choice_message"])
        raise events.StopPropagation
