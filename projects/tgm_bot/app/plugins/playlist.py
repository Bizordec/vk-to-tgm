import re
from typing import TYPE_CHECKING, cast
from urllib.parse import parse_qs, urlparse

from telethon import events
from telethon.client.telegramclient import TelegramClient
from telethon.events import StopPropagation
from telethon.tl.custom.button import Button
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
from app.vk.api import is_playlist_exists
from app.worker import app as celery_app

if TYPE_CHECKING:
    from telethon.tl.types.messages import ChannelMessages

PL_NOT_READY = _("PL_NOT_READY")
PL_SEARCHING = _("PL_SEARCHING")
PL_NOT_FOUND_IN_VK = _("PL_NOT_FOUND_IN_VK")
PL_ALREADY_IN_THE_QUEUE = _("PL_ALREADY_IN_THE_QUEUE")
PL_ALREADY_STARTED = _("PL_ALREADY_STARTED")
PL_FOUND_IN_TGM = _("PL_FOUND_IN_TGM")
PL_NOT_FOUND_IN_TGM = _("PL_NOT_FOUND_IN_TGM")
PL_ADDED_TO_THE_QUEUE = _("PL_ADDED_TO_THE_QUEUE")
PL_UNKNOWN_CHANNEL = _("PL_UNKNOWN_CHANNEL")
PL_YES = _("PL_YES")
PL_CANCEL = _("PL_CANCEL")

pl_link_pattern = re.compile(
    r"(https:\/\/)?(www\.)?(m\.)?vk\.com\/(music(/(playlist|album)|/?\?.+audio_playlist)|\w+/?\?.+audio_playlist)",
)

playlist_full_id = re.compile(r"(?P<owner_id>-?\d+)_(?P<playlist_id>\d+)((_|\/)(?P<access_key>[a-z0-9]+))?")


def _get_playlist_full_id(message: str) -> str | None:
    parsed_url = urlparse(message)
    url_path = parsed_url.path
    url_query = parse_qs(parsed_url.query)

    if url_path.startswith("/music/playlist/"):
        full_id = url_path.split("/music/playlist/")[1]
    elif url_path.startswith("/music/album/"):
        full_id = url_path.split("/music/album/")[1]
    elif url_query:
        z = url_query.get("z")
        act = url_query.get("act")
        pl_unparsed = ""

        if z and z[0].startswith("audio_playlist"):
            pl_unparsed = z[0]
        elif act and act[0].startswith("audio_playlist"):
            pl_unparsed = act[0]

        if pl_unparsed:
            full_id = pl_unparsed.split("audio_playlist")[1]
        else:
            return None

    return full_id


async def add_event_handlers(bot: TelegramClient, client: TelegramClient, vk_api: API) -> None:  # noqa: C901
    # Callback for playlist button in main channel
    @bot.on(events.CallbackQuery(data=b"wait_for_pl_link"))
    async def wait_for_pl_link(event: events.CallbackQuery.Event) -> None:
        await event.answer(PL_NOT_READY)

    @bot.on(events.CallbackQuery(data=b"pl_confirm", func=lambda e: is_current_state(e, State.WAITING_FOR_CHOISE)))
    async def new_pl(event: events.CallbackQuery.Event) -> None:
        await event.edit(buttons=Button.clear())
        if not await is_user_authorized(event):
            raise events.StopPropagation

        data = state_manager.get_info(event.sender_id)[1]
        celery_app.send_task(
            "app.main.forward_playlist",
            task_id=f"{VttTaskType.playlist}_{data['owner_id']}_{data['playlist_id']}",
            queue="vtt-wall",
            kwargs={
                "owner_id": data["owner_id"],
                "playlist_id_id": data["playlist_id"],
                "access_key": data["access_key"],
            },
        )
        state_manager.clear_info(event.sender_id)
        await event.respond(PL_ADDED_TO_THE_QUEUE)
        raise StopPropagation

    @bot.on(events.NewMessage(pattern=pl_link_pattern, func=lambda e: is_current_state(e, State.WAITING_FOR_LINK)))
    async def on_new_pl(event: NewMessageEvent) -> None:
        if not await is_user_authorized(event):
            raise events.StopPropagation

        await event.respond(PL_SEARCHING)
        sender = event.sender_id
        full_id = _get_playlist_full_id(message=event.message.message)
        if not full_id or not (match := playlist_full_id.fullmatch(full_id)):
            await event.respond("Icorrect link!")
            raise StopPropagation

        groupdict = match.groupdict()
        owner_id = int(groupdict["owner_id"])
        playlist_id = int(groupdict["playlist_id"])
        access_key = groupdict.get("access_key")

        if not await is_playlist_exists(vk_api, owner_id, playlist_id, access_key):
            await event.respond(PL_NOT_FOUND_IN_VK)
            raise StopPropagation

        queued_task = get_queued_task(
            backend=celery_app.backend,
            task_type=VttTaskType.playlist,
            owner_id=owner_id,
            post_id=playlist_id,
        )
        if queued_task and queued_task["status"] in {"SENT", "STARTED"}:
            waiting_text = PL_ALREADY_IN_THE_QUEUE if queued_task["status"] == "SENT" else PL_ALREADY_STARTED
            message = await event.respond(
                waiting_text,
                buttons=[
                    Button.inline(PL_YES, data=b"pl_confirm"),
                    Button.inline(PL_CANCEL, data=b"cancel"),
                ],
            )
            state_manager.set_info(
                sender,
                State.WAITING_FOR_CHOISE,
                {
                    "choice_message": message.id,
                    "owner_id": owner_id,
                    "playlist_id": playlist_id,
                    "access_key": access_key,
                },
            )
            raise StopPropagation

        peer = await get_tgm_channel_entity(client, settings.TGM_PL_CHANNEL_ID)
        if peer is None:
            message = await event.respond(PL_UNKNOWN_CHANNEL)
            state_manager.clear_info(event.sender_id)
            raise StopPropagation

        search_result: ChannelMessages = await client(
            SearchRequest(
                peer=peer,
                q=f"https://vk.com/music/playlist/{owner_id}_{playlist_id}",
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
        waiting_text = PL_NOT_FOUND_IN_TGM
        if search_result.messages:
            waiting_text = PL_FOUND_IN_TGM
            message = cast(Message, search_result.messages[0])
            await bot.forward_messages(sender, message.id, from_peer=message.chat_id)

        message = await event.respond(
            waiting_text,
            buttons=[
                Button.inline(PL_YES, data=b"pl_confirm"),
                Button.inline(PL_CANCEL, data=b"cancel"),
            ],
        )

        state_manager.set_info(
            sender,
            State.WAITING_FOR_CHOISE,
            {
                "choice_message": message.id,
                "owner_id": owner_id,
                "playlist_id": playlist_id,
                "access_key": access_key,
            },
        )
        raise StopPropagation
