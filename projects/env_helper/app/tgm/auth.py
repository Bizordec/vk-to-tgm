from abc import ABC, abstractmethod

from telethon.errors import AccessTokenInvalidError, ApiIdInvalidError
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from app.config import DIGITS_PATTERN, TGM_BOT_TOKEN_PATTERN
from app.console import console
from app.prompt import EnvPrompt


class Auth(ABC):
    def __init__(
        self,
        api_id: str,
        api_hash: str,
        access_token: str,
        session: str,
    ) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._access_token = access_token
        self._session = session
        self._need_app_creds = not self._api_id or not self._api_hash

        self._client: TelegramClient | None = None

    @property
    @abstractmethod
    def auth_type(self) -> str: ...

    @abstractmethod
    def prompt_access_token(self) -> str: ...

    @property
    def api_id(self) -> str:
        return self._api_id

    @property
    def api_hash(self) -> str:
        return self._api_hash

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def session(self) -> str:
        return self._session

    @property
    def client(self) -> TelegramClient:
        if self._client:
            return self._client

        client = TelegramClient(
            session=StringSession(string=self._session),
            api_id=self._api_id,
            api_hash=self._api_hash,
        )

        console.print(f"Checking if {self.auth_type} Telegram credentials are valid...")
        client.start(phone=lambda: self._access_token)
        console.print(f"{self.auth_type} Telegram credentials are valid.")

        self._client = client
        return client

    def update_session(self) -> None:
        client = self.client
        self._session = client.session.save()

    def prompt_api_id(self) -> str:
        return EnvPrompt.ask(
            name="TGM_API_ID",
            default=self._api_id,
            description="Telegram API ID. Read more: https://core.telegram.org/api/obtaining_api_id",
            pattern=DIGITS_PATTERN,
            password=True,
        )

    def prompt_api_hash(self) -> str:
        return EnvPrompt.ask(
            name="TGM_API_HASH",
            default=self._api_hash,
            description="Telegram API hash. Read more: https://core.telegram.org/api/obtaining_api_id",
            password=True,
        )

    def prompt_all(self) -> None:
        need_token = True
        while True:
            if self._need_app_creds:
                self._api_id = self.prompt_api_id()
                self._api_hash = self.prompt_api_hash()
            if need_token:
                self._access_token = self.prompt_access_token()
            try:
                self.update_session()
                break
            except ApiIdInvalidError:
                self._need_app_creds = True
                self._api_id = ""
                self._api_hash = ""
                console.print("[prompt.invalid]Invalid Telegram API ID or API hash")
            except AccessTokenInvalidError:
                self._need_app_creds = False
                need_token = True
                self._access_token = ""
                console.print("[prompt.invalid]Invalid Telegram access token")


class UserAuth(Auth):
    @property
    def auth_type(self) -> str:
        return "User"

    def prompt_access_token(self) -> str:
        return EnvPrompt.ask(
            name="TGM_CLIENT_PHONE",
            default=self._access_token,
            description="Telegram client phone. Must be numeric. Used for searching posts in main channel.",
            pattern=DIGITS_PATTERN,
            password=True,
        )


class BotAuth(Auth):
    @property
    def auth_type(self) -> str:
        return "Bot"

    def prompt_access_token(self) -> str:
        return EnvPrompt.ask(
            name="TGM_BOT_TOKEN",
            default=self._access_token,
            description="Telegram bot token. Read more: https://core.telegram.org/bots#how-do-i-create-a-bot",
            pattern=TGM_BOT_TOKEN_PATTERN,
            password=True,
        )
