from __future__ import annotations

from typing import TYPE_CHECKING

from celery.app.task import Context
from celery.signals import before_task_publish

if TYPE_CHECKING:
    from typing import Any, TypedDict

    from celery.backends.base import BaseKeyValueStoreBackend

    from vtt_common.schemas import VttTaskType

    class TaskMeta(TypedDict):
        status: str


def set_task_sent_state_handler(backend: BaseKeyValueStoreBackend) -> None:
    @before_task_publish.connect(weak=False)
    def set_sent_state(
        headers: dict,
        body: tuple[dict, dict, dict],
        routing_key: str,
        **kwargs: Any,
    ) -> None:
        backend.store_result(
            task_id=headers["id"],
            result=None,
            state="SENT",
            request=Context(
                task=headers["task"],
                args=body[0],
                kwargs=body[1],
                delivery_info={
                    "routing_key": routing_key,
                },
            ),
            **kwargs,
        )

def get_queued_task(
    backend: BaseKeyValueStoreBackend,
    task_type: VttTaskType,
    owner_id: int,
    post_id: int,
) -> TaskMeta | None:
    result = backend.get(backend.get_key_for_task(f"{task_type}_{owner_id}_{post_id}"))
    if not result:
        return None

    return backend.decode_result(result)
