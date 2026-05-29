from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated

from fastapi import Body, Depends, FastAPI, Request, Response
from loguru import logger
from vtt_common.schemas import VttTaskType
from vtt_common.tasks import get_queued_task

from app.config import Settings, get_settings
from app.logging import init_logging
from app.schemas import CallbackType, VkCallback, WallPostType, WallWallpostFull
from app.utils import setup_vk_server
from app.worker import create_worker

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping
    from typing import Any

    from celery import Celery
    from loguru import Logger


init_logging()


def _handle_wall_post_new(
    body: VkCallback,
    settings: Settings,
    celery_app: Celery,
    ctx_logger: Logger,
) -> None:
    post_data = body.object
    if post_data is None:
        ctx_logger.warning("Post object is missing")
        return

    post = WallWallpostFull(**post_data)

    owner_id = post.owner_id
    if not owner_id:
        ctx_logger.warning("Post does not have an owner_id")
        return

    post_id = post.id
    if not post_id:
        ctx_logger.warning("Post does not have a post_id")
        return

    ctx_logger = ctx_logger.bind(full_id=f"{owner_id}_{post_id}")

    if post.marked_as_ads and settings.VTT_IGNORE_ADS:
        ctx_logger.warning("Ignoring ad post")
        return

    donut = post.donut
    if donut and donut.is_donut:
        ctx_logger.warning("Ignoring donut post")
        return

    if post.post_type in (
        WallPostType.POST,
        WallPostType.REPLY,
        WallPostType.PHOTO,
        WallPostType.VIDEO,
    ):
        ctx_logger.info("New post")
        if get_queued_task(
            backend=celery_app.backend,
            task_type=VttTaskType.wall,
            owner_id=owner_id,
            post_id=post_id,
        ):
            ctx_logger.warning("Post already exists")
        else:
            celery_app.send_task(
                "app.main.forward_wall",
                task_id=f"{VttTaskType.wall}_{owner_id}_{post_id}",
                queue="vtt-wall",
                kwargs={
                    "owner_id": owner_id,
                    "wall_id": post_id,
                },
            )


def vk_callback(
    request: Request,
    body: Annotated[VkCallback, Body(...)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    ctx_logger = logger.bind(event_id=body.event_id)
    if body.secret != settings.VK_SERVER_SECRET:
        ctx_logger.warning("Unauthorized request")
        return Response(status_code=401)

    event_type = body.type
    ctx_logger.info("New event: {}", event_type)

    if event_type == CallbackType.CONFIRMATION:
        confirmation_code: str = request.state.confirmation_code
        ctx_logger.info("Response with confirmation code '{}' has been sent.", confirmation_code)
        return Response(confirmation_code)

    if event_type == CallbackType.WALL_POST_NEW:
        _handle_wall_post_new(body, settings, request.app.state.celery_app, ctx_logger)

    ctx_logger.info("Response 'ok' has been sent.")
    return Response("ok")


def create_app(settings: Settings | None = None, celery_app: Celery | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[Mapping[str, Any]]:
        yield {"confirmation_code": await setup_vk_server(settings=settings)}

    app = FastAPI(lifespan=lifespan)
    app.add_api_route("/", methods=["POST"], endpoint=vk_callback)

    app.state.celery_app = create_worker(app=celery_app)

    if settings:
        app.dependency_overrides[get_settings] = lambda: settings

    return app
