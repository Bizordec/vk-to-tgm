import logging
import re
from typing import TYPE_CHECKING, cast

from telethon import Button, TelegramClient, events
from telethon.events import StopPropagation
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.patched import Message
from telethon.tl.types import InputMessagesFilterUrl
from vkbottle.api.api import API
from vtt_common.schemas import VttTaskType
from vtt_common.tasks import get_queued_task

from app.config import _, settings
from app.plugins.common import is_current_state, is_user_authorized, state_manager
from app.state_manager import State
from app.utils import NewMessageEvent, get_tgm_channel_entity
from app.worker import app as celery_app

if TYPE_CHECKING:
    from telethon.tl.types.messages import ChannelMessages


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

POST_PATTERN = re.compile(r"(https:\/\/)?(www\.)?(m\.)?vk\.com(\/?|\/\w+\?w=)wall(?P<owner_id>-\d+)_(?P<id>\d+)")


async def add_event_handlers(bot: TelegramClient, client: TelegramClient, vk_api: API) -> None:
    @bot.on(events.CallbackQuery(data=b"wall_confirm", func=lambda e: is_current_state(e, State.WAITING_FOR_CHOISE)))
    async def new_wall(event: NewMessageEvent) -> None:
        await event.edit(buttons=Button.clear())
        if not await is_user_authorized(event):
            raise events.StopPropagation

        data = state_manager.get_info(event.sender_id)[1]
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

    @bot.on(events.NewMessage(pattern=POST_PATTERN, func=lambda e: is_current_state(e, State.WAITING_FOR_LINK)))
    async def on_new_wall(event: NewMessageEvent) -> None:
        if not await is_user_authorized(event):
            raise events.StopPropagation

        await event.respond(WALL_SEARCHING)
        sender = event.sender_id
        match_dict = event.pattern_match.groupdict()
        owner_id = int(match_dict["owner_id"])
        wall_id = int(match_dict["id"])

        full_id = f"{owner_id}_{wall_id}"

        vk_wall_result: list[dict] = (
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

        queued_task = get_queued_task(
            app=celery_app,
            task_type=VttTaskType.wall,
            owner_id=owner_id,
            post_id=wall_id,
        )
        if queued_task and queued_task["status"] in {"SENT", "STARTED"}:
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

        peer = await get_tgm_channel_entity(client, settings.TGM_CHANNEL_ID)
        if peer is None:
            message = await event.respond(WALL_UNKNOWN_CHANNEL)
            state_manager.clear_info(event.sender_id)
            raise StopPropagation

        search_result: ChannelMessages = await client(
            SearchRequest(
                peer=peer,
                q=f"https://vk.com/wall{full_id}",
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
            message = cast(Message, search_result.messages[0])
            await bot.forward_messages(sender, message.id, from_peer=message.chat_id)

        message = cast(
            Message,
            await event.respond(
                waiting_text,
                buttons=[
                    Button.inline(WALL_YES, data=b"wall_confirm"),
                    Button.inline(WALL_CANCEL, data=b"cancel"),
                ],
            ),
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
