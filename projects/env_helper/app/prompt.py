from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING, Generic, TypeVar

from rich.prompt import InvalidResponse
from rich.text import Text

from app.console import console

if TYPE_CHECKING:
    from re import Pattern
    from typing import TextIO

    from rich.text import TextType

PromptType = TypeVar("PromptType", str, bool)


class EnvPromptBase(Generic[PromptType]):
    response_type: type[PromptType]
    default_value: PromptType
    choices: tuple[str, ...] | None = None

    validate_error_message = "[prompt.invalid]Please enter a valid value"
    illegal_choice_message = "[prompt.invalid.choice]Please select one of the available options"
    illegal_match_message = "[prompt.invalid.choice]Please enter a value, that matches pattern"
    prompt_suffix = ": "

    def __init__(
        self,
        prompt: TextType = "",
        *,
        name: str = "",
        description: str = "",
        pattern: str | Pattern[str] | None = None,
        password: bool = False,
        choices: tuple[str, ...] | None = None,
        show_default: bool = True,
        show_choices: bool = True,
    ) -> None:
        self.prompt = Text.from_markup(prompt, style="prompt") if isinstance(prompt, str) else prompt
        self.name = name
        self.description = description
        self.password = password
        if choices is not None:
            self.choices = choices
        self.re_pattern = re.compile(pattern) if pattern and self.choices is None else None
        self.show_default = show_default
        self.show_choices = show_choices

    @classmethod
    def ask(
        cls,
        prompt: TextType = "",
        *,
        name: str = "",
        description: str = "",
        pattern: str | Pattern[str] | None = r"^.+$",
        password: bool = False,
        choices: tuple[str, ...] | None = None,
        show_default: bool = True,
        show_choices: bool = True,
        default: PromptType | None = None,
        stream: TextIO | None = None,
    ) -> PromptType:
        """Shortcut to construct and run a prompt loop and return the result."""
        _prompt = cls(
            prompt or f"Enter {name}",
            name=name,
            description=description,
            pattern=pattern,
            password=password,
            choices=choices,
            show_default=show_default,
            show_choices=show_choices,
        )
        return _prompt(default=default, stream=stream)

    def render_default(self, default: PromptType) -> Text:
        """Turn the supplied default in to a Text instance."""
        return Text(
            text=f"(Default: {'<secret>' if self.password else default})",
            style="prompt.default",
        )

    def make_prompt(self, default: PromptType) -> Text:
        """Make prompt text."""
        prompt = self.prompt.copy()
        prompt.end = ""

        if self.show_choices and self.choices:
            _choices = "/".join(self.choices)
            choices = f"[{_choices}]"
            prompt.append(" ")
            prompt.append(choices, "prompt.choices")

        if default is not None and self.show_default and isinstance(default, self.response_type):
            prompt.append(" ")
            _default = self.render_default(default=default)
            prompt.append(_default)

        prompt.append(self.prompt_suffix)

        return prompt

    @classmethod
    def get_input(
        cls,
        prompt: TextType,
        password: bool,
        stream: TextIO | None = None,
    ) -> str:
        """Get input from user."""
        return console.input(prompt, password=password, stream=stream)

    def check_choice(self, value: str) -> bool:
        """Check value is in the list of valid choices."""
        if self.choices is None:
            raise ValueError("Choices are not set")
        return value in self.choices

    def process_response(self, value: str) -> PromptType:
        """Process response from user, convert to prompt type."""
        value = value.strip()
        try:
            casted_value = self.response_type(value)
        except ValueError as error:
            raise InvalidResponse(self.validate_error_message) from error

        if self.choices is not None and not self.check_choice(value):
            raise InvalidResponse(self.illegal_choice_message)

        if self.re_pattern and not self.re_pattern.match(string=value):
            raise InvalidResponse(self.illegal_match_message)
        return casted_value

    def pre_prompt(self) -> None:
        """Display something before the prompt."""
        console.rule()

        console.print("[bold]Name[/]:", end=" ")
        console.print(self.name, highlight=False, markup=False)

        if self.re_pattern:
            console.print("[bold]Pattern[/]:", end=" ")
            console.print(self.re_pattern.pattern, highlight=False, markup=False)

        console.print("[bold]Description[/]:", end=" ")
        console.print(
            inspect.cleandoc(self.description),
            highlight=False,
            markup=False,
            end="\n\n",
        )

    def __call__(
        self,
        *,
        default: PromptType | None,
        stream: TextIO | None = None,
    ) -> PromptType:
        """Run the prompt loop."""
        self.pre_prompt()
        while True:
            prompt = self.make_prompt(default or self.default_value)
            value = self.get_input(
                prompt,
                password=self.password,
                stream=stream,
            )
            if not value and default is not None:
                return default
            try:
                return_value = self.process_response(value)
            except InvalidResponse as error:
                console.print(error)
                continue
            else:
                return return_value


class EnvPrompt(EnvPromptBase[str]):
    response_type = str
    default_value = ""


class EnvConfirmPrompt(EnvPromptBase[bool]):
    response_type = bool
    default_value = True
    choices = ("y", "n")

    validate_error_message = "[prompt.invalid]Please enter Y or N"

    def render_default(self, default: bool) -> Text:
        """Render the default as (y) or (n) rather than True/False."""
        yes, no = self.choices
        return Text(f"({yes})" if default else f"({no})", style="prompt.default")

    def process_response(self, value: str) -> bool:
        """Convert choices to a bool."""
        value = value.strip().lower()
        if value not in self.choices:
            raise InvalidResponse(self.validate_error_message)
        return value == self.choices[0]
