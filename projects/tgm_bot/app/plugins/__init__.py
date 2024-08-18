from telethon import TelegramClient
from vkbottle import API

from app.config import settings
from app.plugins import common, playlist, wall


async def add_event_handlers(bot: TelegramClient, client: TelegramClient, vk_api: API) -> None:
    await common.add_initial_event_handlers(bot=bot)

    await wall.add_event_handlers(bot=bot, client=client, vk_api=vk_api)

    if settings.TGM_PL_CHANNEL_ID:
        await playlist.add_event_handlers(bot=bot, client=client, vk_api=vk_api)

    await common.add_last_event_handlers(bot=bot)
