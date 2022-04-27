import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from aiohttp import ClientSession
from telethon import TelegramClient
from vkaudiotoken import supported_clients
from vkbottle import AiohttpClient
from vkbottle.api.api import API

from app.bot import plugins
from app.config import settings
from app.utils.vk import VkLangRequestValidator

logging.basicConfig(
    format="%(levelname)s: %(asctime)s [%(name)s] %(message)s",
    level=logging.INFO,
    handlers=[
        RotatingFileHandler(filename="logs/vtt-bot.log", maxBytes=1000000, backupCount=5),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("bot.main")


async def main():
    vk_api = API(
        token=settings.KATE_TOKEN,
        http_client=AiohttpClient(
            session=ClientSession(
                headers={"User-agent": supported_clients.KATE.user_agent},
            ),
        ),
    )
    vk_api.request_validators.append(VkLangRequestValidator())

    client = TelegramClient("tgm_search_client", settings.TGM_API_ID, settings.TGM_API_HASH)
    await client.start(phone=lambda: settings.TGM_CLIENT_PHONE)

    bot = TelegramClient("tgm_bot", settings.TGM_API_ID, settings.TGM_API_HASH)
    await bot.start(bot_token=settings.TGM_BOT_TOKEN)

    async with client:
        await plugins.init(bot, client, vk_api)
        await bot.run_until_disconnected()
        await vk_api.http_client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Program interrupted by user.")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
