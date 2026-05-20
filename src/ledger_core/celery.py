import os
from celery import Celery

os.environ.setdefault("DJANGO_ENV", "prod")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledger_core.settings")

app = Celery("ledger_core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
