from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

import questionary
from aiohttp import ClientSession
from vkbottle import API, AiohttpClient, UserAuth, VKAPIError

from app.console import console
from app.vk.exception import handle_token_exception
from app.vk.models import AuthParams

if TYPE_CHECKING:
    from typing import TypedDict

    class TokenData(TypedDict):
        token: str
        user_agent: str


class TokenFunc(Protocol):
    def __call__(
        self,
        login: str,
        password: str,
        auth_code: str,
        captcha_sid: str,
        captcha_key: str,
    ) -> TokenData: ...


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
    def client_id(self) -> int: ...

    @property
    @abstractmethod
    def client_secret(self) -> str: ...

    @property
    @abstractmethod
    def user_agent(self) -> str: ...

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
    async def prompt_login() -> str:
        while True:
            login: str = await questionary.text(
                "Enter VK login (used to create tokens):",
            ).unsafe_ask_async()
            if login:
                return login
            console.print("[prompt.invalid]VK login must not be empty")

    @staticmethod
    async def prompt_password() -> str:
        while True:
            password: str = await questionary.password(
                "Enter VK password (used to create tokens):",
            ).unsafe_ask_async()
            if password:
                return password
            console.print("[prompt.invalid]VK password must not be empty")

    async def is_valid_token(self, token: str) -> bool:
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
            await vk_api.request("audio.get", data={})
        except VKAPIError as error:
            console.print(
                f"[prompt.invalid]Could not verify '{self.token_name}': {error.error_msg}",
            )
        else:
            console.print(f"{self.token_name} is valid.")
            return True
        return False

    async def get_new_token(self) -> str:
        params = AuthParams(need_creds=self._need_creds)
        user_auth = UserAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            http_client=AiohttpClient(
                session=ClientSession(headers={"User-agent": self.user_agent}),
            ),
        )
        while True:
            if params.need_creds:
                self._login = await self.prompt_login()
                self._password = await self.prompt_password()
            try:
                console.print(f"Getting new '{self.token_name}'...")
                return await user_auth.get_token(
                    login=self._login,
                    password=self._password,
                    auth_code=params.auth_code,
                    captcha_sid=params.captcha_sid,
                    captcha_key=params.captcha_key,
                )
            except VKAPIError as error:
                console.print(
                    f"Error on getting new '{self.token_name}': {error.error_msg}",
                )

                params = await handle_token_exception(user_auth=user_auth, error=error)
                token = params.token
                if await self.is_valid_token(token=token):
                    return token

    async def prompt_all(self) -> None:
        if await self.is_valid_token(token=self._token):
            return

        self._token = await self.get_new_token()


class KateAuth(Auth):
    @property
    def token_name(self) -> str:
        return "VK Kate token"

    @property
    def client_id(self) -> int:
        return 2685278

    @property
    def client_secret(self) -> str:
        return "lxhD8OD7dMsqtXIm5IUY"

    @property
    def user_agent(self) -> str:
        return "KateMobileAndroid/56 lite-460 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en)"
