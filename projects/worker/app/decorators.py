from __future__ import annotations

import asyncio
from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


def async_to_sync[**P](func: Callable[P, Coroutine[None, None, str]]) -> Callable[P, str]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
        return asyncio.run(func(*args, **kwargs))

    return wrapper
