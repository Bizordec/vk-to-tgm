from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from loguru import logger
from telethon import Button, TelegramClient, events
from telethon.events import StopPropagation
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputMessagesFilterUrl
from vtt_common.schemas import VttTaskType
from vtt_common.tasks import get_queued_task

from app.config import _, settings
from app.state_manager import State, state_manager
from app.utils import NewMessageEvent, get_tgm_channel_entity, is_current_state, is_user_authorized
from app.worker import app as celery_app

if TYPE_CHECKING:
    from typing import Any

    from telethon.tl.patched import Message
    from telethon.tl.types.messages import ChannelMessages
    from vkbottle.api.api import API


WALL_SEARCHING = _("WALL_SEARCHING")
WALL_NOT_FOUND_IN_VK = _("WALL_NOT_FOUND_IN_VK")
WALL_ALREADY_IN_THE_QUEUE = _("WALL_ALREADY_IN_THE_QUEUE")
WALL_ALREADY_STARTED = _("WALL_ALREADY_STARTED")
WALL_FOUND_IN_TGM = _("WALL_FOUND_IN_TGM")
WALL_NOT_FOUND_IN_TGM = _("WALL_NOT_FOUND_IN_TGM")
WALL_ADDED_TO_THE_QUEUE = _("WALL_ADDED_TO_THE_QUEUE")
WALL_UNKNOWN_CHANNEL = _("WALL_UNKNOWN_CHANNEL")
WALL_YES = _("WALL_YES")
WALL_CANCEL = _("WALL_CANCEL")

POST_PATTERN = re.compile(r"(https:\/\/)?(www\.)?(m\.)?vk\.(ru|com)(\/?|\/\w+\?w=)wall(?P<owner_id>-\d+)_(?P<id>\d+)")


async def add_event_handlers(bot: TelegramClient, client: TelegramClient, vk_api: API) -> None:  # noqa: PLR0915
    @bot.on(events.CallbackQuery(data=b"wall_confirm", func=lambda e: is_current_state(e, State.WAITING_FOR_CHOISE)))  # type: ignore[untyped-decorator]
    async def new_wall(event: NewMessageEvent) -> None:
        await event.edit(buttons=Button.clear())
        if not await is_user_authorized(event):
            raise events.StopPropagation

        data = state_manager.get_info(event.sender_id)[1]
        logger.info("User {} confirmed wall post {}_{}", event.sender_id, data["owner_id"], data["id"])
        celery_app.send_task(
            "app.main.forward_wall",
            task_id=f"{VttTaskType.wall}_{data['owner_id']}_{data['id']}",
            queue="vtt-wall",
            kwargs={
                "owner_id": data["owner_id"],
                "wall_id": data["id"],
            },
        )
        await event.respond(WALL_ADDED_TO_THE_QUEUE)
        state_manager.clear_info(event.sender_id)
        raise StopPropagation

    @bot.on(events.NewMessage(pattern=POST_PATTERN, func=lambda e: is_current_state(e, State.WAITING_FOR_LINK)))  # type: ignore[untyped-decorator]
    async def on_new_wall(event: NewMessageEvent) -> None:
        if not await is_user_authorized(event):
            raise events.StopPropagation

        logger.info("User {} sent a wall link", event.sender_id)
        await event.respond(WALL_SEARCHING)
        sender = event.sender_id
        match_dict = event.pattern_match.groupdict()
        owner_id = int(match_dict["owner_id"])
        wall_id = int(match_dict["id"])

        full_id = f"{owner_id}_{wall_id}"

        logger.info("Parsed wall post: owner_id={}, id={}", owner_id, wall_id)

        vk_wall_result: list[dict[str, Any]] = (
            await vk_api.request(
                "wall.getById",
                {
                    "posts": full_id,
                },
            )
        )["response"]
        if not vk_wall_result:
            logger.warning("Wall post {}_{} not found in VK", owner_id, wall_id)
            await event.respond(WALL_NOT_FOUND_IN_VK)
            raise StopPropagation

        logger.debug("Wall post {}_{} confirmed in VK", owner_id, wall_id)

        queued_task = get_queued_task(
            backend=celery_app.backend,
            task_type=VttTaskType.wall,
            owner_id=owner_id,
            post_id=wall_id,
        )
        if queued_task and queued_task["status"] in {"SENT", "STARTED"}:
            logger.info("Wall post {}_{} already {} in queue", owner_id, wall_id, queued_task["status"])
            waiting_text = WALL_ALREADY_IN_THE_QUEUE if queued_task["status"] == "SENT" else WALL_ALREADY_STARTED
            message = await event.respond(
                waiting_text,
                buttons=[
                    Button.inline(WALL_YES, data=b"wall_confirm"),
                    Button.inline(WALL_CANCEL, data=b"cancel"),
                ],
            )
            state_manager.set_info(
                sender,
                State.WAITING_FOR_CHOISE,
                {
                    "choice_message": message.id,
                    "owner_id": owner_id,
                    "id": wall_id,
                },
            )
            raise StopPropagation

        logger.debug("Wall post {}_{} not in queue, checking Telegram channel", owner_id, wall_id)
        peer = await get_tgm_channel_entity(client, settings.TGM_CHANNEL_ID)
        if peer is None:
            logger.error("Could not resolve Telegram channel entity for TGM_CHANNEL_ID={}", settings.TGM_CHANNEL_ID)
            message = await event.respond(WALL_UNKNOWN_CHANNEL)
            state_manager.clear_info(event.sender_id)
            raise StopPropagation

        search_result: ChannelMessages = await client(
            SearchRequest(
                peer=peer,
                q=f"https://vk.ru/wall{full_id}",
                filter=InputMessagesFilterUrl(),
                min_date=None,
                max_date=None,
                offset_id=0,
                add_offset=0,
                limit=1,
                max_id=0,
                min_id=0,
                hash=0,
                from_id=None,
            ),
        )
        waiting_text = WALL_NOT_FOUND_IN_TGM
        if search_result.messages:
            waiting_text = WALL_FOUND_IN_TGM
            logger.info("Wall post {}_{} already exists in Telegram channel, forwarding to user", owner_id, wall_id)
            message = cast("Message", search_result.messages[0])
            await bot.forward_messages(sender, message.id, from_peer=message.chat_id)
        else:
            logger.info("Wall post {}_{} not found in Telegram channel", owner_id, wall_id)

        message = cast(
            "Message",
            await event.respond(
                waiting_text,
                buttons=[
                    Button.inline(WALL_YES, data=b"wall_confirm"),
                    Button.inline(WALL_CANCEL, data=b"cancel"),
                ],
            ),
        )
        logger.debug("Wall post {}_{} awaiting user confirmation (message_id={})", owner_id, wall_id, message.id)
        state_manager.set_info(
            sender,
            State.WAITING_FOR_CHOISE,
            {
                "choice_message": message.id,
                "owner_id": owner_id,
                "id": wall_id,
            },
        )
        raise StopPropagation
