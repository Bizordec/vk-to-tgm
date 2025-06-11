import argparse

from loguru import logger
from pydantic import ValidationError

from app.config import Settings


class ArgNamespace(argparse.Namespace):
    env_file: str


def main(arg_list: list[str] | None = None) -> int:
    logger.info("Checking settings...")
    parser = argparse.ArgumentParser(description="Helper to create or update .env file.")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file",
    )
    args = parser.parse_args(arg_list, namespace=ArgNamespace)
    try:
        Settings(_env_file=args.env_file)
    except ValidationError as error:
        logger.error(error)
        return 1
    logger.info("Settings are valid.")
    return 0


if __name__ == "__main__":
    import sys

    logger.disable("vkbottle")

    with logger.catch(onerror=lambda _: sys.exit(1)):
        sys.exit(main())
