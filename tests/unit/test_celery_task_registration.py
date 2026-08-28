"""Regression test: 6 of 15 modules under workers/tasks/ were missing from
config/celery.py's app.conf.include (workers/ isn't a Django app, so
autodiscover_tasks() can't find them) — the worker never registered them,
so every scheduled/dispatched run (GDPR export, DKIM rotation, bounce-rate
monitoring, stuck-message retry, idempotency/audit-log cleanup) published a
message naming a task the worker had no handler for. Confirmed live: the
GDPR export request stayed stuck on "Preparing" indefinitely.

This test is deliberately dynamic (scans the directory) rather than a fixed
list, so a newly added task module that isn't wired in fails immediately."""
from pathlib import Path

from config.celery import app as celery_app

TASKS_DIR = Path(__file__).resolve().parents[2] / "workers" / "tasks"


def _task_module_names():
    return sorted(
        f"workers.tasks.{p.stem}"
        for p in TASKS_DIR.glob("*.py")
        if p.stem != "__init__"
    )


def test_every_task_module_is_in_celery_include():
    missing = [m for m in _task_module_names() if m not in celery_app.conf.include]
    assert not missing, f"Not registered with the Celery app: {missing}"
