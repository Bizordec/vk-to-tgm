from __future__ import annotations

from typing import TYPE_CHECKING, cast

from loguru import logger
from telethon.extensions import html
from telethon.tl.custom.button import Button
from telethon.tl.types import Channel, InputGeoPoint, InputMediaGeoLive
from telethon.tl.types import Message as TelethonMessage

from app.config import _, settings
from app.services.downloader import Downloader
from app.worker import worker

if TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.tl.types import TypeMessageEntity
    from vkbottle_types.objects import AudioAudio

    from app.services.vk import VkService
    from app.vtt.schemas import VttAttachments, VttAudioPlaylist, VttMessage

GO_TO_POST = _("GO_TO_POST")
GO_TO_PL = _("GO_TO_PL")
PL_OUT_OF = _("PL_OUT_OF")


class TelegramWallSender:
    def __init__(self, tgm_client: TelegramClient, vk_service: VkService, channel_id: int) -> None:
        self.tgm_client = tgm_client
        self.vk_service = vk_service

        self.channel_id = channel_id

    async def _send_first_main_message(
        self,
        message_text: list[tuple[str, list[TypeMessageEntity]]],
        caption_text: list[tuple[str, list[TypeMessageEntity]]],
        attachments: VttAttachments,
        reply_to_message_id: int | None = None,
    ) -> tuple[TelethonMessage, bool]:
        logger.info("Sending first main message...")

        first_message_text, first_message_entities = next(iter(message_text), ("", None))
        first_caption_text, first_caption_entities = next(iter(caption_text), ("", None))
        first_caption_html = html.unparse(first_caption_text, first_caption_entities)

        videos = [video for video in attachments.videos if (video.platform is None and not video.is_live)]

        has_link_preview = attachments.link or any((video.platform or video.is_live) for video in attachments.videos)

        is_caption = False

        async with Downloader(vk_service=self.vk_service) as downloader:
            if attachments.photos:
                is_caption = True
                files = await downloader.download_files(urls=attachments.photos)
                if videos:
                    files.extend(await downloader.download_files(videos=videos))
                main_msg = cast(
                    TelethonMessage,
                    (
                        await self.tgm_client.send_file(
                            self.channel_id,
                            file=files,
                            caption=first_caption_html,
                            video_note=True,
                            link_preview=has_link_preview,
                            reply_to=reply_to_message_id,
                        )
                    )[0],
                )
            elif videos:
                is_caption = True
                current_videos = await downloader.download_files(videos=videos)
                main_msg = cast(
                    TelethonMessage,
                    (
                        await self.tgm_client.send_file(
                            self.channel_id,
                            file=current_videos,
                            caption=first_caption_html,
                            video_note=True,
                            link_preview=has_link_preview,
                            reply_to=reply_to_message_id,
                        )
                    )[0],
                )
            elif has_link_preview:
                main_msg = await self.tgm_client.send_message(
                    self.channel_id,
                    message=first_message_text,
                    formatting_entities=first_message_entities,
                    link_preview=True,
                    reply_to=reply_to_message_id,
                )
            elif attachments.documents:
                is_caption = True
                document = attachments.documents.pop(0)
                downloaded_documents = await downloader.download_media(document.url)
                main_msg = cast(
                    TelethonMessage,
                    await self.tgm_client.send_file(
                        self.channel_id,
                        file=downloaded_documents,
                        caption=first_caption_text,
                        formatting_entities=first_caption_entities,
                        reply_to=reply_to_message_id,
                    ),
                )
            elif attachments.audios:
                is_caption = True
                downloaded_audios = await downloader.download_files(audios=attachments.audios[:10])
                main_msg = cast(
                    TelethonMessage,
                    (
                        await self.tgm_client.send_file(
                            self.channel_id,
                            caption=[""] * (len(downloaded_audios) - 1) + [first_caption_html],
                            file=downloaded_audios,
                            voice_note=True,
                            reply_to=reply_to_message_id,
                        )
                    )[0],
                )
                attachments.audios = attachments.audios[10:]
            else:
                main_msg = await self.tgm_client.send_message(
                    self.channel_id,
                    message=first_message_text,
                    formatting_entities=first_message_entities,
                    link_preview=has_link_preview,
                    reply_to=reply_to_message_id,
                )

        return main_msg, is_caption

    async def _send_rest_main_text_messages(
        self,
        first_message_id: int,
        rest_messages_text: list[tuple[str, list[TypeMessageEntity]]],
    ) -> None:
        if not rest_messages_text:
            return

        logger.info("Sending rest main message...")
        for text, entities in rest_messages_text:
            await self.tgm_client.send_message(
                self.channel_id,
                message=text,
                formatting_entities=entities,
                link_preview=False,
                reply_to=first_message_id,
            )

    async def _send_rest_main_media_messages(self, first_message_id: int, attachments: VttAttachments) -> None:
        if attachments.geo and attachments.geo.coordinates:
            logger.info("Sending geo location...")
            latitude, longitude = (float(x) for x in attachments.geo.coordinates.split(" "))
            await self.tgm_client.send_file(
                self.channel_id,
                file=InputMediaGeoLive(geo_point=InputGeoPoint(lat=latitude, long=longitude)),
                reply_to=first_message_id,
            )

        if attachments.poll:
            logger.info("Sending poll...")
            await self.tgm_client.send_file(
                self.channel_id,
                file=attachments.poll,
                reply_to=first_message_id,
            )

        async with Downloader(vk_service=self.vk_service) as downloader:
            if attachments.audios:
                logger.info("Sending audios...")
                current_audios = await downloader.download_files(audios=attachments.audios)
                await self.tgm_client.send_file(
                    self.channel_id,
                    file=current_audios,
                    voice_note=True,
                    reply_to=first_message_id,
                )
                logger.info("Audios sent successfully.")

            if attachments.documents:
                logger.info("Sending documents...")
                document_urls = [doc.url for doc in attachments.documents]
                document_paths = await downloader.download_files(urls=document_urls)
                await self.tgm_client.send_file(
                    self.channel_id,
                    file=document_paths,
                    force_document=True,
                    reply_to=first_message_id,
                )
                logger.info("Documents sent successfully.")

            if attachments.audio_playlist:
                playlist = attachments.audio_playlist

                playlist_caption = playlist.text.caption

                first_pl_caption_text, first_pl_caption_entities = next(iter(playlist_caption), ("", None))
                first_pl_caption_html = html.unparse(first_pl_caption_text, first_pl_caption_entities)

                downloaded_photo = None
                if playlist.photo:
                    downloaded_photo = await downloader.download_media(url=playlist.photo)

                # Send playlist message without audios to the main channel
                main_pl_message = await self.tgm_client.send_message(
                    self.channel_id,
                    message=first_pl_caption_html,
                    file=downloaded_photo,
                    reply_to=first_message_id,
                )

                if settings.TGM_PL_CHANNEL_ID:
                    logger.info("Sending playlist task...")

                    # Send task to create messages in the playlist channel
                    worker.send_task(
                        "app.main.forward_playlist",
                        queue="vtt-playlist",
                        kwargs={
                            "owner_id": playlist.owner_id,
                            "playlist_id": playlist.id,
                            "access_key": playlist.access_key,
                            "reply_channel_id": self.channel_id,
                            "reply_message_id": main_pl_message.id,
                        },
                    )

                    logger.info(f"[{playlist.full_id}] Playlist task sent successfully.")

                # Send rest playlist messages if any to the main channel
                rest_messages = playlist_caption[1:]
                for text, entities in rest_messages:
                    await self.tgm_client.send_message(
                        self.channel_id,
                        message=text,
                        formatting_entities=entities,
                        link_preview=False,
                        reply_to=main_pl_message,
                    )

    async def send_main_message(
        self,
        vtt_message: VttMessage,
        reply_to_message_id: int | None = None,
    ) -> TelethonMessage:
        message_text = vtt_message.text.message
        caption_text = vtt_message.text.caption

        attachments = vtt_message.attachments

        first_message, is_caption = await self._send_first_main_message(
            message_text=message_text,
            caption_text=caption_text,
            attachments=attachments,
            reply_to_message_id=reply_to_message_id,
        )

        rest_messages_text = caption_text[1:] if is_caption else message_text[1:]
        await self._send_rest_main_text_messages(
            first_message_id=first_message.id,
            rest_messages_text=rest_messages_text,
        )

        await self._send_rest_main_media_messages(
            first_message_id=first_message.id,
            attachments=attachments,
        )

        logger.info("Main message sent successfully.")
        return first_message

    async def _get_message_link(self, message_id: int) -> str:
        entity = await self.tgm_client.get_entity(self.channel_id)

        if not isinstance(entity, Channel):
            logger.warning(f"Entity with id '{self.channel_id}' is not a channel.")
            return ""

        channel = entity.username
        if channel is None:
            channel = f"c/{entity.id}"

        return f"https://t.me/{channel}/{message_id}"

    async def send_vtt_message(self, vtt_message: VttMessage) -> str:
        if not vtt_message.copy_history:
            main_message = await self.send_main_message(vtt_message=vtt_message)
        else:
            reversed_posts = vtt_message.copy_history[::-1]

            # Send all reposts except the last one
            reply_id = None
            for repost in reversed_posts[:-1]:
                repost_message = await self.send_main_message(
                    vtt_message=repost,
                    reply_to_message_id=reply_id,
                )
                reply_id = repost_message.id

            repost = reversed_posts[-1]

            main_text = vtt_message.text

            # If that is a bare repost (i.e. main message does not have any text),
            # then add footer text from main message
            if not main_text.header:
                repost.text.footer += main_text.footer

            # Send last repost
            main_message = await self.send_main_message(
                vtt_message=repost,
                reply_to_message_id=reply_id,
            )

            # Send main message if it has text
            if main_text.header:
                main_message = await self.send_main_message(
                    vtt_message=vtt_message,
                    reply_to_message_id=reply_id,
                )

        return await self._get_message_link(message_id=main_message.id)


