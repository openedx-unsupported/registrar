"""
Defines the Celery application for the registrar project.
"""

from celery import Celery
from django.conf import settings


app = Celery('registrar')

app.conf.task_protocol = 1
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


if __name__ == '__main__':
    app.start()
