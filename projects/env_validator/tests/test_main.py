from __future__ import annotations

import os
from textwrap import dedent
from typing import TYPE_CHECKING
from unittest import mock
from unittest.mock import AsyncMock, Mock
from urllib.parse import urlencode

from telethon.tl.custom.participantpermissions import ParticipantPermissions
from telethon.tl.types import InputPeerChannel, InputPeerUser

from app.main import main

if TYPE_CHECKING:
    from pathlib import Path

    from aioresponses import aioresponses
    from pytest_mock import MockerFixture


def _get_vk_method_url(method: str, access_token: str = "", **kwargs: str) -> str:
    params = {
        "v": "5.199",
    }
    params.update(kwargs)
    if access_token:
        params["access_token"] = access_token
    return f"https://api.vk.ru/method/{method}?{urlencode(params)}"


def setup_vk_mocks(mock_aioresponse: aioresponses) -> None:
    # VK_TOKEN
    mock_aioresponse.post(
        _get_vk_method_url("audio.get", access_token="vk-token"),  # noqa: S106
        payload={
            "response": {
                "count": 0,
                "items": [],
            },
        },
    )

    # VK_COMMUNITY_TOKEN
    mock_aioresponse.post(
        _get_vk_method_url("groups.getTokenPermissions", access_token="vk-community-token"),  # noqa: S106
        payload={
            "response": {
                "mask": 262144,
                "permissions": [
                    {
                        "name": "manage",
                        "setting": 262144,
                    },
                ],
            },
        },
    )

    # VK_COMMUNITY_ID
    mock_aioresponse.post(
        _get_vk_method_url("groups.getCallbackServers", access_token="vk-community-token"),  # noqa: S106
        payload={
            "response": {
                "count": 0,
                "items": [],
            },
        },
    )


def setup_telegram_mocks(mocker: MockerFixture) -> None:
    mocker.patch("telethon.client.telegramclient.TelegramClient.start", new=AsyncMock())
    mocker.patch(
        "telethon.client.telegramclient.TelegramClient.get_input_entity",
        side_effect=[
            InputPeerChannel(765432, "access_hash"),
            InputPeerChannel(654321, "access_hash"),
        ],
    )
    mocker.patch(
        "telethon.client.telegramclient.TelegramClient.get_me",
        return_value=InputPeerUser(1234, "access_hash"),
    )
    permissions_mock = Mock(spec=ParticipantPermissions)
    permissions_mock.post_messages = True
    permissions_mock.edit_messages = True

    mocker.patch(
        "telethon.client.telegramclient.TelegramClient.get_permissions",
        side_effect=[permissions_mock],
    )


def test_main(
    mocker: MockerFixture,
    mock_aioresponse: aioresponses,
    tmp_path: Path,
) -> None:
    # VK env vars
    setup_vk_mocks(mock_aioresponse)

    # TGM env vars
    setup_telegram_mocks(mocker)

    env_file = tmp_path / ".env"
    env_file.write_text(
        dedent("""
    SERVER_URL="https://example.com"
    TGM_API_HASH="s0m3v3rys3cr3tt3l3gr4map1h4sh123"
    TGM_API_ID="12345678"
    TGM_BOT_TOKEN="1123456789:BkhsfLSDubilKNy86t8FGYBybxiu23aDX12"
    TGM_BOT_SESSION="1ApWapzMBu3Rlc3Rfa2V5AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    TGM_CHANNEL_ID="-100765432"
    TGM_CHANNEL_USERNAME="test_channel_name"
    TGM_CLIENT_PHONE="89991234567"
    TGM_CLIENT_SESSION="1ApWapzMBu3Rlc3Rfa2V5AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    TGM_PL_CHANNEL_ID="-100654321"
    TGM_PL_CHANNEL_USERNAME="test_pl_channel_name"
    VK_COMMUNITY_ID="123456789"
    VK_COMMUNITY_TOKEN="vk-community-token"
    VK_TOKEN="vk-token"
    VK_SERVER_TITLE="vk-to-tgm"
    VTT_IGNORE_ADS="true"
    VTT_LANGUAGE="en"
    NGINX_SERVER_NAME="example.com"
    NGINX_HTTPS_PORT="443"
    SSL_EMAIL="test@example.com"
    """),
    )

    with mock.patch.dict(os.environ, clear=True):
        exit_code = main(["--env-file", str(env_file)])

    assert exit_code == 0
