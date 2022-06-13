import asyncio
import gettext
import logging
import re
import secrets
import sys
from typing import Callable

from aiohttp import ClientSession
from dotenv.main import set_key
from pydantic import BaseSettings, root_validator, validator
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.utils import get_peer_id
from vkaudiotoken import TwoFAHelper, get_kate_token, get_vk_official_token, supported_clients
from vkaudiotoken.CommonParams import CommonParams
from vkaudiotoken.TokenException import TokenException
from vkbottle import AiohttpClient
from vkbottle.api.api import API
from vkbottle.exception_factory import VKAPIError

from app.utils.telegram import get_entity_by_username

logger = logging.getLogger(__name__)

vk_lang_pattern = re.compile(r"^(ru|uk|be|en|es|fi|de|it)$")


async def get_tgm_channel_id(client: TelegramClient, key_to_set: str, channel_username: str):
    entity = await get_entity_by_username(client, channel_username)
    if not entity:
        raise ValueError(f"Failed to get {key_to_set}.")
    channel_id = get_peer_id(entity)
    set_key(".env", key_to_set, channel_id, quote_mode="never")
    return channel_id


def handle_2fa(
    user_agent: str,
    t_name: str,
    validation_sid: str,
) -> str:
    params = CommonParams(user_agent)
    try:
        TwoFAHelper(params).validate_phone(validation_sid)
        logger.warning("SMS should be sent")
    except TokenException as error:
        error_extra: dict = error.extra or {}
        error_obj: dict = error_extra.get("error", {})
        error_code = error_obj.get("error_code") if error_obj else None
        if error_code is None or error_code != 103:
            raise
    while True:
        try:
            return str(int(input(f"[{t_name}] Enter auth code: ")))
        except ValueError:
            logger.warning("Please enter integer code.")


def get_new_vk_token(
    login: str,
    password: str,
    user_agent: str,
    get_token: Callable[[str, str, str, str, str], str],
    t_name: str,
):
    if not login and not password:
        logger.critical("Environment variables VK_LOGIN and VK_PASSWORD are required.")
        sys.exit(1)
    logger.info(f"[{t_name}] Getting new token...")
    auth_code = "GET_CODE"
    captcha_sid = None
    captcha_key = None
    while True:
        try:
            current_token = get_token(
                login,
                password,
                auth_code=auth_code,
                captcha_sid=captcha_sid,
                captcha_key=captcha_key,
            )["token"]
            if current_token:
                set_key(".env", t_name, current_token)
                break
        except TokenException as err:
            err_code: int = err.code
            err_extra: dict = err.extra or {}
            if err_code == TokenException.TOKEN_NOT_RECEIVED:
                auth_code = "GET_CODE"
                captcha_sid = None
                captcha_key = None
                continue
            if err_code == TokenException.CAPTCHA_REQ and "captcha_sid" in err_extra:
                captcha_sid = err_extra["captcha_sid"]
                captcha_key = input("Enter captcha key from image (" + err_extra["captcha_img"] + "): ")
                continue
            if err_code == TokenException.TWOFA_REQ and "validation_sid" in err_extra:
                auth_code = handle_2fa(user_agent, t_name, err_extra["validation_sid"])
            else:
                raise
    return current_token


async def get_validated_vk_token(
    login: str,
    password: str,
    user_agent: str,
    t_name: str,
    current_token: str = "",
    exit_on_error: bool = False,
    is_kate: bool = True,
) -> str:
    vk_user = API(
        token=current_token,
        http_client=AiohttpClient(session=ClientSession(headers={"User-agent": user_agent})),
    )
    try:
        logger.info(f"[{t_name}] Checking if token is valid...")
        await vk_user.users.get()
        logger.info(f"[{t_name}] Token is valid.")
    except VKAPIError[5] as error:
        err_msg = error.description
        logger.warning(f"[{t_name}] Token is not valid: {err_msg}")
        if exit_on_error:
            sys.exit(err_msg)
        else:
            current_token = await get_vk_token("", login, password, exit_on_error=True, is_kate=is_kate)
    finally:
        await vk_user.http_client.close()
    return current_token


async def get_vk_token(
    login: str,
    password: str,
    current_token: str = "",
    exit_on_error: bool = False,
    is_kate: bool = True,
):
    if is_kate:
        user_agent = supported_clients.KATE.user_agent
        get_token = get_kate_token
        t_name = "KATE_TOKEN"
    else:
        user_agent = supported_clients.VK_OFFICIAL.user_agent
        get_token = get_vk_official_token
        t_name = "VK_OFFICIAL_TOKEN"
    if not current_token:
        current_token = get_new_vk_token(user_agent, get_token, t_name)

    return await get_validated_vk_token(
        login,
        password,
        user_agent,
        t_name,
        current_token,
        exit_on_error,
        is_kate,
    )


