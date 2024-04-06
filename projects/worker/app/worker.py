from celery import Celery
from vtt_common import celeryconfig

worker = Celery()
worker.config_from_object(celeryconfig)
worker.conf.task_routes = {
    "app.main.forward_wall": {
        "queue": "vtt-wall",
    },
    "app.main.forward_playlist": {
        "queue": "vtt-playlist",
    },
}
