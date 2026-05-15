import asyncio

from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession
from vkbottle.api.api import API
from vkbottle.http import AiohttpClient
from vtt_common.proxy import get_tgm_proxy_config

from app import plugins
from app.config import settings
from app.vk.request_validators import VkLangRequestValidator


async def main() -> None:
    vk_api = API(token=settings.VK_TOKEN, http_client=AiohttpClient())
    vk_api.request_validators.append(VkLangRequestValidator())
    logger.info("VK API client initialized")

    logger.info("Creating Telegram user client...")
    proxy_config = (
        get_tgm_proxy_config(
            proxy_type=settings.TGM_PROXY_TYPE,
            proxy_addr=settings.TGM_PROXY_ADDR,
            proxy_port=settings.TGM_PROXY_PORT,
            proxy_user=settings.TGM_PROXY_USER,
            proxy_pass=settings.TGM_PROXY_PASS,
            proxy_rdns=settings.TGM_PROXY_RDNS,
        )
        # NOTE: MTProto proxy not working with user client
        # (ValueError: readexactly size can not be less than zero)
        if settings.TGM_PROXY_TYPE != "mtproto"
        else {}
    )
    client = TelegramClient(
        session=StringSession(settings.TGM_CLIENT_SESSION),
        api_id=settings.TGM_API_ID,
        api_hash=settings.TGM_API_HASH,
        **proxy_config,
    )
    client.parse_mode = "html"
    await client.start(phone=lambda: settings.TGM_CLIENT_PHONE)
    logger.info("Telegram user client started successfully")

    logger.info("Creating Telegram bot client...")
    bot = TelegramClient(
        session=StringSession(settings.TGM_BOT_SESSION),
        api_id=settings.TGM_API_ID,
        api_hash=settings.TGM_API_HASH,
        **get_tgm_proxy_config(
            proxy_type=settings.TGM_PROXY_TYPE,
            proxy_addr=settings.TGM_PROXY_ADDR,
            proxy_port=settings.TGM_PROXY_PORT,
            proxy_user=settings.TGM_PROXY_USER,
            proxy_pass=settings.TGM_PROXY_PASS,
            proxy_rdns=settings.TGM_PROXY_RDNS,
            proxy_mtproto_secret=settings.TGM_PROXY_MTPROTO_SECRET,
            proxy_mtproto_connection=settings.TGM_PROXY_MTPROTO_CONNECTION,
        ),
    )
    bot.parse_mode = "html"
    await bot.start(bot_token=settings.TGM_BOT_TOKEN)
    logger.info("Telegram bot client started successfully")

    async with client:
        await plugins.add_event_handlers(bot=bot, client=client, vk_api=vk_api)

        logger.info("Starting bot event loop")
        await bot.run_until_disconnected()
        await vk_api.http_client.close()
        logger.info("Bot disconnected, shutting down")


if __name__ == "__main__":
    logger.disable("vkbottle")
    asyncio.run(main())
