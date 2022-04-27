import asyncio
import importlib
import inspect
import logging
import os
import time

from telethon import events

from app.bot.plugins.common import NewMessageEvent, check_permission, check_state
from app.bot.state_manager import State
from app.config import _, settings

INCORRECT_LINK = (
    _("INCORRECT_LINK")
    + (
        ":\n"
        "\nvk.com/wall{owner_id}_{id}"
        "\nm.vk.com/wall{owner_id}_{id}"
        "\nhttps://vk.com/wall{owner_id}_{id}"
        "\nhttps://m.vk.com/wall{owner_id}_{id}"
    )
    + (
        "\nvk.com/music/album/{owner_id}_{id}"
        "\nvk.com/music/playlist/{owner_id}_{id}"
        "\nm.vk.com/audio?act=audio_playlist{owner_id}_{id}"
        "\nhttps://vk.com/music/album/{owner_id}_{id}"
        "\nhttps://vk.com/music/playlist/{owner_id}_{id}"
        "\nhttps://m.vk.com/audio?act=audio_playlist{owner_id}_{id}"
    )
    if settings.TGM_PL_CHANNEL_ID
    else ""
)

logger = logging.getLogger(__name__)


async def init(bot, client, vk_api):
    plugins = [
        # Dynamically import
        importlib.import_module(".", f"{__name__}.{file[:-3]}")
        # All the files in the current directory
        for file in os.listdir(os.path.dirname(__file__))
        # If they start with a letter and are Python files
        if file[0].isalpha() and file.endswith(".py")
    ]

    # Keep a mapping of module name to module for easy access inside the plugins
    modules = {m.__name__.split(".")[-1]: m for m in plugins}

    if not settings.TGM_PL_CHANNEL_ID:
        modules.pop("playlist", None)

    # All kwargs provided to get_init_args are those that plugins may access
    to_init = (get_init_coro(plugin, bot=bot, client=client, vk_api=vk_api, modules=modules) for plugin in plugins)

    # Plugins may not have a valid init so those need to be filtered out
    await asyncio.gather(*(filter(None, to_init)))

    @bot.on(events.NewMessage(func=lambda e: check_state(e, State.WAITING_FOR_LINK)))
    async def incorrect_link(event: NewMessageEvent):
        if not await check_permission(event):
            raise events.StopPropagation

        await event.respond(INCORRECT_LINK)
        raise events.StopPropagation


def get_init_coro(plugin, **kwargs):
    p_init = getattr(plugin, "init", None)
    if not callable(p_init):
        return

    result_kwargs = {}
    sig = inspect.signature(p_init)
    for param in sig.parameters:
        if param in kwargs:
            result_kwargs[param] = kwargs[param]
        else:
            logger.error("Plugin %s has unknown init parameter %s", plugin.__name__, param.__name__)
            return

    return _init_plugin(plugin, result_kwargs)


async def _init_plugin(plugin, kwargs):
    try:
        logger.warning(f"Loading plugin {plugin.__name__}…")
        start = time.time()
        await plugin.init(**kwargs)
        took = time.time() - start
        logger.warning(f"Loaded plugin {plugin.__name__} (took {took:.2f}s)")
    except Exception:
        logger.exception(f"Failed to load plugin {plugin}")
