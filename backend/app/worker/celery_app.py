# Celery Application
# TODO: Implement in Session 3

"""
from celery import Celery

app = Celery(
    'rkyc_worker',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    task_queues=[
        Queue('high', routing_key='high'),
        Queue('default', routing_key='default'),
        Queue('low', routing_key='low'),
    ]
)
"""
