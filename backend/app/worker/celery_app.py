"""
rKYC Celery Application
Celery worker configuration for background task processing
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.core.config import settings

# Create Celery application
celery_app = Celery(
    "rkyc_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="Asia/Seoul",
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_acks_late=True,  # Acknowledge after task completion

    # Timeouts
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit

    # Worker settings
    worker_prefetch_multiplier=1,  # For long-running tasks
    worker_concurrency=2,  # Number of concurrent workers

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Task queues
    task_queues=[
        Queue("high", routing_key="high"),
        Queue("default", routing_key="default"),
        Queue("low", routing_key="low"),
    ],
    task_default_queue="default",
    task_default_routing_key="default",

    # Retry settings
    task_default_retry_delay=60,  # 1 minute default retry delay
    task_max_retries=3,

    # ===========================================
    # Celery Beat Schedule (Periodic Tasks)
    # ===========================================
    beat_schedule={
        # Full scan of all corporations - every 6 hours
        "scan-all-corporations-every-6-hours": {
            "task": "scan_all_corporations",
            "schedule": crontab(minute=0, hour="*/6"),  # 00:00, 06:00, 12:00, 18:00
            "options": {"queue": "default"},
        },

        # High-risk corporations scan - every hour
        "scan-high-risk-every-hour": {
            "task": "scan_high_risk_corporations",
            "schedule": crontab(minute=30),  # Every hour at :30
            "options": {"queue": "high"},
        },

        # Profile refresh for expiring profiles - every hour
        "refresh-expiring-profiles-hourly": {
            "task": "refresh_expiring_profiles",
            "schedule": crontab(minute=15),  # Every hour at :15
            "options": {"queue": "low"},
        },

        # Cleanup old jobs - daily at 3 AM
        "cleanup-old-jobs-daily": {
            "task": "cleanup_old_jobs",
            "schedule": crontab(minute=0, hour=3),
            "args": (30,),  # Keep jobs for 30 days
            "options": {"queue": "low"},
        },
    },
)

# Auto-discover tasks in the tasks module
celery_app.autodiscover_tasks(["app.worker.tasks"])
