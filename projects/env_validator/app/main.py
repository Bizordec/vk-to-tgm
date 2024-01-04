from loguru import logger
from pydantic import ValidationError

from app.config import Settings


def main() -> int:
    logger.info("Checking settings...")
    try:
        Settings()
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
