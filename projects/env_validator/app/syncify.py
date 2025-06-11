from __future__ import annotations

import asyncio
from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import ParamSpec, TypeVar

    P = ParamSpec("P")
    Ret = TypeVar("Ret")


def async_to_sync(func: Callable[P, Coroutine[None, None, Ret]]) -> Callable[P, Ret]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Ret:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        coro = func(*args, **kwargs)
        if loop.is_running():
            return loop.create_task(coro).result()

        return loop.run_until_complete(coro)

    return wrapper
