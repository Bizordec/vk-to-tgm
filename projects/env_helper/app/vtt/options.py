from typing import cast, get_args

from app.config import VttLanguage
from app.prompt import EnvConfirmPrompt, EnvSelectPrompt


class Options:
    def __init__(self, *, ignore_ads: bool, language: VttLanguage) -> None:
        self._ignore_ads = ignore_ads
        self._language = language

    @property
    def ignore_ads(self) -> bool:
        return self._ignore_ads

    @property
    def language(self) -> VttLanguage:
        return self._language

    async def prompt_ignore_ads(self) -> bool:
        return await EnvConfirmPrompt.ask(
            name="VTT_IGNORE_ADS",
            description="Ignore forwarding VK ad posts to the main Telegram channel",
            default=self._ignore_ads,
        )

    async def prompt_language(self) -> VttLanguage:
        return cast(
            VttLanguage,
            await EnvSelectPrompt.ask(
                name="VTT_LANGUAGE",
                default=self.language,
                description="Text language for Telegram bot and posts",
                pattern=None,
                choices=get_args(VttLanguage),
            ),
        )

    async def prompt_all(self) -> None:
        self._ignore_ads = await self.prompt_ignore_ads()
        self._language = await self.prompt_language()
