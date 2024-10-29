from __future__ import annotations

import asyncio
import warnings
from typing import TYPE_CHECKING

from loguru import logger

with warnings.catch_warnings(record=True, action="ignore", category=DeprecationWarning):
    from vkbottle.api.api import API

from vkbottle.http import AiohttpClient
from vkbottle_types import API_VERSION
from vkbottle_types.methods.groups import GroupsCategory

from app.config import get_settings

if TYPE_CHECKING:
    from app.config import Settings


async def setup_vk_server(settings: Settings | None = None) -> str:
    if not settings:  # pragma: no cover
        settings = get_settings()

    logger.info("Setting up callback server...")
    vk_group = GroupsCategory(
        API(
            token=settings.VK_COMMUNITY_TOKEN,
            http_client=AiohttpClient(),
        ),
    )

    group_id = settings.VK_COMMUNITY_ID
    server_url = settings.SERVER_URL
    server_title = settings.VK_SERVER_TITLE

    confirmation = await vk_group.get_callback_confirmation_code(group_id=group_id)
    confirmation_code: str = confirmation.code
    logger.info(f"Callback confirmation code: {confirmation_code}")

    server_id: int | None = None
    secret_key = settings.VK_SERVER_SECRET

    servers = await vk_group.get_callback_servers(group_id=group_id)
    if not servers.items:
        new_server = await vk_group.add_callback_server(
            group_id=group_id,
            url=server_url,
            title=server_title,
            secret_key=secret_key,
        )
        server_id = new_server.server_id
        logger.info(f"Added new callback server '{server_title}'")
    else:
        main_server = next(filter(lambda server: server.title == server_title, servers.items), None)
        if main_server:
            await vk_group.edit_callback_server(
                group_id=group_id,
                server_id=main_server.id,
                url=server_url,
                title=main_server.title,
                secret_key=secret_key,
            )
            server_id = main_server.id
            logger.info(f"Using existing callback server '{main_server.title}'")
        else:
            new_server = await vk_group.add_callback_server(
                group_id=group_id,
                url=server_url,
                title=server_title,
                secret_key=secret_key,
            )
            server_id = new_server.server_id
            logger.info(f"No callback server found by title '{server_title}', added new.")

    task = asyncio.create_task(
        vk_group.set_callback_settings(
            group_id=group_id,
            server_id=server_id,
            api_version=API_VERSION,
            wall_post_new=True,
        ),
    )
    task.add_done_callback(lambda _: logger.info("Callback server settings has been set."))

    return confirmation_code
