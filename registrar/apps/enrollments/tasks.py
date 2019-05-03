"""
This module contains the celery task definitions for the enrollment project.
"""
import json

from celery import shared_task
from celery.utils.log import get_task_logger
from requests.exceptions import HTTPError
from rest_framework.exceptions import ValidationError
from user_tasks.models import UserTaskArtifact
from user_tasks.tasks import UserTask


from registrar.apps.core.jobs import post_job_failure, post_job_success
from registrar.apps.enrollments.data import get_program_enrollments
from registrar.apps.enrollments.models import Program
from registrar.apps.enrollments.serializers import serialize_program_enrollments_to_csv


log = get_task_logger(__name__)


@shared_task(base=UserTask, bind=True)
def list_program_enrollments(self, job_id, user_id, program_key, file_format):  # pylint: disable=unused-argument
    """
    A user task for debugging.  Creates user artifact containing given text.
    """
    try:
        program = Program.objects.get(key=program_key)
    except Program.DoesNotExist:
        post_job_failure(job_id, "Bad program key: {}".format(program_key))
        return

    try:
        enrollments = get_program_enrollments(program.discovery_uuid)
    except HTTPError as err:
        post_job_failure(
            job_id,
            "HTTP error {} on when getting enrollments at {}".format(
                err.response.status_code, err.request.url
            ),
        )
        return
    except ValidationError as err:
        post_job_failure(
            job_id,
            "Invalid enrollment data from LMS: {}".format(err),
        )
        return

    if file_format == 'json':
        serialized = json.dumps(enrollments, indent=4)
    elif file_format == 'csv':
        serialized = serialize_program_enrollments_to_csv(enrollments)
    else:
        raise ValueError('Invalid file_format: {}'.format(file_format))
    post_job_success(self.request.id, serialized, file_format)


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
