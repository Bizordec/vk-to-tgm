from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from loguru import logger
from vkbottle_types.objects import CallbackType, WallPostType, WallWallpostFull

from app.config import settings
from app.schemas import (
    VkCallback,  # noqa: TCH001
)
from app.utils import is_queued_post, setup_vk_server
from app.worker import app as celery_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping
    from typing import Any


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[Mapping[str, Any], None]:
    logger.disable("vkbottle")
    confirmation_code = await setup_vk_server()
    yield {"confirmation_code": confirmation_code}


app = FastAPI(lifespan=lifespan)


@app.post("/")
def vk_callback(body: VkCallback, request: Request) -> Response:
    if body.secret != settings.VK_SERVER_SECRET:
        logger.warning(f"Unauthorized request: {body}")
        return Response(status_code=401)

    event_type = body.type
    logger.info(f"New event: {event_type}")

    if event_type == CallbackType.CONFIRMATION:
        confirmation_code: str = request.state.confirmation_code
        logger.info(
            f"Response with confirmation code '{confirmation_code}' has been sent.",
        )
        return Response(confirmation_code)

    if event_type == CallbackType.WALL_POST_NEW:
        post = WallWallpostFull(**body.object)
        owner_id = post.owner_id
        post_id = post.id
        if not owner_id or not post_id:
            logger.warning(f"Post doesn't have owner_id or post_id: {post}")
            return Response("ok")

        full_id = f"{owner_id}_{post_id}"

        if post.marked_as_ads and settings.VTT_IGNORE_ADS:
            logger.warning(f"Ignored ad post ({full_id})")
            return Response("ok")

        if post.donut and post.donut.is_donut:
            logger.warning(f"Ignored donut post ({full_id})")
            return Response("ok")

        if post.post_type in [
            WallPostType.POST,
            WallPostType.REPLY,
            WallPostType.PHOTO,
            WallPostType.VIDEO,
        ]:
            logger.info(f"New post ({full_id}).")
            if is_queued_post(owner_id, post_id):
                logger.warning(f"Post {full_id} already exists.")
            else:
                celery_app.send_task(
                    "app.main.forward_wall",
                    queue="vtt-wall",
                    kwargs={
                        "owner_id": owner_id,
                        "wall_id": post_id,
                    },
                )

    logger.info("Response with 'ok' string has been sent.")
    return Response("ok")
