"""
Defines the Kombu consumer for the registrar project.
"""
from __future__ import absolute_import

from django.conf import settings
from kombu.mixins import ConsumerMixin
from kombu import Exchange, Queue

from registrar.apps.core.models import Program


class ProgramConsumer(ConsumerMixin):
    exchange = Exchange('course_discovery', type='direct')
    queues = [
        Queue('task_queue', exchange, routing_key='task_queue'),
    ]

    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(queues, callbacks=[self.on_message], accept=['json']),
        ]

    def on_message(self, body, message):
        print(Program.objects.first())
        print('RECEIVED MESSAGE: {0!r}'.format(body))

        message.ack()

