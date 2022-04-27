import logging
import re
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

import vkbottle_types
from aiohttp import ClientSession
from telethon.client.telegramclient import TelegramClient
from telethon.extensions import html
from telethon.tl.custom.button import Button
from telethon.tl.types import InputGeoPoint, InputMediaGeoLive, InputMediaPoll, Message, Poll, PollAnswer
from vkaudiotoken import supported_clients
from vkbottle import AiohttpClient
from vkbottle.api.api import API
from vkbottle_types.objects import (
    AudioAudio,
    BasePropertyExists,
    GroupsGroupFull,
    WallWallpostAttachmentType,
    WallWallpostFull,
)

from app.config import _, settings
from app.handlers.text import PlaylistTextHandler, WallTextHandler
from app.schemas.vk import Attachments, AudioPlaylist, Document, VttLink, VttMarket, VttVideo
from app.utils.downloader import Downloader
from app.utils.telegram import get_message_link
from app.utils.vk import VkLangRequestValidator, get_extended_wall, get_photo_url, get_playlist, get_video_url

logger = logging.getLogger(__name__)

PL_SOON = _("PL_SOON")


class WallHandler:
    API_VERSION = vkbottle_types.API_VERSION
    MAX_MESSAGE_LENGTH = 4096

    def __init__(
        self,
        owner_id: int,
        id: int,
        tgm_bot: TelegramClient,
    ) -> None:
        self.channel_id = settings.TGM_CHANNEL_ID
        self.pl_channel_id = settings.TGM_PL_CHANNEL_ID
        self.tgm_bot = tgm_bot

        self.owner_id = owner_id
        self.wall_id = id
        self.groups: Optional[List[GroupsGroupFull]] = None

        self.kate_user = API(
            token=settings.KATE_TOKEN,
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

    async def collect_attachments(self, wall: WallWallpostFull) -> Attachments:
        attachments = Attachments()

        if not wall.attachments:
            return attachments
        logger.info("Collecting attachments...")

        audio_ids: List[str] = []
        video_ids: List[str] = []
        for attachment in wall.attachments:
            attachment_type = attachment.type
            if attachment_type == WallWallpostAttachmentType.PHOTO:
                photo = attachment.photo
                if not photo:
                    continue
                photo_url = get_photo_url(photo.sizes)
                if not photo_url:
                    continue
                attachments.photos.append(photo_url)
            elif attachment_type == WallWallpostAttachmentType.AUDIO:
                audio = attachment.audio
                if not audio:
                    continue
                audio_ids.append(f"{audio.owner_id}_{audio.id}_{audio.access_key}")
            elif attachment_type == WallWallpostAttachmentType.VIDEO:
                video = attachment.video
                if not video:
                    continue
                video_ids.append(f"{video.owner_id}_{video.id}_{video.access_key}")
            elif attachment_type == WallWallpostAttachmentType.DOC:
                document = attachment.doc
                if not (document and document.url):
                    continue
                attachments.documents.append(
                    Document(
                        url=document.url,
                        extension=document.ext,
                    )
                )
            elif attachment_type == WallWallpostAttachmentType.MARKET:
                market = attachment.market
                if not market:
                    continue
                attachments.market = VttMarket(
                    id=market.id,
                    owner_id=market.owner_id,
                    title=market.title,
                )
            elif attachment_type == WallWallpostAttachmentType.POLL:
                poll = attachment.poll
                if not poll:
                    continue
                answers = [PollAnswer(answer.text, str(index).encode()) for index, answer in enumerate(poll.answers)]
                attachments.poll = InputMediaPoll(
                    poll=Poll(
                        id=1,
                        question=poll.question,
                        answers=answers,
                        multiple_choice=poll.multiple,
                    )
                )
            elif attachment_type == WallWallpostAttachmentType.LINK:
                link = attachment.link
                if not link:
                    continue
                parsed_link = urlparse(link.url)

                # Not a VK link
                if parsed_link.netloc not in {"vk.com", "m.vk.com"}:
                    attachments.link = VttLink(
                        caption=link.caption or parsed_link.netloc,
                        url=link.url,
                    )
                    continue

                if parsed_link.netloc == "m.vk.com":
                    parsed_link = parsed_link._replace(netloc="vk.com")

                # Playlist
                query = parse_qs(parsed_link.query)
                if settings.TGM_PL_CHANNEL_ID and "act" in query and query["act"][0].startswith("audio_playlist"):
                    pattern = re.compile(r"(?P<owner_id>-?\d+)_(?P<playlist_id>\d+)")
                    match = pattern.search(query["act"][0])
                    if not match:
                        continue
                    owner_id = match.group("owner_id")
                    if not owner_id:
                        continue
                    playlist_id = match.group("playlist_id")
                    if not playlist_id:
                        continue

                    access_key = None
                    if "access_hash" in query:
                        access_key = query["access_hash"][0]

                    playlist = await get_playlist(
                        self.kate_user,
                        owner_id,
                        playlist_id,
                        access_key,
                        with_audios=False,
                    )
                    if playlist:
                        attachments.audio_playlist = playlist
                    continue

                # Everything else
                attachments.link = VttLink(
                    caption=parsed_link.netloc,
                    url=parsed_link.geturl(),
                )

        if audio_ids:
            audios: List[dict] = (
                await self.kate_user.request(
                    "audio.getById",
                    {
                        "audios": ",".join(audio_ids),
                    },
                )
            )["response"]
            attachments.audios = [AudioAudio(**audio) for audio in audios if audio.get("url")]

        if video_ids:
            videos = (await self.kate_user.video.get(videos=video_ids)).items or []

            for video in videos:
                url = ""
                is_live = video.live is BasePropertyExists.property_exists
                if is_live:
                    logger.warning("Found live stream.")
                    url = f"https://vk.com/video{video.owner_id}_{video.id}"
                elif video.platform:
                    url = video.files and video.files.external
                    if not url:
                        logger.warning("External video url not found.")
                        continue
                else:
                    url = get_video_url(video.files)
                    if not url:
                        logger.warning("VK video url not found, trying with another token...")
                        video_full_id = "{}_{}_{}".format(video.owner_id, video.id, video.access_key)
                        video = next(iter((await self.vk_user.video.get(videos=[video_full_id])).items or []), None)
                        if not video:
                            logger.warning("VK video url not found.")
                            continue
                        url = get_video_url(video.files)
                        if not url:
                            logger.warning("VK video url not found.")
                            continue
                attachments.videos.append(
                    VttVideo(
                        title=video.title or "",
                        url=url,
                        platform=video.platform,
                        is_live=is_live,
                    ),
                )
        return attachments

    async def get_text(
        self,
        wall: WallWallpostFull,
        attachments: Attachments,
        is_repost: bool = False,
    ):
        text = WallTextHandler(self.kate_user, wall, attachments, is_repost, self.groups)
        await text.process_text()
        return text

    async def get_pl_text(
        self,
        playlist: AudioPlaylist,
    ):
        text = PlaylistTextHandler(self.kate_user, playlist)
        await text.process_text()
        return text

    async def send_main_message(
        self,
        wall_text: WallTextHandler,
        attachments: Attachments,
        reply_to_message_id: Optional[int] = None,
    ) -> Message:
        logger.info("Handling main message...")
        caption = wall_text.caption
        caption_first = caption[0] if caption else None
        caption_first_text = caption_first[0] if caption_first else None
        caption_first_entities = caption_first[1] if caption_first else None
        caption_first_html = html.unparse(*caption_first) if caption_first else ""

        message = wall_text.message
        message_first = message[0] if message else None
        message_first_text = message_first[0] if message_first else ""
        message_first_entities = message_first[1] if message_first else None

        vk_videos = [v for v in attachments.videos if (v.platform is None and not v.is_live)]

        has_link_preview = attachments.link or any((v.platform or v.is_live) for v in attachments.videos)

        is_caption = False
        if attachments.photos:
            is_caption = True
            async with Downloader() as downloader:
                files = await downloader.download_medias(attachments.photos)
                if vk_videos:
                    files += await downloader.download_videos(vk_videos)
                main_msg: Message = (
                    await self.tgm_bot.send_file(
                        self.channel_id,
                        file=files,
                        caption=caption_first_html,
                        video_note=True,
                        link_preview=has_link_preview,
                        reply_to=reply_to_message_id,
                    )
                )[0]
        elif vk_videos:
            is_caption = True
            async with Downloader() as downloader:
                current_videos = await downloader.download_videos(vk_videos)
                main_msg = (
                    await self.tgm_bot.send_file(
                        self.channel_id,
                        file=current_videos,
                        caption=caption_first_html,
                        video_note=True,
                        link_preview=has_link_preview,
                        reply_to=reply_to_message_id,
                    )
                )[0]
        elif has_link_preview:
            main_msg = await self.tgm_bot.send_message(
                self.channel_id,
                message=message_first_text,
                formatting_entities=message_first_entities,
                link_preview=True,
                reply_to=reply_to_message_id,
            )
        elif attachments.documents:
            is_caption = True
            document = attachments.documents.pop(0)
            async with Downloader() as downloader:
                downloaded_documents = await downloader.download_media(document.url)
                main_msg = await self.tgm_bot.send_file(
                    self.channel_id,
                    file=downloaded_documents,
                    caption=caption_first_text,
                    formatting_entities=caption_first_entities,
                    reply_to=reply_to_message_id,
                )
        elif attachments.audios:
            is_caption = True
            async with Downloader() as downloader:
                downloaded_audios = await downloader.download_audios(attachments.audios[:10], self.vk_user)
                main_msg = (
                    await self.tgm_bot.send_file(
                        self.channel_id,
                        caption=[""] * (len(downloaded_audios) - 1) + [caption_first_html],
                        file=downloaded_audios,
                        voice_note=True,
                        reply_to=reply_to_message_id,
                    )
                )[0]
            attachments.audios = attachments.audios[10:]
        else:
            main_msg = await self.tgm_bot.send_message(
                self.channel_id,
                message=message_first_text,
                formatting_entities=message_first_entities,
                link_preview=has_link_preview,
                reply_to=reply_to_message_id,
            )

        # Send rest messages
        rest_messages = caption[1:] if is_caption else message[1:]
        for text, entities in rest_messages:
            await self.tgm_bot.send_message(
                self.channel_id,
                message=text,
                formatting_entities=entities,
                link_preview=False,
                reply_to=main_msg,
            )
        logger.info("Main message sent successfully.")
        return main_msg

    async def send_replies(
        self,
        wall: WallWallpostFull,
        attachments: Attachments,
        main_message_id: int,
        wall_text: WallTextHandler,
    ) -> None:
        if wall.geo:
            logger.info("Sending geo location...")
            geo = wall.geo
            latitude, longitude = [float(x) for x in geo.coordinates.split(" ")]
            await self.tgm_bot.send_file(
                self.channel_id,
                file=InputMediaGeoLive(geo_point=InputGeoPoint(lat=latitude, long=longitude)),
                reply_to=main_message_id,
            )
        if attachments.poll:
            logger.info("Sending poll...")
            await self.tgm_bot.send_file(
                self.channel_id,
                file=attachments.poll,
                reply_to=main_message_id,
            )
        if attachments.audios:
            logger.info("Sending audios...")
            async with Downloader() as downloader:
                current_audios = await downloader.download_audios(attachments.audios, self.vk_user)
                await self.tgm_bot.send_file(
                    self.channel_id,
                    file=current_audios,
                    voice_note=True,
                    reply_to=main_message_id,
                )
            logger.info("Audios sent successfully.")
        if attachments.documents:
            logger.info("Sending documents...")
            document_urls = [doc.url for doc in attachments.documents]
            async with Downloader() as downloader:
                document_paths = await downloader.download_medias(document_urls)
                await self.tgm_bot.send_file(
                    self.channel_id,
                    file=document_paths,
                    force_document=True,
                    reply_to=main_message_id,
                )
            logger.info("Documents sent successfully.")

        # Send rest messages
        rest_messages = wall_text.caption[1:]
        for text, entities in rest_messages:
            await self.tgm_bot.send_message(
                self.channel_id,
                message=text,
                formatting_entities=entities,
                link_preview=False,
                reply_to=main_message_id,
            )

        if attachments.audio_playlist:
            logger.info("Sending playlist...")
            playlist = attachments.audio_playlist

            # Send playlist link to the main channel
            playlist_text = await self.get_pl_text(playlist)
            main_pl_caption = playlist_text.caption
            main_pl_caption_first = main_pl_caption[0] if main_pl_caption else None
            main_pl_caption_html = html.unparse(*main_pl_caption_first) if main_pl_caption_first else ""
            async with Downloader() as downloader:
                downloaded_photo = None
                if playlist.photo:
                    downloaded_photo = await downloader.download_media(playlist.photo)
                main_pl_link_message = await self.tgm_bot.send_message(
                    self.channel_id,
                    message=main_pl_caption_html,
                    file=downloaded_photo,
                    buttons=Button.inline(PL_SOON, b"wait_for_pl_link"),
                    reply_to=main_message_id,
                )

            from app.celery_worker import forward_playlist

            forward_playlist.delay(
                owner_id=playlist.owner_id,
                playlist_id=playlist.id,
                access_key=playlist.access_key,
                reply_channel_id=self.channel_id,
                reply_message_id=main_pl_link_message.id,
            )

            rest_messages = main_pl_caption[1:]
            for text, entities in rest_messages:
                await self.tgm_bot.send_message(
                    self.channel_id,
                    message=text,
                    formatting_entities=entities,
                    link_preview=False,
                    reply_to=main_pl_link_message,
                )
            logger.info(f"[{playlist.full_id}] Playlist sent successfully.")

    async def run(self) -> str:
        extended_wall = await get_extended_wall(self.kate_user, self.owner_id, self.wall_id)
        if not (extended_wall and extended_wall.items):
            return "NOT_FOUND"

        wall = extended_wall.items[0]
        if wall.donut and wall.donut.is_donut:
            return "IS_DONUT"

        self.groups = extended_wall.groups

        main_attachments = await self.collect_attachments(wall)
        main_text = await self.get_text(wall, main_attachments)

        if not wall.copy_history:
            main_message = await self.send_main_message(main_text, main_attachments)
            reply_id = main_message.id
            await self.send_replies(wall, main_attachments, reply_id, main_text)
        else:
            reversed_posts = wall.copy_history[::-1]
            reply_id = None
            for repost in reversed_posts[:-1]:
                repost_attachments = await self.collect_attachments(repost)

                repost_text = await self.get_text(
                    repost,
                    repost_attachments,
                    is_repost=True,
                )

                repost_message = await self.send_main_message(
                    repost_text,
                    repost_attachments,
                    reply_to_message_id=reply_id,
                )
                reply_id = repost_message.id
                await self.send_replies(repost, repost_attachments, reply_id, repost_text)

            repost = reversed_posts[-1]
            repost_attachments = await self.collect_attachments(repost)

            repost_text = await self.get_text(
                repost,
                repost_attachments,
                is_repost=True,
            )
            if not main_text.header:
                repost_text.footer += main_text.footer

            main_message = await self.send_main_message(
                repost_text,
                repost_attachments,
                reply_to_message_id=reply_id,
            )
            reply_id = main_message.id
            await self.send_replies(repost, repost_attachments, reply_id, repost_text)

            if main_text.header:
                await self.send_main_message(
                    main_text,
                    main_attachments,
                    reply_to_message_id=reply_id,
                )
        return get_message_link(await self.tgm_bot.get_entity(self.channel_id), main_message.id)
