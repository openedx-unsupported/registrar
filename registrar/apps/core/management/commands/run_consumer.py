""" Management command to run worker that will act on messages  """
import logging

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from registrar.consumer import run_consumer_worker

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    # pylint: disable=missing-docstring

    help = 'Runs a worker to act on messages received from queue.'

    def handle(self, *args, **options):
        run_consumer_worker()
