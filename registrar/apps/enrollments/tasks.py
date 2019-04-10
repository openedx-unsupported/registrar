"""
This module contains the celery task definitions for the enrollment project.
"""
from celery import shared_task
from celery.utils.log import get_task_logger


log = get_task_logger(__name__)


@shared_task(bind=True)
def debug_task(self, *args, **kwargs):  # pylint: disable=unused-argument
    """
    A task for debugging.  Will dump the context of the task request
    to the log as a DEBUG message.
    """
    log.debug('Request: {0!r}'.format(self.request))
