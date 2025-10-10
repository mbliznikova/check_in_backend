import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "check_in_backend.settings")

app = Celery("check_in_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()