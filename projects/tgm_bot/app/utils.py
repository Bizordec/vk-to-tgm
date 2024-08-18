from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias, cast

from loguru import logger
from telethon import events
from telethon.client.telegramclient import TelegramClient
from telethon.errors.rpcbaseerrors import RPCError
from telethon.tl.custom.button import Button

from app.config import _, settings
from app.state_manager import State, state_manager

if TYPE_CHECKING:
    from telethon.tl.types import TypeInputPeer

# Somewhat fixed type for NewMessage event
NewMessageEvent: TypeAlias = events.NewMessage.Event | events.CallbackQuery.Event


NO_PERMISSION = _("NO_PERMISSION")

PERMISSION_CHECK_FAILED = _("PERMISSION_CHECK_FAILED")


def check_is_chat(event: NewMessageEvent) -> bool | None:
    return event.is_private


async def is_current_state(event: NewMessageEvent, expected_state: State) -> bool:
    if not check_is_chat(event):
        return False

    current_state = state_manager.get_info(event.sender_id)[0]
    return current_state == expected_state


async def is_user_authorized(event: NewMessageEvent) -> bool:
    sender = event.sender_id
    client = cast(TelegramClient, event.client)
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


async def get_tgm_channel_entity(
    client: TelegramClient,
    channel_id: int,
) -> TypeInputPeer | None:
    entity = None
    try:
        entity = await client.get_input_entity(channel_id)
    except ValueError:
        logger.critical("Failed to get entity! Add bot to your channel as an admin and try again.")

    return entity
