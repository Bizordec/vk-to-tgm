from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest import mock
from unittest.mock import AsyncMock
from urllib.parse import urlencode

from dotenv import dotenv_values
from telethon.tl.types import InputPeerChannel

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


def _setup_vk_2fa_sms_mocks(mock_aioresponse: aioresponses, sid: str, token: str) -> None:
    mock_aioresponse.post(
        "https://oauth.vk.com/token",
        payload={
            "error": "need_validation",
            "error_description": "open redirect_uri in browser [5]. Also you can use 2fa_supported param",
            "validation_type": "2fa_sms",
            "validation_sid": sid,
            "phone_mask": "+7 *** *** ** 89",
            "redirect_uri": "https://m.vk.ru/login?act=authcheck&api_hash=s0m34p1h4sh",
        },
    )

    mock_aioresponse.get(
        _get_vk_method_url("auth.validatePhone", lang="en", sid=sid),
        payload={
            "response": {
                "type": "general",
                "sid": sid,
                "delay": 60,
                "libverify_support": False,
                "validation_type": "sms",
                "validation_resend": "sms",
                "code_length": 6,
            },
        },
    )

    mock_aioresponse.post(
        "https://oauth.vk.com/token",
        payload={
            "access_token": token,
        },
    )


async def test_main(
    mocker: MockerFixture,
    mock_aioresponse: aioresponses,
    tmp_path: Path,
) -> None:
    # VK_KATE_TOKEN
    _setup_vk_2fa_sms_mocks(mock_aioresponse, "2fa_735098214_5367109_3c8f2a9bde514ee781", "vk-kate-token")

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

    mocker.patch("telethon.client.telegramclient.TelegramClient.start", new=AsyncMock())
    mocker.patch(
        "telethon.client.telegramclient.TelegramClient.get_input_entity",
        side_effect=[
            InputPeerChannel(765432, "access_hash"),
            InputPeerChannel(654321, "access_hash"),
        ],
    )

    mocker.patch(
        "questionary.question.Question.unsafe_ask_async",
        side_effect=[
            "vk-login",  # vk login for kate token
            "vk-password",  # vk login for kate token
            "1234",  # 2fa sms auth code for kate token
            "vk-community-token",  # VK_COMMUNITY_TOKEN
            "123456789",  # VK_COMMUNITY_ID
            "https://example.com",  # SERVER_URL
            "test_server_title",  # VK_SERVER_TITLE
            "12345678",  # TGM_API_ID
            "s0m3v3rys3cr3tt3l3gr4map1h4sh123",  # TGM_API_HASH
            "89991234567",  # TGM_CLIENT_PHONE
            "1123456789:BkhsfLSDubilKNy86t8FGYBybxiu23aDX12",  # TGM_BOT_TOKEN
            "y",  # is main channel public
            "test_channel_name",  # TGM_CHANNEL_USERNAME
            "y",  # has playlist channel
            "y",  # is playlist channel public
            "test_pl_channel_name",  # TGM_PL_CHANNEL_USERNAME
            "y",  # VTT_IGNORE_ADS
            "en",  # VTT_LANGUAGE
            "y",  # use SSL
            "example.com",  # NGINX_SERVER_NAME
            "8443",  # NGINX_HTTPS_PORT
            "test@example.com",  # SSL_EMAIL
        ],
    )

    env_file = tmp_path / ".env"

    with mock.patch.dict(os.environ, clear=True):
        exit_code = await main(["--env-file", str(env_file)])

    assert exit_code == 0
    assert env_file.exists()

    env_values = dotenv_values(env_file)
    assert env_values["SERVER_URL"] == "https://example.com"
    assert env_values["TGM_API_HASH"] == "s0m3v3rys3cr3tt3l3gr4map1h4sh123"
    assert env_values["TGM_API_ID"] == "12345678"
    assert env_values["TGM_BOT_SESSION"] == ""
    assert env_values["TGM_BOT_TOKEN"] == "1123456789:BkhsfLSDubilKNy86t8FGYBybxiu23aDX12"  # noqa: S105
    assert env_values["TGM_CHANNEL_ID"] == "-100765432"
    assert env_values["TGM_CHANNEL_USERNAME"] == "test_channel_name"
    assert env_values["TGM_CLIENT_PHONE"] == "89991234567"
    assert env_values["TGM_CLIENT_SESSION"] == ""
    assert env_values["TGM_PL_CHANNEL_ID"] == "-100654321"
    assert env_values["TGM_PL_CHANNEL_USERNAME"] == "test_pl_channel_name"
    assert env_values["VK_COMMUNITY_ID"] == "123456789"
    assert env_values["VK_COMMUNITY_TOKEN"] == "vk-community-token"  # noqa: S105
    assert env_values["VK_KATE_TOKEN"] == "vk-kate-token"  # noqa: S105
    assert env_values["VK_SERVER_TITLE"] == "test_server_title"
    assert env_values["VTT_IGNORE_ADS"] == "True"
    assert env_values["VTT_LANGUAGE"] == "en"
    assert env_values["NGINX_SERVER_NAME"] == "example.com"
    assert env_values["NGINX_HTTPS_PORT"] == "8443"
    assert env_values["SSL_EMAIL"] == "test@example.com"
