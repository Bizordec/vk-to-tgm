from app.prompt import EnvTextPrompt


class SSL:
    def __init__(self, server_name: str, https_port: str, ssl_email: str) -> None:
        self._server_name = server_name
        self._https_port = https_port
        self._ssl_email = ssl_email

    @property
    def server_name(self) -> str:
        return self._server_name

    @property
    def https_port(self) -> str:
        return self._https_port

    @property
    def ssl_email(self) -> str:
        return self._ssl_email

    async def prompt_server_name(self) -> str:
        return await EnvTextPrompt.ask(
            name="NGINX_SERVER_NAME",
            description="Server name for Nginx configuration",
            default=self._server_name,
            pattern=r"^\S+$",
        )

    async def prompt_https_port(self) -> str:
        return await EnvTextPrompt.ask(
            name="NGINX_HTTPS_PORT",
            description="HTTPS port on host for docker compose configuration",
            default=self._https_port,
            pattern=r"^\d+$",
        )

    async def prompt_ssl_email(self) -> str:
        return await EnvTextPrompt.ask(
            name="SSL_EMAIL",
            default=self._ssl_email,
            description="Email address for SSL certificate expiration notification",
            pattern=r"^\S+@\S+$",
        )

    async def prompt_all(self) -> None:
        self._server_name = await self.prompt_server_name()
        self._https_port = await self.prompt_https_port()
        self._ssl_email = await self.prompt_ssl_email()
