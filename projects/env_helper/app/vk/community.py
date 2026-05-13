from vkbottle import API, AiohttpClient, VKAPIError
from vkbottle_types.codegen.methods.groups import GroupsCategory

from app.config import DIGITS_PATTERN, SERVER_URL_PATTERN
from app.console import console
from app.prompt import EnvPasswordPrompt, EnvTextPrompt


class Community:
    def __init__(
        self,
        community_id: str,
        community_token: str,
        server_title: str,
        server_url: str,
    ) -> None:
        self._community_id = community_id
        self._community_token = community_token
        self._server_title = server_title
        self._server_url = server_url

    @property
    def community_token(self) -> str:
        return self._community_token

    @property
    def community_id(self) -> str:
        return self._community_id

    @property
    def server_title(self) -> str:
        return self._server_title

    @property
    def server_url(self) -> str:
        return self._server_url

    @staticmethod
    async def is_valid_token(token: str) -> bool:
        if not token:
            return False

        vk_groups = GroupsCategory(API(token=token, http_client=AiohttpClient()))
        try:
            console.print("Checking if VK community token is valid...")
            token_permissions = await vk_groups.get_token_permissions()
            console.print("VK community token is valid.")
        except VKAPIError as error:
            error_msg = error.error_msg
            console.print(
                f"[prompt.invalid]Could not verify VK community token: {error_msg}",
            )
            return False

        if not token_permissions.mask & 262144:
            console.print(
                "[prompt.invalid]VK community token does not have 'manage' permission",
            )
            return False
        return True

    async def is_valid_id(self, community_id: str) -> bool:
        vk_groups = GroupsCategory(
            API(token=self._community_token, http_client=AiohttpClient()),
        )
        try:
            console.print("Checking if VK community id is valid...")
            await vk_groups.get_callback_servers(group_id=int(community_id))
            console.print("VK community id is valid.")
        except VKAPIError as error:
            error_msg = error.error_msg
            console.print(
                f"[prompt.invalid]Could not verify VK community id: {error_msg}",
            )
            return False
        return True

    async def prompt_community_id(self) -> str:
        return await EnvTextPrompt.ask(
            name="VK_COMMUNITY_ID",
            default=self._community_id,
            description="VK community ID. Must be numeric. Read more: https://vk.ru/faq18062",
            pattern=DIGITS_PATTERN,
        )

    async def prompt_community_token(self) -> str:
        return await EnvPasswordPrompt.ask(
            name="VK_COMMUNITY_TOKEN",
            default=self._community_token,
            description="""
            VK community token.
            To get it, go to your VK community,
            "Manage" > "Additional" > "API usage" > "Access tokens" > "Create token",
            check "Allow access to community management" permission
            and then click "Create".
            """,
        )

    async def prompt_server_url(self) -> str:
        return await EnvTextPrompt.ask(
            name="SERVER_URL",
            default=self._server_url,
            description="URL of your server. Will be used in automatic server creation.",
            pattern=SERVER_URL_PATTERN,
        )

    async def prompt_server_title(self) -> str:
        return await EnvTextPrompt.ask(
            name="VK_SERVER_TITLE",
            default=self._server_title,
            description="Title for VK Callback API server. Will be used in automatic server creation.",
        )

    async def prompt_all(self) -> None:
        while True:
            self._community_token = await self.prompt_community_token()
            if await self.is_valid_token(self._community_token):
                break
            self._community_token = ""

        while True:
            self._community_id = await self.prompt_community_id()
            if await self.is_valid_id(community_id=self._community_id):
                break
            self._community_id = ""

        self._server_url = await self.prompt_server_url()
        self._server_title = await self.prompt_server_title()
