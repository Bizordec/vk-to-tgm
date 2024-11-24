from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

from telethon.tl.types import InputPeerChannel
from vkaudiotoken import supported_clients

from app.main import main

if TYPE_CHECKING:
    from pathlib import Path

    from aioresponses import aioresponses
    from pytest_mock import MockerFixture


def test_main(mocker: MockerFixture, mock_vk: aioresponses, tmp_path: Path) -> None:
    mocker.patch(
        "vkaudiotoken.get_kate_token",
        return_value={
            "token": "kate-token",
            "user_agent": supported_clients.KATE.user_agent,
        },
    )
    mocker.patch(
        "vkaudiotoken.get_vk_official_token",
        return_value={
            "token": "vk-official-token",
            "user_agent": supported_clients.VK_OFFICIAL.user_agent,
        },
    )
    mock_vk.post(
        "groups.getTokenPermissions",
        payload={
            "mask": 262144,
            "permissions": [
                {
                    "name": "manage",
                    "setting": 262144,
                },
            ],
        },
    )
    mock_vk.post(
        "groups.getCallbackServers",
        payload={
            "count": 0,
            "items": [],
        },
    )
    mocker.patch("telethon.client.telegramclient.TelegramClient.start")
    mocker.patch(
        "telethon.client.telegramclient.TelegramClient.get_input_entity",
        side_effect=[
            InputPeerChannel(765432, "access_hash"),
            InputPeerChannel(654321, "access_hash"),
        ],
    )

    mocker.patch(
        "rich.console.Console.input",
        side_effect=[
            "vk-login",
            "vk-password",
            "vk-community-token",
            "123456789",
            "https://example.com",
            "test_server_title",
            "12345678",
            "s0m3v3rys3cr3tt3l3gr4map1h4sh123",
            "89991234567",
            "1123456789:BkhsfLSDubilKNy86t8FGYBybxiu23aDX12",
            "y",  # is main channel public
            "test_channel_name",
            "y",  # has playlist channel
            "y",  # is playlist channel public
            "test_pl_channel_name",
            "y",
            "en",
        ],
    )

    env_file = tmp_path / ".env"
    exit_code = main(["--env-file", str(env_file)])

    assert exit_code == 0
    assert env_file.exists()

    env_content = env_file.read_text(encoding="utf8")
    assert env_content == dedent("""
        SERVER_URL='https://example.com'
        TGM_API_HASH='s0m3v3rys3cr3tt3l3gr4map1h4sh123'
        TGM_API_ID='12345678'
        TGM_BOT_SESSION=''
        TGM_BOT_TOKEN='1123456789:BkhsfLSDubilKNy86t8FGYBybxiu23aDX12'
        TGM_CHANNEL_ID='-100765432'
        TGM_CHANNEL_USERNAME='test_channel_name'
        TGM_CLIENT_PHONE='89991234567'
        TGM_CLIENT_SESSION=''
        TGM_PL_CHANNEL_ID='-100654321'
        TGM_PL_CHANNEL_USERNAME='test_pl_channel_name'
        VK_COMMUNITY_ID='123456789'
        VK_COMMUNITY_TOKEN='vk-community-token'
        VK_KATE_TOKEN='kate-token'
        VK_OFFICIAL_TOKEN='vk-official-token'
        VK_SERVER_TITLE='test_server_title'
    """).lstrip("\n")
