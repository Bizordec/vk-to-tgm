from aiohttp import ClientSession
from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession
from vkaudiotoken import supported_clients
from vkbottle import API, AiohttpClient

from app.config import settings
from app.decorators import async_to_sync
from app.services.tgm import TelegramService
from app.services.vk import VkService
from app.vk.request_validators import VkLangRequestValidator
from app.vtt.factories.message import VttMessageFactory
from app.worker import worker


@worker.task()
@async_to_sync
async def forward_wall(owner_id: int, wall_id: int) -> str:
    with logger.contextualize(owner_id=owner_id, wall_id=wall_id):
        logger.info("New post received.")

        kate_user = API(
            token=settings.VK_KATE_TOKEN,
            http_client=AiohttpClient(
                session=ClientSession(
                    headers={"User-agent": supported_clients.KATE.user_agent},
                ),
            ),
        )
        kate_user.request_validators.append(VkLangRequestValidator())

        vk_user = API(
            token=settings.VK_OFFICIAL_TOKEN,
            http_client=AiohttpClient(
                session=ClientSession(
                    headers={"User-agent": supported_clients.VK_OFFICIAL.user_agent},
                ),
            ),
        )
        vk_user.request_validators.append(VkLangRequestValidator())

        vk_service = VkService(kate_user=kate_user, vk_user=vk_user)

        vtt_factory = VttMessageFactory(vk_service=vk_service)
        vtt_message = await vtt_factory.create(owner_id=owner_id, wall_id=wall_id)

        if isinstance(vtt_message, str):
            logger.warning(f"Post was not sent to Telegram. Reason: '{vtt_message}'")
            return vtt_message

        tgm_bot = TelegramClient(
            session=StringSession(settings.TGM_BOT_SESSION),
            api_id=settings.TGM_API_ID,
            api_hash=settings.TGM_API_HASH,
        )
        tgm_bot.parse_mode = "html"

        async with await tgm_bot.start(bot_token=settings.TGM_BOT_TOKEN):
            tgm_service = TelegramService(
                tgm_client=tgm_bot,
                vk_service=vk_service,
                channel_id=settings.TGM_CHANNEL_ID,
            )
            return await tgm_service.send_vtt_message(vtt_message=vtt_message)
