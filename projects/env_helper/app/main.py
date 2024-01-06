from dotenv import set_key
from pydantic import ValidationError
from rich.prompt import Confirm

from app.config import Settings
from app.console import console
from app.tgm import BotAuth, MainChannel, PlaylistChannel, UserAuth
from app.vk import Community, FloodControlError, KateAuth, OfficialAuth
from app.vtt import Options


def main() -> int:  # noqa: C901
    vk_kate_auth = None
    vk_official_auth = None
    vk_community = None
    tgm_bot_auth = None
    tgm_user_auth = None
    tgm_main_channel = None
    tgm_playlist_channel = None
    vtt_options = None

    console.print(
        "[yellow]Note: sensitive information (e.g. passwords, tokens) "
        "won't be shown in prompts.",
        end="\n\n",
    )
    console.print("Loading values from '.env' file...")
    try:
        settings = Settings()
    except ValidationError as error:
        print(error)  # noqa: T201
        return 1

    try:
        vk_kate_auth = KateAuth(
            token=settings.VK_KATE_TOKEN,
        )
        vk_kate_auth.prompt_all()

        vk_official_auth = OfficialAuth(
            token=settings.VK_OFFICIAL_TOKEN,
            login=vk_kate_auth.login,
            password=vk_kate_auth.password,
        )
        vk_official_auth.prompt_all()

        vk_community = Community(
            community_id=settings.VK_COMMUNITY_ID,
            community_token=settings.VK_COMMUNITY_TOKEN,
            server_title=settings.VK_SERVER_TITLE,
            server_url=settings.SERVER_URL,
        )
        vk_community.prompt_all()

        tgm_bot_auth = BotAuth(
            api_id=settings.TGM_API_ID,
            api_hash=settings.TGM_API_HASH,
            access_token=settings.TGM_BOT_TOKEN,
            session=settings.TGM_BOT_SESSION,
        )
        tgm_bot_auth.prompt_all()

        tgm_user_auth = UserAuth(
            api_id=tgm_bot_auth.api_id,
            api_hash=tgm_bot_auth.api_hash,
            access_token=settings.TGM_CLIENT_PHONE,
            session=settings.TGM_CLIENT_SESSION,
        )
        tgm_user_auth.prompt_all()

        bot_client = tgm_bot_auth.client

        tgm_main_channel = MainChannel(
            client=bot_client,
            name=settings.TGM_CHANNEL_USERNAME,
            channel_id=settings.TGM_CHANNEL_ID,
        )
        tgm_main_channel.prompt_all()

        tgm_bot_auth.update_session()

        console.rule()

        has_pl_tgm = Confirm.ask(
            prompt=(
                "Do you want to forward audio playlists? "
                "Additional Telegram channel required"
            ),
        )
        if has_pl_tgm:
            tgm_playlist_channel = PlaylistChannel(
                client=bot_client,
                name=settings.TGM_CHANNEL_USERNAME,
                channel_id=settings.TGM_CHANNEL_ID,
            )
            tgm_playlist_channel.prompt_all()

            tgm_bot_auth.update_session()

        vtt_options = Options(
            ignore_ads=settings.VTT_IGNORE_ADS,
            language=settings.VTT_LANGUAGE,
        )
        vtt_options.prompt_all()

    except (KeyboardInterrupt, FloodControlError):
        console.print("\nInterrupted...")

    console.rule()
    console.print("Saving to '.env' file...")

    if vk_kate_auth:
        settings.VK_KATE_TOKEN = vk_kate_auth.token
    if vk_official_auth:
        settings.VK_OFFICIAL_TOKEN = vk_official_auth.token
    if vk_community:
        settings.VK_COMMUNITY_TOKEN = vk_community.community_token
        settings.VK_COMMUNITY_ID = vk_community.community_id
        settings.SERVER_URL = vk_community.server_url
        settings.VK_SERVER_TITLE = vk_community.server_title
    if tgm_bot_auth:
        settings.TGM_API_ID = tgm_bot_auth.api_id
        settings.TGM_API_HASH = tgm_bot_auth.api_hash
        settings.TGM_BOT_TOKEN = tgm_bot_auth.access_token
        settings.TGM_BOT_SESSION = tgm_bot_auth.session
    if tgm_user_auth:
        settings.TGM_CLIENT_PHONE = tgm_user_auth.access_token
        settings.TGM_CLIENT_SESSION = tgm_user_auth.session
    if tgm_main_channel:
        settings.TGM_CHANNEL_USERNAME = tgm_main_channel.name
        settings.TGM_CHANNEL_ID = tgm_main_channel.channel_id
    if tgm_playlist_channel:
        settings.TGM_PL_CHANNEL_USERNAME = tgm_playlist_channel.name
        settings.TGM_PL_CHANNEL_ID = tgm_playlist_channel.channel_id
    if vtt_options:
        settings.VTT_IGNORE_ADS = vtt_options.ignore_ads
        settings.VTT_LANGUAGE = vtt_options.language

    for field in sorted(settings.__fields_set__):
        set_key(
            dotenv_path=".env",
            key_to_set=field,
            value_to_set=str(getattr(settings, field)),
        )

    console.print("Done.")
    return 0


if __name__ == "__main__":
    import sys

    from loguru import logger

    logger.disable("vkbottle")

    with logger.catch(onerror=lambda _: sys.exit(1)):
        sys.exit(main())
