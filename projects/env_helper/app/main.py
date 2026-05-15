import argparse
from pathlib import Path

import questionary
import uvloop
from pydantic import ValidationError

from app.config import Settings
from app.console import console
from app.settings_manager import SettingsManager
from app.vk import FloodControlError


class ArgNamespace(argparse.Namespace):
    env_file: str


async def main(arg_list: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Helper to create or update .env file.")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file",
    )
    args = parser.parse_args(arg_list, namespace=ArgNamespace)

    console.print("Loading values from '.env' file...")
    try:
        settings = Settings(_env_file=args.env_file)
    except ValidationError as error:
        print(error)  # noqa: T201
        return 1

    settings_manager = SettingsManager(settings=settings)
    try:
        await settings_manager.prompt_vk_auth()
        await settings_manager.prompt_vk_community()
        await settings_manager.prompt_tgm_user_auth()
        tgm_bot_auth = await settings_manager.prompt_tgm_bot_auth()
        await settings_manager.prompt_tgm_main_channel(tgm_bot_auth=tgm_bot_auth)

        console.rule()

        has_pl_tgm = await questionary.confirm(
            "Do you want to forward audio playlists? Additional Telegram channel required",
        ).unsafe_ask_async()
        if has_pl_tgm:
            await settings_manager.prompt_tgm_playlist_channel(tgm_bot_auth=tgm_bot_auth)

        await settings_manager.prompt_vtt_options()

        use_ssl = await questionary.confirm(
            "Do you want to use SSL? Domain name for your server is required",
        ).unsafe_ask_async()
        if use_ssl:
            await settings_manager.prompt_vtt_ssl()
    except KeyboardInterrupt, FloodControlError:
        console.print("\nInterrupted...")

    console.rule()

    console.print("Saving to '.env' file...")
    settings_manager.save_env(env_file=Path(args.env_file))

    console.print("Done.")
    return 0


if __name__ == "__main__":
    import sys

    from loguru import logger

    logger.disable("vkbottle")

    with logger.catch(onerror=lambda _: sys.exit(1)):
        sys.exit(uvloop.run(main()))
