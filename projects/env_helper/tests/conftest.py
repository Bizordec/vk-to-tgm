from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from aiohttp import ClientResponse, hdrs
from aioresponses import aioresponses

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from re import Pattern
    from typing import Any

    from yarl import URL


class VkMockClient(aioresponses):
    def add(
        self,
        url: URL | str | Pattern[str],
        method: str = hdrs.METH_GET,
        status: int = 200,
        body: str | bytes = "",
        exception: Exception | None = None,
        content_type: str = "application/json",
        payload: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        response_class: type[ClientResponse] | None = None,
        repeat: bool = False,  # noqa: FBT002
        timeout: bool = False,  # noqa: FBT002
        reason: str | None = None,
        callback: Callable[..., Any] | None = None,
    ) -> None:
        url = f"https://api.vk.com/method/{url}?access_token=vk-community-token&v=5.199"
        if payload is not None:
            payload = {"response": payload}

        return super().add(
            url,
            method,
            status,
            body,
            exception,
            content_type,
            payload,
            headers,
            response_class,
            repeat,
            timeout,
            reason,
            callback,
        )


@pytest.fixture
def mock_vk() -> Generator[aioresponses, None, None]:
    with VkMockClient() as m:
        yield m
