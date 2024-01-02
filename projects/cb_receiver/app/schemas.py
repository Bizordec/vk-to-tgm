from enum import Enum
from typing import Any

from vkbottle_types.objects import CallbackBase


class VkCallback(CallbackBase):
    object: Any | None = None  # noqa: A003


class VttTaskType(Enum):
    wall = 0
    playlist = 1
    unknown = 2
