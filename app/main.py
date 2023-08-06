import logging
import os

from fastapi import BackgroundTasks, FastAPI, Response
from vkbottle_types.objects import CallbackType, WallPostType, WallWallpostFull

from app.celery_worker import forward_wall
from app.config import settings
from app.schemas.vk import VkCallback
from app.utils.database import VttTaskType, get_queued_task
from app.utils.vk import setup_vk_server

logger = logging.getLogger(__name__)

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    await setup_vk_server()


@app.post("/")
def read_vk(req: VkCallback, bg: BackgroundTasks):
    if req.secret != settings.VK_SERVER_SECRET:
        logger.warning(f"Unauthorized request: {req}")
        return Response(status_code=401)

    req_type = req.type
    logger.info(f"[VK] New event: {req_type}")
    if req_type == CallbackType.CONFIRMATION:
        confirmation_token = os.getenv("VK_CONFIRM_CODE")
        logger.info(f'[VK] Response with confirmation code "{confirmation_token}" has been sent.')
        return Response(confirmation_token)
    if req_type == CallbackType.WALL_POST_NEW:
        post = WallWallpostFull(**req.object)
        if post.marked_as_ads and settings.VK_IGNORE_ADS:
            logger.info('[VK] Response with "ok" string has been sent.')
            return Response("ok")
        if post.post_type in [
            WallPostType.POST,
            WallPostType.REPLY,
            WallPostType.PHOTO,
            WallPostType.VIDEO,
        ] and not (post.donut and post.donut.is_donut):
            owner_id = post.owner_id
            post_id = post.id
            if owner_id and post_id:
                logger.info(f"[VK] New post ({owner_id}_{post_id}).")
                if get_queued_task(owner_id, post_id, VttTaskType.wall):
                    logger.warning(f"[VK] Post {owner_id}_{post_id} already exists.")
                else:
                    forward_wall.delay(
                        owner_id=owner_id,
                        wall_id=post_id,
                    )
    logger.info('[VK] Response with "ok" string has been sent.')
    return Response("ok")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_config="logging_config.yaml",
        use_colors=True,
        log_level="debug",
    )
