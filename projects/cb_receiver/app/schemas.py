from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from vkbottle_types.objects import CallbackType


class VkCallback(BaseModel):
    type: CallbackType = Field()
    """Property `CallbackBase.type`."""

    group_id: int = Field()
    """Property `CallbackBase.group_id`."""

    event_id: str = Field()
    """Unique event id. If it passed twice or more - you should ignore it.."""

    v: str = Field()
    """API object version."""

    secret: str | None = Field(default=None)
    """Property `CallbackBase.secret`."""

    object: dict[str, Any] | None = Field(default=None)


class VttTaskType(Enum):
    wall = 0
    playlist = 1
    unknown = 2
