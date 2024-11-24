from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from rich.prompt import IntPrompt, Prompt
from vkaudiotoken import CommonParams, TokenException, TwoFAHelper

from app.console import console
from app.vk.models import AuthParams

if TYPE_CHECKING:
    from typing import Any


class FloodControlError(Exception):
    pass


def _prompt_auth_code() -> int:
    return IntPrompt.ask(prompt="Enter auth code", password=True)


def _handle_2fa_sms(user_agent: str, validation_sid: str) -> AuthParams:
    params = CommonParams(user_agent)
    TwoFAHelper(params).validate_phone(validation_sid)
    console.print("[yellow]SMS should be sent")
    return AuthParams(auth_code=str(_prompt_auth_code()))


def _handle_2fa_app(redirect_uri: str) -> AuthParams:
    console.print(f"Enter code from 2FA app here: {redirect_uri}")
    while True:
        url = Prompt.ask(
            prompt="Enter OAuth URL from VK after signin in",
            password=True,
        )
        parsed_url = urlparse(url=url)
        try:
            access_token = parse_qs(parsed_url.fragment)["access_token"][0]
        except KeyError:
            access_token = None
        if parsed_url.hostname != "oauth.vk.com" or not access_token:
            console.print("[prompt.invalid]Incorrect URL.")
            continue
        return AuthParams(token=access_token)


def _handle_captcha(error_extra: dict[str, Any]) -> AuthParams:
    captcha_sid = error_extra["captcha_sid"]
    captcha_key = input(
        "Enter captcha key from image (" + error_extra["captcha_img"] + "): ",
    )
    return AuthParams(captcha_sid=captcha_sid, captcha_key=captcha_key)


def handle_token_exception(user_agent: str, error: TokenException) -> AuthParams:
    error_code: int = error.code
    error_extra: dict[str, Any] = error.extra or {}
    error_name = error_extra["error"]
    if error_name == "need_validation":
        validation_type = error_extra["validation_type"]
        if validation_type == "2fa_sms":
            return _handle_2fa_sms(
                user_agent=user_agent,
                validation_sid=error_extra["validation_sid"],
            )
        if validation_type == "2fa_app":
            return _handle_2fa_app(redirect_uri=error_extra["redirect_uri"])
    if error_code == TokenException.TOKEN_NOT_RECEIVED:
        if error_name == "invalid_client":
            return AuthParams(need_creds=True)
        if error_name == "9;Flood control":
            raise FloodControlError
        return AuthParams(auth_code="GET_CODE")
    if error_code == TokenException.CAPTCHA_REQ:
        return _handle_captcha(error_extra=error_extra)
    raise error
