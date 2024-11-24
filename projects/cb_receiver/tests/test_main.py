from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.utils import setup_vk_server
from tests.utils import get_settings_override

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from aioresponses import aioresponses
    from pytest_mock import MockerFixture


app = create_app(settings=get_settings_override())

client = TestClient(app)


def test_missing_body() -> None:
    response = client.post("/")

    assert response.status_code == 422, response.text


def test_body_without_secret() -> None:
    response = client.post(
        "/",
        json={
            "type": "confirmation",
            "event_id": "123",
            "group_id": 123456,
            "v": "5.199",
            "object": {},
        },
    )

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_create_new_vk_server(mock_vk: aioresponses, caplog: LogCaptureFixture) -> None:
    mock_vk.post(
        "groups.getCallbackConfirmationCode",
        payload={"code": "test_code"},
    )
    mock_vk.post(
        "groups.getCallbackServers",
        payload={"count": 0, "items": []},
    )
    mock_vk.post(
        "groups.addCallbackServer",
        payload={"server_id": 1},
    )

    confirmation_code = await setup_vk_server(settings=get_settings_override())

    assert confirmation_code == "test_code"
    assert "Added new callback server 'vk-to-tgm'" in caplog.text


@pytest.mark.asyncio
async def test_use_existing_vk_server(mock_vk: aioresponses, caplog: LogCaptureFixture) -> None:
    mock_vk.post(
        "groups.getCallbackConfirmationCode",
        payload={"code": "test_code"},
    )
    mock_vk.post(
        "groups.getCallbackServers",
        payload={
            "count": 1,
            "items": [
                {
                    "id": 1,
                    "title": "vk-to-tgm",
                    "creator_id": 123,
                    "url": "https://example.com",
                    "secret_key": "vk-server-secret",
                    "status": "ok",
                },
            ],
        },
    )
    mock_vk.post("groups.editCallbackServer", payload=1)

    confirmation_code = await setup_vk_server(settings=get_settings_override())

    assert confirmation_code == "test_code"
    assert "Using existing callback server 'vk-to-tgm'" in caplog.text


@pytest.mark.asyncio
async def test_create_new_vk_server_if_not_found_by_title(mock_vk: aioresponses, caplog: LogCaptureFixture) -> None:
    mock_vk.post(
        "groups.getCallbackConfirmationCode",
        payload={"code": "test_code"},
    )
    mock_vk.post(
        "groups.getCallbackServers",
        payload={
            "count": 1,
            "items": [
                {
                    "id": 1,
                    "title": "test-server",
                    "creator_id": 123,
                    "url": "https://example.com",
                    "secret_key": "vk-server-secret",
                    "status": "ok",
                },
            ],
        },
    )
    mock_vk.post(
        "groups.addCallbackServer",
        payload={"server_id": 2},
    )

    confirmation_code = await setup_vk_server(settings=get_settings_override())

    assert confirmation_code == "test_code"
    assert "No callback server found by title 'vk-to-tgm', added new." in caplog.text


def test_confirmation(mock_vk: aioresponses) -> None:
    mock_vk.post(
        "groups.getCallbackConfirmationCode",
        payload={"code": "test_code"},
    )
    mock_vk.post(
        "groups.getCallbackServers",
        payload={"count": 0, "items": []},
    )
    mock_vk.post(
        "groups.addCallbackServer",
        payload={"server_id": 1},
    )

    with client:
        response = client.post(
            "/",
            json={
                "type": "confirmation",
                "event_id": "123",
                "group_id": 123456,
                "v": "5.199",
                "secret": "vk-server-secret",
                "object": {},
            },
        )

    assert response.status_code == 200
    assert response.text == "test_code"


def test_missing_owner_id(caplog: LogCaptureFixture) -> None:
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
            },
        },
    )

    assert response.status_code == 200
    assert response.text == "ok"
    assert "[123] Post does not have an owner_id" in caplog.text


def test_missing_post_id(caplog: LogCaptureFixture) -> None:
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
            },
        },
    )

    assert response.status_code == 200
    assert response.text == "ok"
    assert "[123] Post does not have a post_id" in caplog.text


def test_ignore_ad_post(caplog: LogCaptureFixture) -> None:
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
                "marked_as_ads": True,
            },
        },
    )

    assert response.status_code == 200
    assert response.text == "ok"
    assert "[123] [1234_111] Ignoring ad post" in caplog.text


def test_ignore_donut_post(caplog: LogCaptureFixture) -> None:
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
                "donut": {
                    "is_donut": True,
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.text == "ok"
    assert "[123] [1234_111] Ignoring donut post" in caplog.text


@pytest.mark.parametrize("post_type", ["post", "reply", "photo", "video"])
def test_new_wall_post(mocker: MockerFixture, post_type: str) -> None:
    mocker.patch("app.main.get_queued_task", return_value=None)
    mocked_send_task = mocker.patch("celery.Celery.send_task")

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
                "post_type": post_type,
            },
        },
    )

    assert response.status_code == 200
    assert response.text == "ok"

    assert mocked_send_task.call_args.args == ("app.main.forward_wall",)
    assert mocked_send_task.call_args.kwargs == {
        "task_id": "wall_1234_111",
        "queue": "vtt-wall",
        "kwargs": {"owner_id": 1234, "wall_id": 111},
    }


def test_skip_wall_post(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.main.get_queued_task",
        return_value={
            "status": "SENT",
            "result": None,
            "traceback": None,
            "children": [],
            "date_done": None,
            "task_id": "wall_1234_111",
        },
    )
    mocked_send_task = mocker.patch("celery.Celery.send_task")

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

    assert not mocked_send_task.called
