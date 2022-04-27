import asyncio
import logging
import sys

from telethon.client.telegramclient import TelegramClient

from app.config import settings
from app.utils.telegram import get_entity_by_id

logger = logging.getLogger("app.sign_in")


async def get_channel_entities(client: TelegramClient):
    logger.info("Getting main channel entity...")
    entity = await get_entity_by_id(
        client,
        settings.TGM_CHANNEL_ID,
    )
    if not entity:
        sys.exit(1)

    if settings.TGM_PL_CHANNEL_ID:
        logger.info("Getting playlist channel entity...")
        entity = await get_entity_by_id(
            client,
            settings.TGM_PL_CHANNEL_ID,
        )
        if not entity:
            sys.exit(1)


async def main():
    logger.info("Signing into Telegram...")
    tgm_search_client = TelegramClient("tgm_search_client", settings.TGM_API_ID, settings.TGM_API_HASH)
    await tgm_search_client.start(phone=lambda: settings.TGM_CLIENT_PHONE)
    await get_channel_entities(tgm_search_client)
    await tgm_search_client.disconnect()

    tgm_bot = TelegramClient("tgm_bot", settings.TGM_API_ID, settings.TGM_API_HASH)
    await tgm_bot.start(bot_token=settings.TGM_BOT_TOKEN)
    await get_channel_entities(tgm_bot)
    await tgm_bot.disconnect()

    worker_bot = TelegramClient("worker_bot", settings.TGM_API_ID, settings.TGM_API_HASH)
    await worker_bot.start(bot_token=settings.TGM_BOT_TOKEN)
    await get_channel_entities(worker_bot)
    await worker_bot.disconnect()

    if settings.TGM_PL_CHANNEL_ID:
        worker_pl_bot = TelegramClient("worker_pl_bot", settings.TGM_API_ID, settings.TGM_API_HASH)
        await worker_pl_bot.start(bot_token=settings.TGM_BOT_TOKEN)
        await get_channel_entities(worker_pl_bot)
        await worker_pl_bot.disconnect()

    logger.info("Done.")


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s: %(asctime)s [%(name)s] %(message)s", level=logging.INFO, force=True)
    asyncio.run(main())
