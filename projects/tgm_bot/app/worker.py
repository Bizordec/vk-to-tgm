from celery import Celery
from vtt_common import celeryconfig
from vtt_common.tasks import set_task_sent_state_handler

app = Celery()
app.config_from_object(celeryconfig)

set_task_sent_state_handler(backend=app.backend)
