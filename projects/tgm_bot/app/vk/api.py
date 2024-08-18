from loguru import logger
from vkbottle import VKAPIError
from vkbottle.api.api import API


async def is_playlist_exists(
    vk_api: API,
    owner_id: int,
    playlist_id: int,
    access_key: str | None = None,
) -> bool:
    try:
        await vk_api.request(
            "audio.getPlaylistById",
            {
                "owner_id": owner_id,
                "playlist_id": playlist_id,
                "access_key": access_key,
            },
        )
    except VKAPIError as error:
        pl_full_id = f"{owner_id}_{playlist_id}"
        if access_key:
            pl_full_id += f"_{access_key}"

        logger.warning(f"Failed to get playlist (https://vk.com/music/album/{pl_full_id}): {error.description}")

        return False

    return True
