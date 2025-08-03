from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from loguru import logger
from vkbottle import VKAPIError
from vkbottle_types.objects import AudioAudio, BasePropertyExists

from app.vk.schemas import AudioPlaylist
from app.vtt.schemas import VttVideo

if TYPE_CHECKING:
    from vkbottle.api import API
    from vkbottle.api.abc import ABCAPI
    from vkbottle_types.objects import VideoVideoFiles, VideoVideoFull
    from vkbottle_types.responses.wall import WallGetByIdExtendedResponseModel


def get_video_url(formats: VideoVideoFiles | None) -> str | None:
    if not formats:
        return None

    return cast(
        str | None,
        formats.mp4_720 or formats.mp4_480 or formats.mp4_360 or formats.mp4_240 or formats.mp4_144 or formats.flv_320,
    )


class VkService:
    def __init__(self, vk_api: ABCAPI) -> None:
        self.vk_api = vk_api

    @classmethod
    async def _request_with_version(cls, method: str, data: dict[str, Any], version: str, api: API) -> dict[str, Any]:
        data = await api.validate_request(data)

        async with api.token_generator as token:
            response = await api.http_client.request_text(
                api.API_URL + method,
                method="POST",
                data=data,
                params={"access_token": token, "v": version},
            )
        logger.debug("Request {} with {} data returned {}", method, data, response)
        return await api.validate_response(method, data, response)  # type: ignore[no-any-return]

    async def get_extended_wall(
        self,
        owner_id: int,
        wall_id: int,
    ) -> WallGetByIdExtendedResponseModel | None:
        try:
            wall_info = await self.vk_api.wall.get_by_id(
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
                    await self.vk_api.request(
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

    async def get_audio_by_ids(self, audio_ids: list[str]) -> list[AudioAudio]:
        audios: list[dict[str, Any]] = (
            await self.vk_api.request(
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
    ) -> list[AudioAudio]:
        audios: list[dict[str, Any]] = (
            await self.vk_api.request(
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
        videos = cast("list[VideoVideoFull]", (await self.vk_api.video.get(videos=video_ids)).items or [])

        vtt_videos = []
        for video in videos:
            _video = video
            url: str | None = None
            is_live = _video.live is BasePropertyExists.PROPERTY_EXISTS
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
