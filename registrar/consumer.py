 """
 Defines the Kombu consumer for the registrar project.
 """
 from __future__ import absolute_import

 from kombu.mixins import ConsumerMixin
 from kombu import Exchange, Queue

 task_exchange = Exchange('course_discovery', type='direct')
 queues = [
     Queue('task_queue', task_exchange, routing_key='task_queue'),
 ]

 class Worker(ConsumerMixin):

     def __init__(self, connection):
         self.connection = connection

     def get_consumers(self, Consumer, channel):
         return [
             Consumer(queues, callbacks=[self.on_message], accept=['json']),
         ]

     def on_message(self, body, message):
         print('RECEIVED MESSAGE: {0!r}'.format(body))
         message.ack()


 if __name__ == '__main__':
     from kombu import Connection
     from kombu.utils.debug import setup_logging
     setup_logging(loglevel='DEBUG')

     with Connection('redis://:password@redis:6379/0') as conn:
         try:
             Worker(conn).run()
         except KeyboardInterrupt:
             print('bye bye')

