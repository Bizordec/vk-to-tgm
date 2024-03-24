from __future__ import annotations

import asyncio
from functools import wraps
from typing import TYPE_CHECKING, ParamSpec

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    P = ParamSpec("P")


def async_to_sync(func: Callable[P, Coroutine[None, None, str]]) -> Callable[P, str]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
        return asyncio.run(func(*args, **kwargs))

    return wrapper
