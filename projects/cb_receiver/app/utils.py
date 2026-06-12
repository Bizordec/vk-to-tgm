from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from loguru import logger

from app.config import get_settings

if TYPE_CHECKING:
    from typing import Any

    from app.config import Settings
    from app.schemas import (
        AddCallbackServerResponse,
        GetCallbackServersResponse,
        GetConfirmationCodeResponse,
    )


async def _vk_api_request(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    request_params = dict(params or {})
    request_params["access_token"] = settings.VK_COMMUNITY_TOKEN
    request_params["v"] = "5.199"

    if data:
        request_params.update(data)

    encoded = urlencode(request_params).encode()

    def _request() -> dict[str, Any]:
        try:
            with urlopen(f"https://api.vk.ru/method/{method}", data=encoded) as resp:
                result: dict[str, Any] = json.loads(resp.read())
        except HTTPError as e:
            msg = f"VK API HTTP error {e.code}: {e.reason}"
            raise RuntimeError(msg) from e
        except URLError as e:
            msg = f"VK API connection error: {e.reason}"
            raise RuntimeError(msg) from e
        except json.JSONDecodeError as e:
            msg = f"VK API invalid JSON response: {e}"
            raise RuntimeError(msg) from e

        error = cast("dict[str, Any] | None", result.get("error"))
        if error:
            msg = error.get("error_msg", str(error))
            raise RuntimeError(f"VK API error: {msg}")

        try:
            return cast("dict[str, Any]", result["response"])
        except KeyError:
            raise RuntimeError(f"VK API response missing 'response' key: {result}") from None

    return await asyncio.to_thread(_request)


async def _find_or_create_server(
    group_id: int,
    server_url: str,
    server_title: str,
    secret_key: str,
) -> int:
    servers = cast(
        "GetCallbackServersResponse",
        await _vk_api_request("groups.getCallbackServers", {"group_id": group_id}),
    )

    items = servers["items"]
    main_server = next(
        filter(lambda server: server["title"] == server_title, items),
        None,
    )

    if main_server:
        server_id = main_server["id"]
        await _vk_api_request(
            "groups.editCallbackServer",
            data={
                "group_id": group_id,
                "server_id": server_id,
                "url": server_url,
                "title": server_title,
                "secret_key": secret_key,
            },
        )
        logger.info(f"Using existing callback server '{server_title}'")
        return server_id

    new_server = cast(
        "AddCallbackServerResponse",
        await _vk_api_request(
            "groups.addCallbackServer",
            data={
                "group_id": group_id,
                "url": server_url,
                "title": server_title,
                "secret_key": secret_key,
            },
        ),
    )
    server_id = new_server["server_id"]

    if items:
        logger.info(f"No callback server found by title '{server_title}', added new.")
    else:
        logger.info(f"Added new callback server '{server_title}'")

    return server_id


async def get_confirmation_code(group_id: int) -> str:
    confirmation = cast(
        "GetConfirmationCodeResponse",
        await _vk_api_request(
            "groups.getCallbackConfirmationCode",
            {"group_id": group_id},
        ),
    )
    code = confirmation["code"]
    logger.info(f"Callback confirmation code: {code}")
    return code


async def _set_callback_settings(group_id: int, server_id: int) -> None:
    await _vk_api_request(
        "groups.setCallbackSettings",
        data={
            "group_id": group_id,
            "server_id": server_id,
            "api_version": "5.199",
            "wall_post_new": 1,
        },
    )
    logger.info("Callback server settings has been set.")


async def configure_callback_server(settings: Settings | None = None) -> None:
    if not settings:
        settings = get_settings()

    logger.info("Setting up callback server...")

    group_id = settings.VK_COMMUNITY_ID

    server_id = await _find_or_create_server(
        group_id=group_id,
        server_url=settings.SERVER_URL,
        server_title=settings.VK_SERVER_TITLE,
        secret_key=settings.VK_SERVER_SECRET,
    )

    await _set_callback_settings(
        group_id=group_id,
        server_id=server_id,
    )
