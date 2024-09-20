import argparse
from pathlib import Path

from pydantic import ValidationError
from rich.prompt import Confirm

from app.config import Settings
from app.console import console
from app.settings_manager import SettingsManager
from app.vk import FloodControlError


class ArgNamespace(argparse.Namespace):
    env_file: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Helper to create or update .env file.")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file",
    )
    args = parser.parse_args(namespace=ArgNamespace)

    console.print(
        "[yellow]Note: sensitive information (e.g. passwords, tokens) won't be shown in prompts.",
        end="\n\n",
    )
    console.print("Loading values from '.env' file...")
    try:
        settings = Settings(_env_file=args.env_file)  # type: ignore[call-arg]
    except ValidationError as error:
        print(error)  # noqa: T201
        return 1

    settings_manager = SettingsManager(settings=settings)
    try:
        settings_manager.prompt_vk_auth()
        settings_manager.prompt_vk_community()
        settings_manager.prompt_tgm_user_auth()
        tgm_bot_auth = settings_manager.prompt_tgm_bot_auth()
        settings_manager.prompt_tgm_main_channel(tgm_bot_auth=tgm_bot_auth)

        console.rule()
        has_pl_tgm = Confirm.ask(
            prompt=("Do you want to forward audio playlists? Additional Telegram channel required"),
        )
        if has_pl_tgm:
            settings_manager.prompt_tgm_playlist_channel(tgm_bot_auth=tgm_bot_auth)

        settings_manager.prompt_vtt_options()
    except (KeyboardInterrupt, FloodControlError):
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
        sys.exit(main())
