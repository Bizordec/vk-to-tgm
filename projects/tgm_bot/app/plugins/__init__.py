from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from app.config import settings
from app.plugins import common, playlist, wall

if TYPE_CHECKING:
    from telethon import TelegramClient
    from vkbottle import API


async def add_event_handlers(bot: TelegramClient, client: TelegramClient, vk_api: API) -> None:
    logger.info("Registering event handlers...")
    await common.add_initial_event_handlers(bot=bot)

    logger.info("Registering wall post event handlers")
    await wall.add_event_handlers(bot=bot, client=client, vk_api=vk_api)

    if settings.TGM_PL_CHANNEL_ID:
        logger.info("Registering playlist event handlers")
        await playlist.add_event_handlers(bot=bot, client=client, vk_api=vk_api)
    else:
        logger.info("Skipping playlist event handlers (TGM_PL_CHANNEL_ID not set)")

    logger.info("Registering fallback event handlers")
    await common.add_last_event_handlers(bot=bot)
