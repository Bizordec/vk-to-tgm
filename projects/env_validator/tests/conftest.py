from __future__ import annotations

from typing import TYPE_CHECKING

import pytest_asyncio
from aiointercept import aiointercept

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest_asyncio.fixture
async def mock_http(socket_enabled: None) -> AsyncGenerator[aiointercept]:  # noqa: ARG001
    async with aiointercept(mock_external_urls=True) as m:
        yield m
