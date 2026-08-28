"""Regression test for a production incident: every task in workers/tasks/
is dispatched via plain .delay() with no queue kwarg, so without an explicit
task_default_queue they all silently route to Celery's built-in default
queue name ("celery") — which the worker container never consumes from
(Dockerfile.celery only listens on `-Q default,emails,webhooks`). Confirmed
live: 100k+ backlogged, never-processed messages sitting in that queue,
including outbound send_email_task calls."""
from django.conf import settings

from config.celery import app as celery_app


def test_default_queue_setting_matches_a_queue_the_worker_consumes():
    # Dockerfile.celery: celery worker -Q default,emails,webhooks
    worker_queues = {"default", "emails", "webhooks"}
    assert settings.CELERY_TASK_DEFAULT_QUEUE in worker_queues


def test_celery_app_picked_up_the_default_queue_setting():
    # Guards against a typo/renamed setting silently breaking the CELERY_
    # namespace mapping in config/celery.py (config_from_object(... namespace="CELERY")).
    assert celery_app.conf.task_default_queue == settings.CELERY_TASK_DEFAULT_QUEUE
