import re
from urllib.parse import parse_qs, urlparse

from telethon import events
from telethon.client.telegramclient import TelegramClient
from telethon.events import StopPropagation
from telethon.tl.custom.button import Button
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.patched import Message
from telethon.tl.types import InputMessagesFilterUrl
from telethon.tl.types.messages import ChannelMessages
from vkbottle.api.api import API

from app.bot.plugins.common import NewMessageEvent, check_permission, check_state, state_manager
from app.bot.state_manager import State
from app.celery_worker import forward_playlist
from app.config import _, settings
from app.utils.database import VttTaskType, get_queued_task
from app.utils.telegram import get_entity_by_id
from app.utils.vk import get_playlist

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
    r"(https:\/\/)?(www\.)?(m\.)?vk\.com\/(music(/(playlist|album)|/?\?.+audio_playlist)|\w+/?\?.+audio_playlist)"
)

playlist_full_id = re.compile(r"(?P<owner_id>-?\d+)_(?P<playlist_id>\d+)((_|\/)(?P<access_key>[a-z0-9]+))?")


async def init(bot: TelegramClient, client: TelegramClient, vk_api: API):

    # Callback for playlist button in main channel
    @bot.on(events.CallbackQuery(data=b"wait_for_pl_link"))
    async def wait_for_pl_link(event: events.CallbackQuery.Event):
        await event.answer(PL_NOT_READY)

    @bot.on(events.CallbackQuery(data=b"pl_confirm", func=lambda e: check_state(e, State.WAITING_FOR_CHOISE)))
    async def new_pl(event: events.CallbackQuery.Event):
        await event.edit(buttons=Button.clear())
        if not await check_permission(event):
            raise events.StopPropagation

        data = state_manager.get_info(event.sender_id)[1]
        forward_playlist.delay(
            owner_id=data["owner_id"],
            playlist_id=data["playlist_id"],
            access_key=data["access_key"],
        )
        state_manager.clear_info(event.sender_id)
        await event.respond(PL_ADDED_TO_THE_QUEUE)
        raise StopPropagation

    @bot.on(events.NewMessage(pattern=pl_link_pattern, func=lambda e: check_state(e, State.WAITING_FOR_LINK)))
    async def on_new_pl(event: NewMessageEvent):
        if not await check_permission(event):
            raise events.StopPropagation

        await event.respond(PL_SEARCHING)
        sender = event.sender_id
        parsed_url = urlparse(event.message.message)
        url_path = parsed_url.path
        url_query = parse_qs(parsed_url.query)
        full_id = ""

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
                await event.respond("Icorrect link!")
                raise StopPropagation
        match = playlist_full_id.search(full_id)
        groupdict = match.groupdict()
        owner_id = groupdict.get("owner_id")
        playlist_id = groupdict.get("playlist_id")
        access_key = groupdict.get("access_key")

        playlist = await get_playlist(vk_api, owner_id, playlist_id, access_key, with_audios=False)

        if not playlist:
            await event.respond(PL_NOT_FOUND_IN_VK)
            raise StopPropagation

        queued_task = get_queued_task(owner_id, playlist_id, VttTaskType.playlist)
        if queued_task:
            if queued_task.status == "SENT":
                waiting_text = PL_ALREADY_IN_THE_QUEUE
            else:
                waiting_text = PL_ALREADY_STARTED
            message = await event.respond(
                waiting_text,
                buttons=[
                    Button.inline(PL_YES, data="pl_confirm"),
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

        peer = await get_entity_by_id(client, settings.TGM_PL_CHANNEL_ID)
        if peer is None:
            message = await event.respond(PL_UNKNOWN_CHANNEL)
            state_manager.clear_info(event.sender_id)
            raise StopPropagation
        filter = InputMessagesFilterUrl()
        search_result: ChannelMessages = await client(
            SearchRequest(
                peer=peer,
                q=f"https://vk.com/music/playlist/{owner_id}_{playlist_id}",
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
        waiting_text = PL_NOT_FOUND_IN_TGM
        if search_result.messages:
            waiting_text = PL_FOUND_IN_TGM
            message: Message = search_result.messages[0]
            await bot.forward_messages(sender, message.id, from_peer=message.chat_id)
        message = await event.respond(
            waiting_text,
            buttons=[
                Button.inline(PL_YES, data="pl_confirm"),
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
