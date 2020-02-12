"""
Defines the Kombu consumer for the registrar project.
"""
from __future__ import absolute_import

from kombu import Exchange, Queue
from kombu.mixins import ConsumerMixin

from registrar.apps.core.models import Program


class ProgramConsumer(ConsumerMixin):
    """
    Class to define Kombu consumer behavior.
    Consumer Queue binds to an exchange and handles messages from corresponding Producers.
    """
    exchange = Exchange('course_discovery', type='direct')
    queues = [
        Queue('task_queue', exchange, routing_key='task_queue'),
    ]

    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(self.queues, callbacks=[self.on_message], accept=['json']),
        ]

    def on_message(self, body, message):
        print(Program.objects.first())
        print('RECEIVED MESSAGE: {0!r}'.format(body))

        message.ack()
