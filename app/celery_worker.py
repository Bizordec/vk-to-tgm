import asyncio
import logging
from typing import Optional, Tuple

import uvloop
from celery import Celery
from celery.app.task import Context
from celery.signals import before_task_publish
from telethon import TelegramClient

from app import celeryconfig
from app.config import settings
from app.handlers.playlist import PlaylistHandler
from app.handlers.wall import WallHandler
from app.utils.database import VttTaskType, vtt_store_result

logger = logging.getLogger(__name__)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

worker = Celery("vk-to-tgm")
worker.config_from_object(celeryconfig)


@before_task_publish.connect
def set_state_on_task_call(
    headers: dict,
    body: Tuple[dict, dict, dict],
    routing_key: str,
    **kwargs,
):
    task_name: str = headers["task"]
    short_task_name = task_name.split(".")[-1]
    if short_task_name not in ("forward_wall", "forward_playlist"):
        return

    task_id: str = headers["id"]
    args: dict = body[0]
    _kwargs: dict = body[1]
    task_request = Context(
        task=task_name,
        args=args,
        kwargs=_kwargs,
        delivery_info={
            "routing_key": routing_key,
        },
    )

    if short_task_name == "forward_wall":
        vk_type = VttTaskType.wall
        vk_id = kwargs.get("wall_id")
    elif short_task_name == "forward_playlist":
        vk_type = VttTaskType.playlist
        vk_id = kwargs.get("playlist_id")
    else:
        vk_type = VttTaskType.unknown
        vk_id = 0

    vtt_store_result(
        vk_type=vk_type,
        vk_owner_id=kwargs["owner_id"],
        vk_id=vk_id,
        task_uuid=task_id,
        result=None,
        state="SENT",
        request=task_request,
    )


async def aio_forward_wall(
    *,
    owner_id: int,
    wall_id: int,
):
    wall_url = f"https://vk.com/wall{owner_id}_{wall_id}"
    logger.info(f"Handling wall task ({wall_url})...")

    tgm_bot = TelegramClient("worker_bot", settings.TGM_API_ID, settings.TGM_API_HASH)
    tgm_bot.parse_mode = "html"

    async with await tgm_bot.start(bot_token=settings.TGM_BOT_TOKEN):
        async with WallHandler(
            owner_id,
            wall_id,
            tgm_bot,
        ) as handler:
            post_link = await handler.run()

    logger.info(f"Wall task ({wall_url}) done.")

    return post_link


async def aio_forward_playlist(
    *,
    owner_id: int,
    playlist_id: int,
    access_key: Optional[str] = None,
    reply_channel_id: Optional[int] = None,
    reply_message_id: Optional[int] = None,
):
    pl_url = f"https://vk.com/music/playlist/{owner_id}_{playlist_id}_{access_key}"
    logger.info(f"Handling task for forwarding playlist {pl_url}...")

    tgm_bot = TelegramClient("worker_pl_bot", settings.TGM_API_ID, settings.TGM_API_HASH)
    tgm_bot.parse_mode = "html"

    async with await tgm_bot.start(bot_token=settings.TGM_BOT_TOKEN):
        async with PlaylistHandler(
            owner_id,
            playlist_id,
            access_key,
            tgm_bot,
            settings.KATE_TOKEN,
            main_channel_id=reply_channel_id,
            main_message_id=reply_message_id,
        ) as handler:
            post_link = await handler.run()

    logger.info(f"Task for playlist ({pl_url}) done.")

    return post_link


@worker.task()
def forward_wall(
    *,
    owner_id: int,
    wall_id: int,
):
    result = asyncio.run(
        aio_forward_wall(
            owner_id=owner_id,
            wall_id=wall_id,
        )
    )
    return result


@worker.task()
def forward_playlist(
    *,
    owner_id: int,
    playlist_id: int,
    access_key: Optional[str] = None,
    reply_channel_id: Optional[int] = None,
    reply_message_id: Optional[int] = None,
):
    result = asyncio.run(
        aio_forward_playlist(
            owner_id=owner_id,
            playlist_id=playlist_id,
            access_key=access_key,
            reply_channel_id=reply_channel_id,
            reply_message_id=reply_message_id,
        )
    )
    return result
