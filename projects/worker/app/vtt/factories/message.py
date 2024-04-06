from loguru import logger
from vkbottle_types.objects import GroupsGroupFull, WallWallpostFull

from app.config import settings
from app.services.vk import VkService
from app.vtt.attachments import get_attachment_handler
from app.vtt.factories.playlist import VttPlaylistFactory
from app.vtt.factories.text import VttWallTextFactory
from app.vtt.schemas import VttAttachments, VttMessage, VttText


class VttMessageFactory:
    def __init__(self, vk_service: VkService) -> None:
        self.vk_service = vk_service

    async def _get_attachments(self, wall: WallWallpostFull) -> VttAttachments:
        vtt_attachments = VttAttachments()
        if not wall.attachments and not wall.geo:
            logger.info("No attachments found.")
            return vtt_attachments

        vtt_attachments.geo = wall.geo

        for attachment in wall.attachments:
            handler = get_attachment_handler(attachment=attachment)
            handler.add_to_message(vtt_attachments=vtt_attachments)

        if vtt_attachments.audio_playlist_id:
            audio_playlist_id = vtt_attachments.audio_playlist_id
            vtt_attachments.audio_playlist = await VttPlaylistFactory(vk_service=self.vk_service).create(
                owner_id=audio_playlist_id.owner_id,
                playlist_id=audio_playlist_id.playlist_id,
                access_key=audio_playlist_id.access_key,
            )

        if vtt_attachments.audio_ids:
            vtt_attachments.audios = await self.vk_service.get_audio_by_ids(audio_ids=vtt_attachments.audio_ids)

        if vtt_attachments.video_ids:
            vtt_attachments.videos = await self.vk_service.get_video_by_ids(video_ids=vtt_attachments.video_ids)

        return vtt_attachments

    async def _get_text(
        self,
        wall: WallWallpostFull,
        attachments: VttAttachments,
        groups: list[GroupsGroupFull] | None = None,
        *,
        is_repost: bool = False,
    ) -> VttText:
        text_factory = VttWallTextFactory(
            vk_api=self.vk_service.kate_user,
            wall=wall,
            attachments=attachments,
            groups=groups,
            is_repost=is_repost,
        )
        return await text_factory.create()

    async def create(
        self,
        owner_id: int,
        wall_id: int,
    ) -> VttMessage | str:
        extended_wall = await self.vk_service.get_extended_wall(owner_id=owner_id, wall_id=wall_id)
        if not extended_wall or not extended_wall.items:
            logger.warning("Wall post not found.")
            return "NOT_FOUND"

        wall = extended_wall.items[0]

        if wall.donut and wall.donut.is_donut:
            logger.warning("Skipping donut wall post.")
            return "IS_DONUT"

        if wall.marked_as_ads and settings.VTT_IGNORE_ADS:
            logger.warning("Skipping ad wall post.")
            return "IS_AD"

        groups = extended_wall.groups

        main_attachments = await self._get_attachments(wall)
        main_text = await self._get_text(wall=wall, attachments=main_attachments, groups=groups)
        vtt_message = VttMessage(text=main_text, attachments=main_attachments)

        if wall.copy_history:
            for repost in wall.copy_history[::-1]:
                repost_attachments = await self._get_attachments(repost)
                repost_text = await self._get_text(
                    wall=repost,
                    attachments=repost_attachments,
                    groups=groups,
                    is_repost=True,
                )
                vtt_message.copy_history.append(
                    VttMessage(
                        text=repost_text,
                        attachments=repost_attachments,
                    ),
                )

        return vtt_message
