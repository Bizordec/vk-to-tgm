from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from celery.app.task import Context
from fastapi.testclient import TestClient

from app.main import create_app
from tests.utils import get_settings_override

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from celery.backends.redis import RedisBackend
    from pytest_celery import CeleryTestSetup

pytestmark = pytest.mark.allow_hosts(["127.0.0.1", "::1"])


def test_new_wall_post(celery_setup: CeleryTestSetup) -> None:
    assert celery_setup.ready()

    celery_app = celery_setup.app
    client = TestClient(
        app=create_app(
            settings=get_settings_override(),
            celery_app=celery_app,
        ),
    )

    response = client.post(
        "/",
        json={
            "type": "wall_post_new",
            "event_id": "123",
            "group_id": 123456,
            "v": "5.199",
            "secret": "vk-server-secret",
            "object": {
                "inner_type": "wall_wallpost",
                "owner_id": 1234,
                "id": 111,
                "post_type": "post",
            },
        },
    )

    assert response.status_code == 200
    assert response.text == "ok"

    backend: RedisBackend = celery_app.backend
    result = backend.get(backend.get_key_for_task("wall_1234_111"))
    assert result
    assert backend.decode_result(result) == {
        "task_id": "wall_1234_111",
        "result": None,
        "status": "SENT",
        "traceback": None,
        "children": [],
        "date_done": None,
    }


def test_skip_wall_post(celery_setup: CeleryTestSetup, caplog: LogCaptureFixture) -> None:
    assert celery_setup.ready()

    celery_app = celery_setup.app
    celery_app.backend.store_result(
        task_id="wall_1234_111",
        result=None,
        state="SENT",
        request=Context(
            task="app.main.forward_wall",
            args=(),
            kwargs={"owner_id": 1234, "wall_id": 111},
            delivery_info={
                "routing_key": "vtt-wall",
            },
        ),
    )
    client = TestClient(
        app=create_app(
            settings=get_settings_override(),
            celery_app=celery_app,
        ),
    )

    response = client.post(
        "/",
        json={
            "type": "wall_post_new",
            "event_id": "123",
            "group_id": 123456,
            "v": "5.199",
            "secret": "vk-server-secret",
            "object": {
                "inner_type": "wall_wallpost",
                "owner_id": 1234,
                "id": 111,
                "post_type": "post",
            },
        },
    )

    assert response.status_code == 200
    assert response.text == "ok"

    assert "Post already exists" in caplog.text
