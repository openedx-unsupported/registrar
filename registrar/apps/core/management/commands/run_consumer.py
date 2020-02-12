""" Management command to run worker that will act on messages  """
import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from kombu import Connection
from kombu.utils.debug import setup_logging

from registrar.apps.core.consumers import ProgramConsumer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    # pylint: disable=missing-docstring

    help = 'Runs a worker to act on messages received from queue.'

    def handle(self, *args, **options):
        setup_logging(loglevel='DEBUG')

        with Connection(settings.BROKER_URL) as conn:
         try:
             ProgramConsumer(conn).run()
         except KeyboardInterrupt:
             print('bye bye')

