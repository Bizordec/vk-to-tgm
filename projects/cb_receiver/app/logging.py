from __future__ import annotations

import inspect
import logging
import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Record


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)


def format_record(record: Record) -> str:
    message = ""
    if record["extra"].get("event_id") is not None:
        message += "[{extra[event_id]}] "
    if record["extra"].get("full_id") is not None:
        message += "[{extra[full_id]}] "
    message += "{message}"

    format_string = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        f"<level>{message}</level>"
    )

    format_string += "{exception}\n"
    return format_string


def init_logging() -> None:
    logger.disable("vkbottle")
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    loggers = (logging.getLogger(name) for name in logging.root.manager.loggerDict if name.startswith("uvicorn."))
    for uvicorn_logger in loggers:
        uvicorn_logger.handlers = []

    intercept_handler = InterceptHandler()
    logging.getLogger("uvicorn").handlers = [intercept_handler]

    logger.configure(handlers=[{"sink": sys.stdout, "level": logging.DEBUG, "format": format_record}])
