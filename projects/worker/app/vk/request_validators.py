from typing import Any

from vkbottle import ABCRequestValidator

from app.config import settings


class VkLangRequestValidator(ABCRequestValidator):
    async def validate(self, request: dict[str, Any]) -> dict[str, Any]:
        request["lang"] = settings.VTT_LANGUAGE
        return request
