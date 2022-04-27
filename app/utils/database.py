import enum
from typing import Optional, Union

from celery import states
from celery.app.task import Context
from celery.backends.database import DatabaseBackend, retry, session_cleanup
from celery.backends.database.models import ResultModelBase, Task
from sqlalchemy import Column, Enum, ForeignKey, Integer, event
from sqlalchemy.engine import Engine
from sqlalchemy.sql.expression import desc


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class VttTaskType(enum.Enum):
    wall = 0
    playlist = 1
    unknown = 2


class VttTask(ResultModelBase):
    __tablename__ = "vtt_task"

    id = Column(Integer, primary_key=True)
    vk_type = Column(Enum(VttTaskType))
    vk_owner_id = Column(Integer)
    vk_id = Column(Integer)
    task_id = Column(Integer, ForeignKey(Task.id, ondelete="CASCADE"))

    def __repr__(self):
        return f"<VttTask type: {self.type} vk_fullid: {self.vk_owner_id}_{self.vk_id} task_id: {self.task_id}>"


@retry
def vtt_store_result(
    vk_type: VttTaskType,
    vk_owner_id: int,
    vk_id: int,
    task_uuid: str,
    result,
    state: str,
    traceback: Optional[str] = None,
    request: Optional[Context] = None,
    **kwargs,
) -> None:
    """Store return value and state of an executed task."""
    from app.celery_worker import worker

    backend: DatabaseBackend = worker.backend
    celery_task = backend.task_cls
    session = backend.ResultSession()
    with session_cleanup(session):
        task = list(session.query(celery_task).filter(celery_task.task_id == task_uuid))
        task = task and task[0]
        if not task:
            task = celery_task(task_uuid)
            task.task_id = task_uuid
            session.add(task)
            session.flush()

            # Add entry to vtt_task table
            session.add(VttTask(vk_type=vk_type.name, vk_owner_id=vk_owner_id, vk_id=vk_id, task_id=task.id))
            session.flush()

        backend._update_result(task, result, state, traceback=traceback, request=request)
        session.commit()


def get_queued_task(vk_owner_id: int, vk_id: int, vk_type: VttTaskType):
    from app.celery_worker import worker

    backend: DatabaseBackend = worker.backend
    celery_task = backend.task_cls
    session = backend.ResultSession()
    with session_cleanup(session):
        queued_task: Union[celery_task, None] = (
            session.query(celery_task)
            .join(VttTask)
            .filter(
                (VttTask.vk_owner_id == vk_owner_id)
                & (VttTask.vk_id == vk_id)
                & (VttTask.vk_type == vk_type.name)
                & ((celery_task.status == "SENT") | (celery_task.status == states.STARTED))
            )
            .order_by(desc(celery_task.date_done))
            .first()
        )
        return queued_task
