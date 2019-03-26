"""
Defines the Celery application for the registrar project.
"""
from __future__ import absolute_import

from celery import Celery
from django.conf import settings


app = Celery('registrar')

app.config_from_object(settings)
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


if __name__ == '__main__':
    app.start()
