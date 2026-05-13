from __future__ import annotations

import inspect
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast

import questionary
from rich.text import Text

from app.console import console

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from questionary.prompts.common import Choice


def int_validator(value: str) -> bool | str:
    try:
        int(value)
    except ValueError:
        return "Value must be integer"

    return True


class BaseEnvPrompt[PromptType: (str, bool)](ABC):
    def __init__(
        self,
        prompt: str,
        name: str,
        description: str,
        pattern: str | re.Pattern[str] | None = None,
        default: PromptType | None = None,
        choices: Sequence[str | Choice | dict[str, Any]] | None = None,
    ) -> None:
        self.prompt = prompt
        self.name = name
        self.description = description
        self.re_pattern = re.compile(pattern) if pattern else None

        self.default: PromptType | None = default
        self.choices = choices or []

        self.validator = self._make_validator(self.re_pattern) if self.re_pattern else None

    def _make_validator(self, re_pattern: re.Pattern[str]) -> Callable[[str], bool | str]:
        def validator(value: str) -> bool | str:
            if not re_pattern.match(value.strip()):
                return "Please enter a value, that matches pattern"
            return True

        return validator

    def _pre_prompt(self) -> None:
        console.rule()
        console.print("[bold]Name[/]:", end=" ")
        console.print(self.name, highlight=False, markup=False)

        if self.re_pattern:
            console.print("[bold]Pattern[/]:", end=" ")
            console.print(self.re_pattern.pattern, highlight=False, markup=False)

        console.print("[bold]Description[/]:", end=" ")
        console.print(Text.from_markup(inspect.cleandoc(self.description)), highlight=False, markup=False, end="\n\n")

    @abstractmethod
    async def get_input(self) -> PromptType:
        raise NotImplementedError

    async def __call__(self) -> PromptType:
        self._pre_prompt()
        return await self.get_input()

    @classmethod
    async def ask(
        cls,
        prompt: str = "",
        name: str = "",
        description: str = "",
        pattern: str | re.Pattern[str] | None = None,
        default: PromptType | None = None,
        choices: tuple[str, ...] | None = None,
    ) -> PromptType:
        _prompt = cls(
            prompt or f"Enter {name}:",
            name=name,
            description=description,
            pattern=pattern,
            default=default,
            choices=choices,
        )
        return await _prompt()


class EnvConfirmPrompt(BaseEnvPrompt[bool]):
    async def get_input(self) -> bool:
        return bool(await questionary.confirm(self.prompt, default=bool(self.default)).unsafe_ask_async())


class EnvPasswordPrompt(BaseEnvPrompt[str]):
    async def get_input(self) -> str:
        return str(await questionary.password(self.prompt, default=self.default or "").unsafe_ask_async())


class EnvSelectPrompt(BaseEnvPrompt[str]):
    async def get_input(self) -> str:
        return str(await questionary.select(self.prompt, choices=self.choices, default=self.default).unsafe_ask_async())


class EnvTextPrompt(BaseEnvPrompt[str]):
    async def get_input(self) -> str:
        return str(
            await questionary.text(
                self.prompt,
                default=self.default or "",
                validate=self.validator,
            ).unsafe_ask_async(),
        )


async def prompt_env(
    prompt: str,
    name: str,
    description: str = "",
    default: str | bool | None = None,
    pattern: str | None = None,
    choices: list[str] | None = None,
    *,
    is_password: bool = False,
    is_confirm: bool = False,
) -> str | bool:
    console.rule()

    console.print("[bold]Name[/]:", end=" ")
    console.print(name, highlight=False, markup=False)

    re_pattern = re.compile(pattern) if pattern else None
    if re_pattern:
        console.print("[bold]Pattern[/]:", end=" ")
        console.print(re_pattern.pattern, highlight=False, markup=False)

    console.print("[bold]Description[/]:", end=" ")
    console.print(inspect.cleandoc(description), highlight=False, markup=False, end="\n\n")

    prompt_text = prompt or f"Enter {name}"

    if is_confirm:
        return cast("bool", await questionary.confirm(prompt_text, default=bool(default)).unsafe_ask_async())

    if is_password:
        return cast("str", await questionary.password(prompt_text).unsafe_ask_async())

    if isinstance(default, bool):
        default = str(default)

    if choices:
        return cast("str", await questionary.select(prompt_text, choices=choices, default=default).unsafe_ask_async())

    validator = None
    if re_pattern:

        def validate(value: str) -> bool | str:
            value = value.strip()
            if re_pattern and not re_pattern.match(value):
                return "Please enter a value, that matches pattern"
            return True

        validator = validate

    return cast(
        "str",
        await questionary.text(prompt_text, default=default or "", validate=validator).unsafe_ask_async(),
    )
