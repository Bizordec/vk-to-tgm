from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class State(Enum):
    WAITING_FOR_LINK = auto()
    LINK_SENT = auto()
    WAITING_FOR_CHOISE = auto()


class StateManager:
    def __init__(self) -> None:
        self._states: dict[int, tuple[State, dict[str, Any]]] = {}

    def get_info(self, sender_id: int) -> tuple[State, dict[str, Any]]:
        info = self._states.get(sender_id)
        if not info:
            info = (State.WAITING_FOR_LINK, {})
            self._states[sender_id] = info
        return info

    def set_info(self, sender_id: int, state: State, data: dict[str, Any] | None = None) -> None:
        self._states[sender_id] = (state, data or {})

    def clear_info(self, sender_id: int) -> None:
        self._states.pop(sender_id, None)


state_manager = StateManager()
