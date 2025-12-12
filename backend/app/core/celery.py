"""
Celery configuration for background task processing.

Usage:
    # In your code
    from app.core.celery import celery_app

    @celery_app.task
    def my_task():
        pass
"""

from celery import Celery
from flask import Flask


def make_celery(app: Flask = None) -> Celery:
    """
    Create and configure Celery instance.

    If Flask app is provided, configures Celery with Flask's config.
    Otherwise, reads from environment variables.
    """
    celery = Celery(
        'app',
        broker=app.config.get('CELERY_BROKER_URL') if app else None,
        backend=app.config.get('CELERY_RESULT_BACKEND') if app else None,
        include=['app.core.tasks']  # Auto-discover tasks
    )

    if app:
        # Update celery config from Flask config
        celery.conf.update(
            broker_url=app.config.get('CELERY_BROKER_URL'),
            result_backend=app.config.get('CELERY_RESULT_BACKEND'),
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=30 * 60,  # 30 minutes
            worker_prefetch_multiplier=1,
            task_acks_late=True,
        )

        class ContextTask(celery.Task):
            """Task that runs within Flask application context."""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery


# Create celery instance - will be configured when Flask app is created
celery_app = Celery('app')


def init_celery(app: Flask) -> Celery:
    """
    Initialize Celery with Flask app.

    Call this from create_app() to configure Celery.
    """
    global celery_app
    celery_app = make_celery(app)
    return celery_app
