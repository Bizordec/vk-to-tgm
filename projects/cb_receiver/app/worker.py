from celery import Celery
from vtt_common import celeryconfig

app = Celery()
app.config_from_object(celeryconfig)
