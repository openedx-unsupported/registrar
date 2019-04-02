"""
This module contains the celery task definitions for the enrollment project.
"""
import time

from celery import shared_task
from celery.utils.log import get_task_logger
from user_tasks.models import UserTaskArtifact
from user_tasks.tasks import UserTask


log = get_task_logger(__name__)


@shared_task(bind=True)
def debug_task(self, *args, **kwargs):  # pylint: disable=unused-argument
    """
    A task for debugging.  Will dump the context of the task request
    to the log as a DEBUG message.
    """
    log.debug('Request: {0!r}'.format(self.request))


@shared_task(base=UserTask, bind=True)
def debug_user_task(self, user_id, text):  # pylint: disable=unused-argument
    """
    A user task for debugging.  Creates user artifact containing given text.
    """
    UserTaskArtifact.objects.create(status=self.status, text=text)


@shared_task(base=UserTask, bind=True)
def list_program_enrollments(self, user_id, program_key, original_url):  # pylint: disable=unused-argument
    """
    A user task for debugging.  Creates user artifact containing given text.
    """
    time.sleep(5)
    UserTaskArtifact.objects.create(status=self.status)
