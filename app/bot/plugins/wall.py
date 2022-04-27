import logging
import re
from typing import List, Union

from telethon import Button, TelegramClient, events
from telethon.events import StopPropagation
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.patched import Message
from telethon.tl.types import InputMessagesFilterUrl
from telethon.tl.types.messages import ChannelMessages
from vkbottle.api.api import API

from app.bot.plugins.common import check_permission, check_state, state_manager
from app.bot.state_manager import State
from app.celery_worker import forward_wall
from app.config import _, settings
from app.utils.database import VttTaskType, get_queued_task
from app.utils.telegram import get_entity_by_id

logger = logging.getLogger(__name__)

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

post_pattern = re.compile(r"(https:\/\/)?(www\.)?(m\.)?vk\.com(\/?|\/\w+\?w=)wall(?P<owner_id>-\d+)_(?P<id>\d+)")

# Somewhat fixed type for NewMessage event
NewMessageEvent = Union[events.NewMessage.Event, events.CallbackQuery.Event]


async def init(bot: TelegramClient, client: TelegramClient, vk_api: API):
    @bot.on(events.CallbackQuery(data=b"wall_confirm", func=lambda e: check_state(e, State.WAITING_FOR_CHOISE)))
    async def new_wall(event: NewMessageEvent):
        await event.edit(buttons=Button.clear())
        if not await check_permission(event):
            raise events.StopPropagation

        data = state_manager.get_info(event.sender_id)[1]
        forward_wall.delay(
            owner_id=data["owner_id"],
            wall_id=data["id"],
        )
        await event.respond(WALL_ADDED_TO_THE_QUEUE)
        state_manager.clear_info(event.sender_id)
        raise StopPropagation

    @bot.on(events.NewMessage(pattern=post_pattern, func=lambda e: check_state(e, State.WAITING_FOR_LINK)))
    async def on_new_wall(event: NewMessageEvent):
        if not await check_permission(event):
            raise events.StopPropagation

        await event.respond(WALL_SEARCHING)
        sender = event.sender_id
        match_dict = event.pattern_match.groupdict()
        owner_id = int(match_dict["owner_id"])
        id = int(match_dict["id"])

        full_id = f"{owner_id}_{id}"

        vk_wall_result: List[dict] = (
            await vk_api.request(
                "wall.getById",
                {
                    "posts": full_id,
                },
            )
        )["response"]
        if not vk_wall_result:
            await event.respond(WALL_NOT_FOUND_IN_VK)
            raise StopPropagation

        queued_task = get_queued_task(owner_id, id, VttTaskType.wall)
        if queued_task:
            if queued_task.status == "SENT":
                waiting_text = WALL_ALREADY_IN_THE_QUEUE
            else:
                waiting_text = WALL_ALREADY_STARTED
            message = await event.respond(
                waiting_text,
                buttons=[
                    Button.inline(WALL_YES, data="wall_confirm"),
                    Button.inline(WALL_CANCEL, data=b"cancel"),
                ],
            )
            state_manager.set_info(
                sender,
                State.WAITING_FOR_CHOISE,
                {
                    "choice_message": message.id,
                    "owner_id": owner_id,
                    "id": id,
                },
            )
            raise StopPropagation

        peer = await get_entity_by_id(client, settings.TGM_CHANNEL_ID)
        if peer is None:
            message = await event.respond(WALL_UNKNOWN_CHANNEL)
            state_manager.clear_info(event.sender_id)
            raise StopPropagation

        filter = InputMessagesFilterUrl()
        search_result: ChannelMessages = await client(
            SearchRequest(
                peer=peer,
                q=f"https://vk.com/wall{full_id}",
                filter=filter,
                min_date=None,
                max_date=None,
                offset_id=0,
                add_offset=0,
                limit=1,
                max_id=0,
                min_id=0,
                hash=0,
                from_id=None,
            )
        )
        waiting_text = WALL_NOT_FOUND_IN_TGM
        if search_result.messages:
            waiting_text = WALL_FOUND_IN_TGM
            message: Message = search_result.messages[0]
            await bot.forward_messages(sender, message.id, from_peer=message.chat_id)
        message = await event.respond(
            waiting_text,
            buttons=[
                Button.inline(WALL_YES, data="wall_confirm"),
                Button.inline(WALL_CANCEL, data=b"cancel"),
            ],
        )
        state_manager.set_info(
            sender,
            State.WAITING_FOR_CHOISE,
            {
                "choice_message": message.id,
                "owner_id": owner_id,
                "id": id,
            },
        )
        raise StopPropagation
