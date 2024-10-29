from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from aiohttp import ClientResponse, hdrs
from aioresponses import aioresponses
from loguru import logger
from pytest_celery import CeleryBackendCluster, CeleryBrokerCluster

from app.logging import format_record

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from re import Pattern
    from typing import Any

    from _pytest.logging import LogCaptureFixture
    from pytest_celery import RedisTestBackend, RedisTestBroker
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


@pytest.fixture
def caplog(caplog: LogCaptureFixture) -> Generator[LogCaptureFixture, None, None]:
    handler_id = logger.add(caplog.handler, format=format_record)
    yield caplog
    logger.remove(handler_id)


@pytest.fixture
def celery_broker_cluster(celery_redis_broker: RedisTestBroker) -> Generator[CeleryBrokerCluster, None, None]:
    cluster = CeleryBrokerCluster(celery_redis_broker)
    yield cluster
    cluster.teardown()


@pytest.fixture
def celery_backend_cluster(celery_redis_backend: RedisTestBackend) -> Generator[CeleryBackendCluster, None, None]:
    cluster = CeleryBackendCluster(celery_redis_backend)
    yield cluster
    cluster.teardown()
