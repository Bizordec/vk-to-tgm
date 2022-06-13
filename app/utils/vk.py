import logging
import os
from typing import Callable, List, Optional, Union

from vkbottle import AiohttpClient, VKAPIError
from vkbottle.api.api import API
from vkbottle.api.request_validator import ABCRequestValidator
from vkbottle_types import API_VERSION
from vkbottle_types.methods.groups import GroupsCategory
from vkbottle_types.objects import (
    AudioAudio,
    GroupsCallbackServer,
    PhotosPhotoSizes,
    PhotosPhotoSizesType,
    VideoVideoFiles,
)
from vkbottle_types.responses.wall import GetByIdExtendedResponseModel

from app.config import settings
from app.schemas.vk import AudioPlaylist, VkApiAudioPlaylist

logger = logging.getLogger(__name__)


async def setup_vk_server():
    logger.info("[VK] Setting up callback server...")
    vk_group = GroupsCategory(
        API(
            token=settings.VK_COMMUNITY_TOKEN,
            http_client=AiohttpClient(),
        ),
    )
    group_id = settings.VK_COMMUNITY_ID
    server_url = settings.SERVER_URL
    server_title = settings.VK_SERVER_TITLE
    try:
        confirm = await vk_group.get_callback_confirmation_code(group_id=group_id)
        os.environ.setdefault("VK_CONFIRM_CODE", confirm.code)
        logger.info(f"[VK] Callback code to confirm: {confirm.code}")

        server_id: Optional[int] = None
        secret_key = settings.VK_SERVER_SECRET

        servs = await vk_group.get_callback_servers(group_id=group_id)
        if not servs.items:
            new_serv = await vk_group.add_callback_server(
                group_id=group_id,
                url=server_url,
                title=server_title,
                secret_key=secret_key,
            )
            server_id = new_serv.server_id
            logger.info("[VK] No callback servers found, added new.")
        else:
            find_by_title: Callable[[GroupsCallbackServer], GroupsCallbackServer] = lambda x: x.title == server_title
            main_serv: Optional[GroupsCallbackServer] = next(filter(find_by_title, servs.items), None)
            if main_serv:
                await vk_group.edit_callback_server(
                    group_id=group_id,
                    server_id=main_serv.id,
                    url=server_url,
                    title=main_serv.title,
                    secret_key=secret_key,
                )
                server_id = main_serv.id
                logger.info(f"[VK] Using the existing callback server: {main_serv.title}")
            else:
                new_serv = await vk_group.add_callback_server(
                    group_id=group_id,
                    url=server_url,
                    title=server_title,
                    secret_key=secret_key,
                )
                server_id = new_serv.server_id
                logger.info(f'[VK] No callback server found by title "{server_title}", added new.')

        await vk_group.set_callback_settings(
            group_id=group_id,
            server_id=server_id,
            api_version=API_VERSION,
            wall_post_new=True,
        )
        logger.info("[VK] The callback server settings has been set.")
    finally:
        await vk_group.api.http_client.close()


async def get_playlist(
    vk_api: API,
    owner_id: int,
    playlist_id: int,
    access_key: Optional[str] = None,
    with_audios: bool = True,
) -> Union[AudioPlaylist, None]:
    playlist_info = None
    try:
        playlist_info = (
            await vk_api.request(
                "audio.getPlaylistById",
                {
                    "owner_id": owner_id,
                    "playlist_id": playlist_id,
                    "access_key": access_key,
                },
            )
        )["response"]
    except VKAPIError as error:
        pl_full_id = f"{owner_id}_{playlist_id}"
        if access_key:
            pl_full_id += f"_{access_key}"
        logger.warning(f"Failed to get playlist (https://vk.com/music/album/{pl_full_id}): {error.description}")

    if not playlist_info:
        return None

    playlist_info = VkApiAudioPlaylist(**playlist_info)

    full_title = playlist_info.title
    if playlist_info.main_artists:
        artists = ", ".join([artist.name for artist in playlist_info.main_artists])
        full_title = f"{artists} - {playlist_info.title}"

    playlist_photo = None
    if playlist_info.photo:
        playlist_photo = playlist_info.photo.photo_1200
    elif playlist_info.thumbs:
        playlist_photo = playlist_info.thumbs[0].photo_1200

    playlist_audios = []
    if with_audios:
        playlist_audios = (
            await vk_api.request(
                "audio.get",
                {
                    "owner_id": owner_id,
                    "playlist_id": playlist_id,
                    "count": playlist_info.count,
                    "access_key": access_key,
                },
            )
        )["response"]["items"]
        playlist_audios = [AudioAudio(**audio) for audio in playlist_audios if audio.get("url")]
    return AudioPlaylist(
        id=playlist_id,
        owner_id=owner_id,
        access_key=access_key,
        full_id=f"{owner_id}_{playlist_id}_{access_key}",
        title=full_title,
        description=playlist_info.description,
        photo=playlist_photo,
        audios=playlist_audios,
    )


async def get_extended_wall(
    vk_api: API,
    owner_id: int,
    wall_id: int,
) -> Union[GetByIdExtendedResponseModel, None]:
    try:
        wall_info: GetByIdExtendedResponseModel = await vk_api.wall.get_by_id(
            posts=[f"{owner_id}_{wall_id}"],
            copy_history_depth=100,
            extended=True,
        )
        if not wall_info.items:
            return None
        return wall_info
    except VKAPIError as error:
        logger.warning(f"Failed to get wall post (https://vk.com/wall/{owner_id}_{wall_id}): {error.description}")
        return None


def get_video_url(formats: Optional[VideoVideoFiles]) -> Union[str, None]:
    if not formats:
        return None
    url = formats.mp4_720 or formats.mp4_480 or formats.mp4_360 or formats.mp4_240 or formats.flv_320
    return url


# Filter cropped photo sizes
photo_sizes = [
    size
    for size in PhotosPhotoSizesType
    if size
    not in (
        PhotosPhotoSizesType.O,
        PhotosPhotoSizesType.P,
        PhotosPhotoSizesType.Q,
        PhotosPhotoSizesType.R,
    )
]


def get_photo_url(sizes: Optional[List[PhotosPhotoSizes]]) -> Union[str, None]:
    if not sizes:
        return None

    max_photo = (None, None)
    for size in sizes:
        try:
            current_index = photo_sizes.index(size.type)
        except ValueError:
            continue
        if not max_photo[0] or (current_index > photo_sizes.index(max_photo[0])):
            max_photo = (size.type, size.url)
    return max_photo[1]


class VkLangRequestValidator(ABCRequestValidator):
    async def validate(self, request: dict) -> dict:
        request["lang"] = settings.VK_API_LANGUAGE
        return request
