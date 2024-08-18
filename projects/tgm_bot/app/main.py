import asyncio

from aiohttp import ClientSession
from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession
from vkaudiotoken import supported_clients
from vkbottle import AiohttpClient
from vkbottle.api.api import API

from app import plugins
from app.config import settings
from app.vk.request_validators import VkLangRequestValidator


async def main() -> None:
    kate_user = API(
        token=settings.VK_KATE_TOKEN,
        http_client=AiohttpClient(
            session=ClientSession(
                headers={"User-agent": supported_clients.KATE.user_agent},
            ),
        ),
    )
    kate_user.request_validators.append(VkLangRequestValidator())

    client = TelegramClient(
        session=StringSession(settings.TGM_CLIENT_SESSION),
        api_id=settings.TGM_API_ID,
        api_hash=settings.TGM_API_HASH,
    )
    client.parse_mode = "html"
    await client.start(phone=lambda: settings.TGM_CLIENT_PHONE)

    bot = TelegramClient(
        session=StringSession(settings.TGM_BOT_SESSION),
        api_id=settings.TGM_API_ID,
        api_hash=settings.TGM_API_HASH,
    )
    bot.parse_mode = "html"
    await bot.start(bot_token=settings.TGM_BOT_TOKEN)

    async with client:
        await plugins.add_event_handlers(bot=bot, client=client, vk_api=kate_user)
        await bot.run_until_disconnected()
        await kate_user.http_client.close()


if __name__ == "__main__":
    logger.disable("vkbottle")
    asyncio.run(main())
