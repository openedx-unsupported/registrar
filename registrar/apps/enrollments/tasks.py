"""
This module contains the celery task definitions for the enrollment project.
"""
from celery import shared_task
from celery.utils.log import get_task_logger

from registrar.apps.jobs.api import post_job_success


log = get_task_logger(__name__)


@shared_task(bind=True)
def debug_task(self, *args, **kwargs):  # pylint: disable=unused-argument
    """
    A task for debugging.  Will dump the context of the task request
    to the log as a DEBUG message.
    """
    log.debug('Request: {0!r}'.format(self.request))


@shared_task(bind=True)
def list_program_enrollments(self, job_id, program_key):  # pylint: disable=unused-argument
    """
    TODO docstring
    """
    # TODO write this
    time.sleep(5)
    post_job_success(job_id, 'https://example.com/{}'.format(program_key))
