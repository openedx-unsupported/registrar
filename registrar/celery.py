"""
Defines the Celery application for the registrar project.
"""

from celery import Celery


# TEMP: This code will be removed by ARCH-BOM on 4/22/24
# ddtrace allows celery task logs to be traced by the dd agent.
# TODO: remove this code.
try:
    from ddtrace import patch
    patch(celery=True)
except ImportError:
    pass

app = Celery('registrar')

app.conf.task_protocol = 1
app.config_from_object('django.conf:settings', namespace="CELERY")
app.autodiscover_tasks()


if __name__ == '__main__':
    app.start()
