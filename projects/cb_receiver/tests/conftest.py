from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from loguru import logger
from pytest_celery import CeleryBackendCluster, CeleryBrokerCluster
from pytest_mock import MockerFixture

from app.logging import format_record

if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.logging import LogCaptureFixture
    from pytest_celery import RedisTestBackend, RedisTestBroker
    from pytest_mock import MockerFixture


class VkMock:
    def __init__(self) -> None:
        self._responses: dict[str, Any] = {}

    def post(self, method: str, payload: Any) -> None:  # noqa: ANN401
        self._responses[method] = payload


@pytest.fixture
def mock_vk(mocker: MockerFixture) -> VkMock:
    mock = VkMock()

    async def handler(
        method: str,
        params: dict[str, Any] | None = None,  # noqa: ARG001
        *,
        data: dict[str, Any] | None = None,  # noqa: ARG001
    ) -> object:
        if method not in mock._responses:
            msg = f"No mock registered for VK API method: {method}"
            raise RuntimeError(msg)
        return mock._responses[method]

    mocker.patch("app.utils._vk_api_request", side_effect=handler)

    return mock


@pytest.fixture
def caplog(caplog: LogCaptureFixture) -> Generator[LogCaptureFixture]:
    handler_id = logger.add(caplog.handler, format=format_record)
    yield caplog
    logger.remove(handler_id)


@pytest.fixture
def celery_broker_cluster(celery_redis_broker: RedisTestBroker) -> Generator[CeleryBrokerCluster]:
    cluster = CeleryBrokerCluster(celery_redis_broker)
    yield cluster
    cluster.teardown()


@pytest.fixture
def celery_backend_cluster(celery_redis_backend: RedisTestBackend) -> Generator[CeleryBackendCluster]:
    cluster = CeleryBackendCluster(celery_redis_backend)
    yield cluster
    cluster.teardown()
