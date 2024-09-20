from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import uvloop
from aiohttp import ClientSession
from rich.prompt import Prompt
from vkaudiotoken import (
    TokenException,
    get_kate_token,
    get_vk_official_token,
    supported_clients,
)
from vkbottle import API, AiohttpClient, VKAPIError

from app.console import console
from app.vk.exception import handle_token_exception
from app.vk.models import AuthParams

if TYPE_CHECKING:
    from typing import Protocol

    class TokenFunc(Protocol):
        def __call__(
            self,
            login: str,
            password: str,
            auth_code: str,
            captcha_sid: str,
            captcha_key: str,
        ) -> str: ...


class Auth(ABC):
    def __init__(self, token: str, login: str = "", password: str = "") -> None:
        self._token = token
        self._login = login
        self._password = password

        self._need_creds = not self._login or not self._password

    @property
    @abstractmethod
    def token_name(self) -> str: ...

    @property
    @abstractmethod
    def user_agent(self) -> str: ...

    @property
    @abstractmethod
    def get_token_fn(self) -> TokenFunc: ...

    @property
    def login(self) -> str:
        return self._login

    @property
    def password(self) -> str:
        return self._password

    @property
    def token(self) -> str:
        return self._token

    @staticmethod
    def prompt_login() -> str:
        while True:
            login = Prompt.ask("Enter VK login (used to create tokens)")
            if login:
                return login
            console.print("[prompt.invalid]VK login must not be empty")

    @staticmethod
    def prompt_password() -> str:
        while True:
            password = Prompt.ask(
                "Enter VK password (used to create tokens)",
                password=True,
            )
            if password:
                return password
            console.print("[prompt.invalid]VK password must not be empty")

    async def _is_valid_token(self, token: str) -> bool:
        if not token:
            return False

        vk_api = API(
            token=token,
            http_client=AiohttpClient(
                session=ClientSession(headers={"User-agent": self.user_agent}),
            ),
        )
        try:
            console.print(f"Checking if {self.token_name} is valid...")
            await vk_api.users.get()
        except VKAPIError as error:
            error_msg = error.description
            console.print(
                f"[prompt.invalid]Could not verify '{self.token_name}': {error_msg}",
            )
        else:
            console.print(f"{self.token_name} is valid.")
            return True
        return False

    def is_valid_token(self, token: str) -> bool:
        return uvloop.run(self._is_valid_token(token=token))

    def get_new_token(self) -> str:
        params = AuthParams(auth_code="GET_CODE", need_creds=self._need_creds)
        while True:
            if params.need_creds:
                self._login = self.prompt_login()
                self._password = self.prompt_password()
            try:
                console.print(f"Getting new '{self.token_name}'...")
                return self.get_token_fn(
                    login=self._login,
                    password=self._password,
                    auth_code=params.auth_code,
                    captcha_sid=params.captcha_sid,
                    captcha_key=params.captcha_key,
                )
            except TokenException as error:
                error_extra: dict = error.extra or {}
                error_desc = error_extra.get("error_description", error)
                console.print(f"Error on getting new '{self.token_name}': {error_desc}")

                params = handle_token_exception(user_agent=self.user_agent, error=error)
                token = params.token
                if self.is_valid_token(token=token):
                    return token

    def prompt_all(self) -> None:
        if self.is_valid_token(token=self._token):
            return

        self._token = self.get_new_token()


class OfficialAuth(Auth):
    @property
    def token_name(self) -> str:
        return "VK official token"

    @property
    def user_agent(self) -> str:
        return supported_clients.VK_OFFICIAL.user_agent

    @property
    def get_token_fn(self) -> TokenFunc:
        return get_vk_official_token


class KateAuth(Auth):
    @property
    def token_name(self) -> str:
        return "VK Kate token"

    @property
    def user_agent(self) -> str:
        return supported_clients.KATE.user_agent

    @property
    def get_token_fn(self) -> TokenFunc:
        return get_kate_token
