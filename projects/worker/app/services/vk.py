from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from loguru import logger
from vkbottle import VKAPIError
from vkbottle_types.objects import AudioAudio, BasePropertyExists, VideoVideoFiles

from app.vk.schemas import AudioPlaylist
from app.vtt.schemas import VttVideo

if TYPE_CHECKING:
    from vkbottle.api.abc import ABCAPI
    from vkbottle_types.responses.wall import GetByIdExtendedResponseModel


def get_video_url(formats: VideoVideoFiles | None) -> str | None:
    if not formats:
        return None
    return (
        formats.mp4_720 or formats.mp4_480 or formats.mp4_360 or formats.mp4_240 or formats.mp4_144 or formats.flv_320
    )


class VkService:
    def __init__(self, kate_user: ABCAPI, vk_user: ABCAPI) -> None:
        self.kate_user = kate_user
        self.vk_user = vk_user

    async def get_extended_wall(
        self,
        owner_id: int,
        wall_id: int,
    ) -> GetByIdExtendedResponseModel | None:
        try:
            wall_info = await self.kate_user.wall.get_by_id(
                posts=[f"{owner_id}_{wall_id}"],
                copy_history_depth=100,
                extended=True,
            )
            if not wall_info.items:
                return None
        except VKAPIError as error:
            logger.warning(f"Failed to get wall post (https://vk.com/wall/{owner_id}_{wall_id}): {error.description}")
            return None
        else:
            return wall_info

    async def get_audio_playlist(
        self,
        owner_id: int,
        playlist_id: int,
        access_key: str | None = None,
    ) -> AudioPlaylist | None:
        try:
            vk_audio_playlist = cast(
                dict[str, Any],
                (
                    await self.kate_user.request(
                        "audio.getPlaylistById",
                        {
                            "owner_id": owner_id,
                            "playlist_id": playlist_id,
                            "access_key": access_key,
                        },
                    )
                )["response"],
            )
        except VKAPIError as error:
            pl_full_id = f"{owner_id}_{playlist_id}"
            if access_key:
                pl_full_id += f"_{access_key}"
            logger.warning(f"Failed to get playlist (https://vk.com/music/album/{pl_full_id}): {error.description}")
            return None
        else:
            return AudioPlaylist(**vk_audio_playlist)

    async def get_audio_by_ids(self, audio_ids: list[str], *, use_vk_user: bool = False) -> list[AudioAudio]:
        vk_api = self.kate_user
        if use_vk_user:
            vk_api = self.vk_user
        audios: list[dict[str, Any]] = (
            await vk_api.request(
                "audio.getById",
                {
                    "audios": ",".join(audio_ids),
                },
            )
        )["response"]
        return [AudioAudio(**audio) for audio in audios if audio.get("url")]

    async def get_audios_by_playlist_id(
        self,
        owner_id: int,
        playlist_id: int,
        access_key: str,
        count: int,
        *,
        use_vk_user: bool = False,
    ) -> list[AudioAudio]:
        vk_api = self.kate_user
        if use_vk_user:
            vk_api = self.vk_user
        audios: list[dict[str, Any]] = (
            await vk_api.request(
                "audio.get",
                {
                    "owner_id": owner_id,
                    "playlist_id": playlist_id,
                    "access_key": access_key,
                    "count": count,
                },
            )
        )["response"]["items"]
        return [AudioAudio(**audio) for audio in audios if audio.get("url")]

    async def get_video_by_ids(self, video_ids: list[str]) -> list[VttVideo]:
        videos = (await self.kate_user.video.get(videos=video_ids)).items or []

        vtt_videos = []
        for video in videos:
            _video = video
            url: str | None = None
            is_live = _video.live is BasePropertyExists.property_exists
            if is_live:
                logger.warning("Found live stream.")
                url = f"https://vk.com/video{_video.owner_id}_{_video.id}"
            elif _video.platform:
                url = _video.files and _video.files.external
                if not url:
                    logger.warning("External video url not found.")
                    continue
            else:
                url = get_video_url(_video.files)
                if not url:
                    logger.warning("VK video url not found, trying with another token...")
                    video_full_id = f"{_video.owner_id}_{_video.id}_{_video.access_key}"
                    _video = next(iter((await self.vk_user.video.get(videos=[video_full_id])).items or []), None)
                    if not _video:
                        logger.warning("VK video url not found.")
                        continue
                    url = get_video_url(_video.files)
                    if not url:
                        logger.warning("VK video url not found.")
                        continue
            vtt_videos.append(
                VttVideo(
                    title=_video.title or "",
                    url=url,
                    platform=_video.platform,
                    is_live=is_live,
                ),
            )
        return vtt_videos
