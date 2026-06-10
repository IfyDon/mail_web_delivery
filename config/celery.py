import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('web_mail')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# workers/ is not a Django app so autodiscover_tasks() won't find it automatically.
# Explicitly include every task module so the worker registers them all.
app.conf.include = [
    'workers.tasks.send_email',
    'workers.tasks.webhook_dispatch',
    'workers.tasks.dispatch_scheduled',
    'workers.tasks.cleanup',
    'workers.tasks.domain_verify',
    'workers.tasks.process_events',
    'workers.tasks.aggregate_stats',
    'workers.tasks.reset_quota',
    'workers.tasks.decay_scores',
]