class TelegramPlaylistSender:
    def __init__(
        self,
        tgm_client: TelegramClient,
        vk_service: VkService,
        pl_channel_id: int,
        wall_channel_id: int | None = None,
        wall_message_id: int | None = None,
    ) -> None:
        self.tgm_client = tgm_client
        self.vk_service = vk_service

        self.pl_channel_id = pl_channel_id

        self.wall_channel_id = wall_channel_id
        self.wall_message_id = wall_message_id

    async def _get_message_link(self, channel_id: int, message_id: int) -> str:
        entity = await self.tgm_client.get_entity(channel_id)

        if not isinstance(entity, Channel):
            logger.warning(f"Entity with id '{channel_id}' is not a channel.")
            return ""

        channel = entity.username
        if channel is None:
            channel = f"c/{entity.id}"

        return f"https://t.me/{channel}/{message_id}"

    async def _add_link_buttons(self, pl_message: TelethonMessage) -> None:
        if not self.wall_channel_id or not self.wall_message_id:
            return

        wall_post_link = await self._get_message_link(
            channel_id=self.wall_channel_id,
            message_id=self.wall_message_id,
        )
        pl_main_message = await self.tgm_client.edit_message(
            entity=pl_message,
            buttons=Button.url(f"🔗 {GO_TO_POST}", wall_post_link),
        )

        pl_post_link = await self._get_message_link(
            channel_id=self.pl_channel_id,
            message_id=pl_main_message.id,
        )
        wall_message = cast(
            TelethonMessage,
            await self.tgm_client.get_messages(
                self.wall_channel_id,
                ids=self.wall_message_id,
            ),
        )
        await self.tgm_client.edit_message(
            wall_message,
            buttons=Button.url(f"🔊 {GO_TO_PL}", pl_post_link),
        )

    async def _send_first_main_message(self, vtt_playlist: VttAudioPlaylist) -> tuple[TelethonMessage, bool]:
        logger.info("Sending first main message...")

        is_caption = False

        async with Downloader(vk_service=self.vk_service) as downloader:
            if not vtt_playlist.photo:
                message, entities = next(iter(vtt_playlist.text.message), ("", None))
                downloaded_photo = None
            else:
                is_caption = True
                message, entities = next(iter(vtt_playlist.text.caption), ("", None))
                downloaded_photo = await downloader.download_media(url=vtt_playlist.photo)

        main_message = await self.tgm_client.send_message(
            self.pl_channel_id,
            file=downloaded_photo,
            message=message,
            formatting_entities=entities,
            link_preview=False,
        )

        await self._add_link_buttons(pl_message=main_message)

        return main_message, is_caption

    async def _send_rest_main_text_messages(
        self,
        first_message_id: int,
        rest_messages_text: list[tuple[str, list[TypeMessageEntity]]],
    ) -> None:
        if not rest_messages_text:
            return

        logger.info("Sending rest main message...")
        for text, entities in rest_messages_text:
            await self.tgm_client.send_message(
                self.pl_channel_id,
                message=text,
                formatting_entities=entities,
                link_preview=False,
                reply_to=first_message_id,
            )

    async def _send_main_message(self, vtt_playlist: VttAudioPlaylist) -> TelethonMessage:
        first_message, is_caption = await self._send_first_main_message(vtt_playlist=vtt_playlist)

        rest_messages_text = vtt_playlist.text.caption[1:] if is_caption else vtt_playlist.text.message[1:]
        await self._send_rest_main_text_messages(
            first_message_id=first_message.id,
            rest_messages_text=rest_messages_text,
        )

        logger.info("Main message sent successfully.")
        return first_message

    async def _send_audios(self, audios: list[AudioAudio] | None, main_message_id: int) -> None:
        if not audios:
            return

        full_audios_count = len(audios)
        for i in range(0, full_audios_count, 10):
            current_audios = audios[i : i + 10]
            current_audios_count = len(current_audios)
            pl_audio_caption = [""] * (current_audios_count - 1) + [
                f"{i + 1}-{i + current_audios_count} {PL_OUT_OF} {full_audios_count}",
            ]
            async with Downloader(vk_service=self.vk_service) as downloader:
                current_audios_paths = await downloader.download_files(audios=current_audios)
                await self.tgm_client.send_file(
                    self.pl_channel_id,
                    file=current_audios_paths,
                    caption=pl_audio_caption,
                    reply_to=main_message_id,
                )

    async def send_vtt_playlist(self, vtt_playlist: VttAudioPlaylist) -> str:
        main_message = await self._send_main_message(vtt_playlist=vtt_playlist)
        main_message_id = main_message.id

        await self._send_audios(audios=vtt_playlist.audios, main_message_id=main_message_id)

        return await self._get_message_link(channel_id=self.pl_channel_id, message_id=main_message_id)