class Settings(BaseSettings):
    VK_LOGIN: str = ""
    VK_PASSWORD: str = ""

    VK_COMMUNITY_ID: int
    VK_COMMUNITY_TOKEN: str

    VK_SERVER_TITLE: str
    VK_SERVER_SECRET: str = secrets.token_hex(25)

    # Id is 0 by default for root_validator
    TGM_CHANNEL_ID: int = 0
    TGM_CHANNEL_USERNAME: str = ""
    TGM_PL_CHANNEL_ID: int = 0
    TGM_PL_CHANNEL_USERNAME: str = ""

    TGM_CLIENT_PHONE: str = ""
    TGM_BOT_TOKEN: str

    TGM_API_ID: int
    TGM_API_HASH: str

    SERVER_URL: str

    KATE_TOKEN: str = ""
    VK_OFFICIAL_TOKEN: str = ""

    VTT_LANGUAGE: str = "en"
    VK_API_LANGUAGE: str = ""

    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    CELERY_RESULT_BACKEND: str = "db+sqlite:///celery-results.db"

    @validator("VK_SERVER_TITLE")
    def check_vk_server_title(cls, value: str):
        title_length = len(value)
        if title_length < 1 or title_length > 14:
            raise ValueError("VK_SERVER_TITLE must have length of 1-14 characters.")
        return value

    @validator("SERVER_URL")
    def check_server_url(cls, value: str):
        if not re.fullmatch(r"^https?://.*", value):
            raise ValueError("SERVER_URL must start with 'http[s]://'.")
        if not value.endswith("/"):
            value = f"{value}/"
        return value

    @validator("VTT_LANGUAGE")
    def check_vtt_lang(cls, value: str):
        if not gettext.find("vtt", "locale", languages=[value]):
            raise ValueError("No such locale available for VTT_LANGUAGE.")
        return value

    @validator("VK_API_LANGUAGE")
    def check_vk_api_lang(cls, value: str):
        if value and not vk_lang_pattern.fullmatch(value):
            raise ValueError("No such locale available for VK_API_LANGUAGE.")
        return value

    @staticmethod
    async def _async_check_all(values: dict):
        if not values["VK_API_LANGUAGE"]:
            VTT_LANGUAGE: str = values["VTT_LANGUAGE"]
            if vk_lang_pattern.fullmatch(VTT_LANGUAGE):
                values["VK_API_LANGUAGE"] = VTT_LANGUAGE
            else:
                values["VK_API_LANGUAGE"] = "en"

        TGM_CHANNEL_ID: str = values["TGM_CHANNEL_ID"]
        TGM_PL_CHANNEL_ID: str = values["TGM_PL_CHANNEL_ID"]
        if not TGM_CHANNEL_ID or not TGM_PL_CHANNEL_ID:
            client = TelegramClient(MemorySession(), values["TGM_API_ID"], values["TGM_API_HASH"])
            async with await client.start(bot_token=values["TGM_BOT_TOKEN"]):  # type: ignore
                if not TGM_CHANNEL_ID:
                    TGM_CHANNEL_USERNAME: str = values["TGM_CHANNEL_USERNAME"]
                    if not TGM_CHANNEL_USERNAME:
                        raise ValueError("TGM_CHANNEL_ID or TGM_CHANNEL_USERNAME is required.")
                    values["TGM_CHANNEL_ID"] = await get_tgm_channel_id(
                        client=client,
                        key_to_set="TGM_CHANNEL_ID",
                        channel_username=TGM_CHANNEL_USERNAME,
                    )

                TGM_PL_CHANNEL_USERNAME: str = values["TGM_PL_CHANNEL_USERNAME"]
                if not TGM_PL_CHANNEL_ID and TGM_PL_CHANNEL_USERNAME:
                    TGM_PL_CHANNEL_ID = await get_tgm_channel_id(
                        client=client,
                        key_to_set="TGM_PL_CHANNEL_ID",
                        channel_username=TGM_PL_CHANNEL_USERNAME,
                    )

        KATE_TOKEN: str = values["KATE_TOKEN"]
        VK_OFFICIAL_TOKEN: str = values["VK_OFFICIAL_TOKEN"]
        if not KATE_TOKEN or not VK_OFFICIAL_TOKEN:
            VK_LOGIN: str = values["VK_LOGIN"]
            VK_PASSWORD: str = values["VK_PASSWORD"]
            if not VK_LOGIN or not VK_PASSWORD:
                raise ValueError("Either VK_LOGIN and VK_PASSWORD or KATE_TOKEN and VK_OFFICIAL_TOKEN are required.")
            values["KATE_TOKEN"] = await get_vk_token(
                VK_LOGIN,
                VK_PASSWORD,
                KATE_TOKEN,
            )
            values["VK_OFFICIAL_TOKEN"] = await get_vk_token(
                VK_LOGIN,
                VK_PASSWORD,
                VK_OFFICIAL_TOKEN,
                is_kate=False,
            )

    @root_validator(skip_on_failure=True)
    def check_all(cls, values: dict):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(cls._async_check_all(values))
        else:
            loop.run_until_complete(cls._async_check_all(values))
        return values

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

_ = gettext.translation("vtt", "locale", languages=[settings.VTT_LANGUAGE]).gettext
