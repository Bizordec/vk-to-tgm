from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession
from vkbottle import API
from vkbottle.http import AiohttpClient
from vtt_common.proxy import get_tgm_proxy_config

from app.config import settings
from app.decorators import async_to_sync
from app.exceptions import VttError
from app.services.tgm import TelegramPlaylistSender, TelegramWallSender
from app.services.vk import VkService
from app.vk.request_validators import VkLangRequestValidator
from app.vtt.factories.message import VttMessageFactory
from app.vtt.factories.playlist import VttPlaylistFactory
from app.worker import worker

logger.disable("vkbottle")


@worker.task()  # type: ignore[untyped-decorator]
@async_to_sync
async def forward_wall(owner_id: int, wall_id: int) -> str:
    with logger.contextualize(owner_id=owner_id, wall_id=wall_id):
        logger.info(f"New VK wall post received: 'https://vk.ru/wall{owner_id}_{wall_id}'")

        vk_api = API(token=settings.VK_TOKEN, http_client=AiohttpClient())
        vk_api.request_validators.append(VkLangRequestValidator())

        vk_service = VkService(vk_api=vk_api)

        vtt_factory = VttMessageFactory(vk_service=vk_service)
        vtt_message = await vtt_factory.create(owner_id=owner_id, wall_id=wall_id)

        if isinstance(vtt_message, str):
            logger.warning(f"Post was not sent to Telegram. Reason: '{vtt_message}'")
            return vtt_message

        tgm_bot = TelegramClient(
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
        tgm_bot.parse_mode = "html"

        async with await tgm_bot.start(bot_token=settings.TGM_BOT_TOKEN):
            tgm_service = TelegramWallSender(
                tgm_client=tgm_bot,
                vk_service=vk_service,
                channel_id=settings.TGM_CHANNEL_ID,
            )
            try:
                return await tgm_service.send_vtt_message(vtt_message=vtt_message)
            except VttError as error:
                error_msg = error.message
                logger.warning(f"Post was not sent to Telegram. Reason: '{error_msg}'")
                return error_msg


@worker.task()  # type: ignore[untyped-decorator]
@async_to_sync
async def forward_playlist(
    *,
    owner_id: int,
    playlist_id: int,
    access_key: str | None = None,
    reply_channel_id: int | None = None,
    reply_message_id: int | None = None,
) -> str:
    with logger.contextualize(
        owner_id=owner_id,
        playlist_id=playlist_id,
        access_key=access_key,
        reply_channel_id=reply_channel_id,
        reply_message_id=reply_message_id,
    ):
        pl_url = f"https://vk.ru/music/playlist/{owner_id}_{playlist_id}{'_' + access_key if access_key else ''}"
        logger.info(f"New VK playlist received: '{pl_url}'")

        vk_api = API(token=settings.VK_TOKEN, http_client=AiohttpClient())
        vk_api.request_validators.append(VkLangRequestValidator())

        vk_service = VkService(vk_api=vk_api)

        vtt_factory = VttPlaylistFactory(vk_service=vk_service)
        vtt_playlist = await vtt_factory.create(
            owner_id=owner_id,
            playlist_id=playlist_id,
            access_key=access_key,
            with_audios=True,
        )
        if not vtt_playlist:
            return "NOT_FOUND"

        tgm_bot = TelegramClient(
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
        tgm_bot.parse_mode = "html"

        async with await tgm_bot.start(bot_token=settings.TGM_BOT_TOKEN):
            tgm_service = TelegramPlaylistSender(
                tgm_client=tgm_bot,
                vk_service=vk_service,
                pl_channel_id=settings.TGM_PL_CHANNEL_ID,
                wall_channel_id=reply_channel_id,
                wall_message_id=reply_message_id,
            )
            return await tgm_service.send_vtt_playlist(vtt_playlist=vtt_playlist)
