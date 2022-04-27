import logging
from typing import Optional

from aiohttp import ClientSession
from telethon.client.telegramclient import TelegramClient
from telethon.tl.custom.button import Button
from telethon.tl.types import Message
from vkaudiotoken import supported_clients
from vkbottle import AiohttpClient
from vkbottle.api.api import API

from app.config import _, settings
from app.handlers.text import PlaylistTextHandler
from app.schemas.vk import AudioPlaylist
from app.utils.downloader import Downloader
from app.utils.telegram import get_message_link
from app.utils.vk import VkLangRequestValidator, get_playlist

logger = logging.getLogger(__name__)

PL_READY = _("PL_READY")
PL_GO_TO_WALL = _("PL_GO_TO_WALL")
PL_OF = _("PL_OF")


class PlaylistHandler:
    def __init__(
        self,
        owner_id: int,
        playlist_id: int,
        access_key: Optional[str],
        tgm_bot: TelegramClient,
        kate_token: str,
        main_channel_id: Optional[int] = None,
        main_message_id: Optional[int] = None,
    ) -> None:
        self.pl_channel_id = settings.TGM_PL_CHANNEL_ID
        self.owner_id = owner_id
        self.playlist_id = playlist_id
        self.access_key = access_key
        self.main_channel_id = main_channel_id
        self.main_message_id = main_message_id
        self.tgm_bot = tgm_bot
        self.kate_user = API(
            token=kate_token,
            http_client=AiohttpClient(
                session=ClientSession(
                    headers={"User-agent": supported_clients.KATE.user_agent},
                ),
            ),
        )
        self.kate_user.request_validators.append(VkLangRequestValidator())

        self.vk_user = API(
            token=settings.VK_OFFICIAL_TOKEN,
            http_client=AiohttpClient(
                session=ClientSession(
                    headers={"User-agent": supported_clients.VK_OFFICIAL.user_agent},
                ),
            ),
        )
        self.vk_user.request_validators.append(VkLangRequestValidator())

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.kate_user.http_client.close()
        await self.vk_user.http_client.close()

    async def get_text(
        self,
        playlist: AudioPlaylist,
    ):
        text = PlaylistTextHandler(self.kate_user, playlist)
        await text.process_text()
        return text

    async def run(self) -> str:
        playlist = await get_playlist(
            self.kate_user,
            self.owner_id,
            self.playlist_id,
            self.access_key,
        )

        if not playlist:
            full_id = f"{self.owner_id}_{self.playlist_id}_{self.access_key}"
            logger.warning(f"[{full_id}] Playlist not found.")
            return "NOT_FOUND"

        logger.info(f"[{playlist.full_id}] Sending main playlist message...")
        pl_captions = (await self.get_text(playlist)).caption
        pl_captions_first = pl_captions[0] if pl_captions else None
        pl_captions_first_text = pl_captions_first[0] if pl_captions_first else ""
        pl_captions_first_entities = pl_captions_first[1] if pl_captions_first else None
        async with Downloader() as downloader:
            downloaded_photo = None
            if playlist.photo:
                downloaded_photo = await downloader.download_media(playlist.photo)
            pl_main_message = await self.tgm_bot.send_message(
                self.pl_channel_id,
                file=downloaded_photo,
                message=pl_captions_first_text,
                formatting_entities=pl_captions_first_entities,
                link_preview=False,
            )

        if self.main_channel_id and self.main_message_id:
            logger.info(f"[{playlist.full_id}] Setting links between playlist and main message...")
            main_post_link = get_message_link(
                await self.tgm_bot.get_entity(self.main_channel_id),
                self.main_message_id,
            )
            pl_main_message = await self.tgm_bot.edit_message(
                pl_main_message,
                buttons=Button.url(f"🔗 {PL_GO_TO_WALL}", main_post_link),
            )

            pl_post_link = get_message_link(
                await self.tgm_bot.get_entity(self.pl_channel_id),
                pl_main_message.id,
            )
            main_message: Message = await self.tgm_bot.get_messages(
                self.main_channel_id,
                ids=self.main_message_id,
            )
            await self.tgm_bot.edit_message(
                main_message,
                buttons=Button.url(f"🔊 {PL_READY}", pl_post_link),
            )

        logger.info(f"[{playlist.full_id}] Sending rest playlist messages...")
        rest_messages = pl_captions[1:]
        for text, entities in rest_messages:
            await self.tgm_bot.send_message(
                self.pl_channel_id,
                message=text,
                formatting_entities=entities,
                link_preview=False,
                reply_to=pl_main_message,
            )

        logger.info(f"[{playlist.full_id}] Uploading playlist audios...")
        pl_length = len(playlist.audios)
        for i in range(0, pl_length, 10):
            current_audios = playlist.audios[i : i + 10]  # noqa: E203
            current_audios_len = len(current_audios)
            pl_audio_caption = [""] * (current_audios_len - 1) + [
                f"{i + 1}-{i + current_audios_len} {PL_OF} {pl_length}"
            ]
            async with Downloader() as downloader:
                current_audios_paths = await downloader.download_audios(current_audios, self.vk_user)
                await self.tgm_bot.send_file(
                    self.pl_channel_id,
                    file=current_audios_paths,
                    caption=pl_audio_caption,
                    voice_note=True,
                    reply_to=pl_main_message,
                )
        return get_message_link(await self.tgm_bot.get_entity(self.pl_channel_id), pl_main_message.id)
