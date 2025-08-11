from __future__ import annotations

from typing import TYPE_CHECKING

from dotenv import set_key

from app.tgm import BotAuth, MainChannel, PlaylistChannel, UserAuth
from app.vk import Community, KateAuth
from app.vtt import SSL, Options

if TYPE_CHECKING:
    from pathlib import Path

    from app.config import Settings


class SettingsManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def _update_tgm_bot_session(self, tgm_bot_auth: BotAuth) -> None:
        await tgm_bot_auth.update_session()

        self.settings.TGM_BOT_SESSION = tgm_bot_auth.session

    async def prompt_vk_auth(self) -> None:
        vk_kate_auth = KateAuth(token=self.settings.VK_KATE_TOKEN)
        await vk_kate_auth.prompt_all()

        self.settings.VK_KATE_TOKEN = vk_kate_auth.token

    async def prompt_vk_community(self) -> None:
        vk_community = Community(
            community_id=self.settings.VK_COMMUNITY_ID,
            community_token=self.settings.VK_COMMUNITY_TOKEN,
            server_title=self.settings.VK_SERVER_TITLE,
            server_url=self.settings.SERVER_URL,
        )
        await vk_community.prompt_all()

        self.settings.VK_COMMUNITY_TOKEN = vk_community.community_token
        self.settings.VK_COMMUNITY_ID = vk_community.community_id
        self.settings.SERVER_URL = vk_community.server_url
        self.settings.VK_SERVER_TITLE = vk_community.server_title

    async def prompt_tgm_bot_auth(self) -> BotAuth:
        tgm_bot_auth = BotAuth(
            api_id=self.settings.TGM_API_ID,
            api_hash=self.settings.TGM_API_HASH,
            access_token=self.settings.TGM_BOT_TOKEN,
            session=self.settings.TGM_BOT_SESSION,
        )
        await tgm_bot_auth.prompt_all()

        self.settings.TGM_API_ID = tgm_bot_auth.api_id
        self.settings.TGM_API_HASH = tgm_bot_auth.api_hash
        self.settings.TGM_BOT_TOKEN = tgm_bot_auth.access_token
        self.settings.TGM_BOT_SESSION = tgm_bot_auth.session

        return tgm_bot_auth

    async def prompt_tgm_user_auth(self) -> None:
        tgm_user_auth = UserAuth(
            api_id=self.settings.TGM_API_ID,
            api_hash=self.settings.TGM_API_HASH,
            access_token=self.settings.TGM_CLIENT_PHONE,
            session=self.settings.TGM_CLIENT_SESSION,
        )
        await tgm_user_auth.prompt_all()

        self.settings.TGM_API_ID = tgm_user_auth.api_id
        self.settings.TGM_API_HASH = tgm_user_auth.api_hash
        self.settings.TGM_CLIENT_PHONE = tgm_user_auth.access_token
        self.settings.TGM_CLIENT_SESSION = tgm_user_auth.session

    async def prompt_tgm_main_channel(self, tgm_bot_auth: BotAuth) -> None:
        tgm_main_channel = MainChannel(
            client=tgm_bot_auth.client,
            name=self.settings.TGM_CHANNEL_USERNAME,
            channel_id=self.settings.TGM_CHANNEL_ID,
        )
        await tgm_main_channel.prompt_all()

        await self._update_tgm_bot_session(tgm_bot_auth=tgm_bot_auth)

        self.settings.TGM_CHANNEL_USERNAME = tgm_main_channel.name
        self.settings.TGM_CHANNEL_ID = tgm_main_channel.channel_id

    async def prompt_tgm_playlist_channel(self, tgm_bot_auth: BotAuth) -> None:
        tgm_playlist_channel = PlaylistChannel(
            client=tgm_bot_auth.client,
            name=self.settings.TGM_CHANNEL_USERNAME,
            channel_id=self.settings.TGM_CHANNEL_ID,
        )
        await tgm_playlist_channel.prompt_all()

        await self._update_tgm_bot_session(tgm_bot_auth=tgm_bot_auth)

        self.settings.TGM_PL_CHANNEL_USERNAME = tgm_playlist_channel.name
        self.settings.TGM_PL_CHANNEL_ID = tgm_playlist_channel.channel_id

    async def prompt_vtt_options(self) -> None:
        vtt_options = Options(
            ignore_ads=self.settings.VTT_IGNORE_ADS,
            language=self.settings.VTT_LANGUAGE,
        )
        await vtt_options.prompt_all()

        self.settings.VTT_IGNORE_ADS = vtt_options.ignore_ads
        self.settings.VTT_LANGUAGE = vtt_options.language

    async def prompt_vtt_ssl(self) -> None:
        vtt_ssl = SSL(
            server_name=self.settings.NGINX_SERVER_NAME,
            https_port=self.settings.NGINX_HTTPS_PORT,
            ssl_email=self.settings.SSL_EMAIL,
        )
        await vtt_ssl.prompt_all()

        self.settings.NGINX_SERVER_NAME = vtt_ssl.server_name
        self.settings.NGINX_HTTPS_PORT = vtt_ssl.https_port
        self.settings.SSL_EMAIL = vtt_ssl.ssl_email

    def save_env(self, env_file: Path) -> None:
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.touch(exist_ok=True)

        for field in sorted(self.settings.model_fields_set):
            set_key(
                dotenv_path=env_file,
                key_to_set=field,
                value_to_set=str(getattr(self.settings, field)),
            )
