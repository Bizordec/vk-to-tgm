from __future__ import annotations

from enum import StrEnum
from typing import Any, TypedDict

from pydantic import BaseModel, Field


class CallbackServerDict(TypedDict):
    id: int
    title: str


class GetCallbackServersResponse(TypedDict):
    count: int
    items: list[CallbackServerDict]


class AddCallbackServerResponse(TypedDict):
    server_id: int


class GetConfirmationCodeResponse(TypedDict):
    code: str


class CallbackType(StrEnum):
    CONFIRMATION = "confirmation"
    WALL_POST_NEW = "wall_post_new"


class WallPostType(StrEnum):
    POST = "post"
    COPY = "copy"
    REPLY = "reply"
    POSTPONE = "postpone"
    SUGGEST = "suggest"
    POST_ADS = "post_ads"
    PHOTO = "photo"
    VIDEO = "video"
    CLIP = "clip"


class WallWallpostDonut(BaseModel):
    """Info about paid wall post. Model: `WallWallpostDonut`."""

    is_donut: bool = Field()
    """Post only for dons."""


class WallWallpostFull(BaseModel):
    """Model: `WallWallpostFull`."""

    owner_id: int | None = Field(default=None)
    """Wall owner's ID."""

    id: int | None = Field(default=None)
    """Post ID."""

    marked_as_ads: bool | None = Field(default=None)
    """Information whether the post is marked as ads."""

    donut: WallWallpostDonut | None = Field(default=None)
    """Property `WallWallpostFull.donut`."""

    post_type: WallPostType | None = Field(default=None)
    """Property `WallWallpost.post_type`."""


class VkCallback(BaseModel):
    """Model: `VkCallback`."""

    type: CallbackType | str = Field()
    """Property `VkCallback.type`."""

    group_id: int = Field()
    """Property `VkCallback.group_id`."""

    event_id: str = Field()
    """Unique event id. If it passed twice or more - you should ignore it.."""

    v: str = Field()
    """API object version."""

    secret: str | None = Field(default=None)
    """Property `VkCallback.secret`."""

    object: dict[str, Any] | None = Field(default=None)
    """Property `VkCallback.object`."""
