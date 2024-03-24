import os

# Default broker URL.
broker_url = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")

# The backend used to store task results.
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost/0")

# Make task report its status as ‘started’ when executed by a worker.
task_track_started = True

# Kill all long-running tasks with late acknowledgment enabled on connection loss.
worker_cancel_long_running_tasks_on_connection_loss = True

# The maximum number of connections that can be open in the connection pool.
broker_pool_limit = 1

broker_connection_retry_on_startup = True

# Late ack means the task messages
# will be acknowledged after the task has been executed.
task_acks_late = True

# How many messages to prefetch at a time
# multiplied by the number of concurrent processes.
worker_prefetch_multiplier = 1

# A list of routers used to route tasks to queues.
task_routes = {
    "app.celery_worker.forward_wall": {"queue": "vtt-wall"},
    "app.celery_worker.forward_playlist": {"queue": "vtt-playlist"},
}
