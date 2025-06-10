from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import questionary
from vkbottle import APIAuthError, AuthError, CaptchaError

from app.console import console
from app.prompt import EnvPasswordPrompt, int_validator
from app.vk.models import AuthParams

if TYPE_CHECKING:
    from vkbottle import UserAuth, VKAPIError


class FloodControlError(Exception):
    pass


async def _handle_2fa_sms(user_auth: UserAuth, validation_sid: str) -> AuthParams:
    await user_auth.validate_phone(validation_sid)

    console.print("[yellow]SMS should be sent")

    auth_code: str = await questionary.text("Enter auth code:", validate=int_validator).unsafe_ask_async()

    return AuthParams(auth_code=auth_code, need_creds=False)


async def _handle_2fa_app(redirect_uri: str) -> AuthParams:
    console.print(f"Enter code from 2FA app here: {redirect_uri}")
    while True:
        url = await EnvPasswordPrompt.ask(prompt="Enter OAuth URL from VK after signin in")
        parsed_url = urlparse(url=url)
        try:
            access_token = parse_qs(parsed_url.fragment)["access_token"][0]
        except KeyError:
            access_token = None
        if parsed_url.hostname != "oauth.vk.com" or not access_token:
            console.print("[prompt.invalid]Incorrect URL.")
            continue
        return AuthParams(token=access_token)


async def _handle_captcha(error: CaptchaError) -> AuthParams:
    captcha_key = await questionary.text(f"Enter captcha key from image ({error.captcha_img}):").unsafe_ask_async()
    return AuthParams(captcha_sid=error.captcha_sid, captcha_key=captcha_key, need_creds=False)


async def handle_token_exception(user_auth: UserAuth, error: VKAPIError) -> AuthParams:
    if isinstance(error, CaptchaError):
        return await _handle_captcha(error=error)
    if isinstance(error, APIAuthError):
        validation_type = error.validation_type
        if validation_type == "2fa_sms":
            return await _handle_2fa_sms(user_auth=user_auth, validation_sid=error.validation_sid)
        if validation_type == "2fa_app":
            return await _handle_2fa_app(redirect_uri=error.redirect_uri)
    if isinstance(error, AuthError):
        error_name = error.error_msg
        if error_name == "invalid_client":
            return AuthParams(need_creds=True)
        if error_name == "9;Flood control":
            raise FloodControlError
        return AuthParams(auth_code=True)
    raise error
