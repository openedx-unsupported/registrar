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

from registrar.apps.core.constants import UPLOADS_PATH_PREFIX
from registrar.apps.core.filestore import get_filestore
from registrar.apps.core.jobs import post_job_failure, post_job_success
from registrar.apps.enrollments import data
from registrar.apps.enrollments.models import Program
from registrar.apps.enrollments.serializers import (
    serialize_course_run_enrollments_to_csv,
    serialize_enrollment_results_to_csv,
    serialize_program_enrollments_to_csv,
)
from registrar.apps.enrollments.utils import build_enrollment_job_status_name


log = get_task_logger(__name__)
uploads_filestore = get_filestore(UPLOADS_PATH_PREFIX)


# pylint: disable=unused-argument


@shared_task(base=UserTask, bind=True)
def list_program_enrollments(self, job_id, user_id, file_format, program_key):
    """
    A user task for retrieving program enrollments from LMS.
    """
    program = _get_program(job_id, program_key)
    if not program:
        return None

    try:
        enrollments = data.get_program_enrollments(program.discovery_uuid)
    except HTTPError as err:
        post_job_failure(
            job_id,
            "HTTP error {} when getting enrollments at {}".format(
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
    post_job_success(job_id, serialized, file_format)


@shared_task(base=UserTask, bind=True)
def list_course_run_enrollments(
        self, job_id, user_id, file_format, program_key, course_key   # pylint: disable=unused-argument
):
    """
    A user task for retrieving program course run enrollments from LMS.
    """
    program = _get_program(job_id, program_key)
    if not program:
        return None

    try:
        enrollments = data.get_course_run_enrollments(
            program.discovery_uuid, course_key
        )
    except HTTPError as err:
        post_job_failure(
            job_id,
            "HTTP error {} when getting enrollments at {}".format(
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
        serialized = serialize_course_run_enrollments_to_csv(enrollments)
    else:
        raise ValueError('Invalid file_format: {}'.format(file_format))
    post_job_success(job_id, serialized, file_format)


class EnrollmentWriteTask(UserTask):
    """
    Base class for enrollment-writing tasks.
    Expects instances to have `program_key` field.
    """

    # pylint: disable=abstract-method

    @classmethod
    def generate_name(cls, arguments_dict):
        """
        Predictably sets name in such a way that other parts of the codebase
        can query for the state of enrollment writing tasks.
        The format is "$program_key:$task_function_name".
        """
        return build_enrollment_job_status_name(
            arguments_dict['program_key'],
            cls.__name__,  # Name of specific task.
        )


@shared_task(base=EnrollmentWriteTask, bind=True)
def write_program_enrollments(
        self, job_id, user_id, json_filepath, program_key
):
    """
    A user task that reads program enrollment requests from json_filepath,
    and writes them to the LMS.
    """
    program = _get_program(job_id, program_key)
    if not program:
        return None
    requests = _load_enrollment_requests(job_id, program_key, json_filepath)
    if requests is None:
        return
    good, bad, results = data.write_program_enrollments(
        'PUT', program.discovery_uuid, requests
    )
    results_str = serialize_enrollment_results_to_csv(results)
    if good and bad:
        code_str = "207 Multi-Status"
    elif good:
        code_str = "200 OK"
    elif bad:
        code_str = "422 Unprocessable Entity"
    else:
        # This only happens if no enrollments are given.
        code_str = "204 No Content"
    post_job_success(job_id, results_str, "csv", text=code_str)


@shared_task(base=EnrollmentWriteTask, bind=True)
def write_course_run_enrollments(
        self, job_id, user_id, json_filepath, program_key
):
    """
    A user task that reads course enrollment requests from json_filepath,
    and writes them to the LMS.
    """
    post_job_failure(  # pragma: no cover
        job_id,
        "not implemented",
    )
    return  # pragma: no cover


def _load_enrollment_requests(job_id, program_key, json_filepath):
    """
    Load enrollment reqeusts from JSON file.

    If file doesn't exist or isn't valid JSON, post job failure and retrurn None.
    Else, return data loaded from JSON.
    """
    json_text = uploads_filestore.retrieve(json_filepath)
    if not json_text:
        post_job_failure(
            job_id,
            "Enrollment file for program_key={} not found at {}".format(
                program_key, json_filepath
            )
        )
        return None
    try:
        return json.loads(json_text)
    except json.decoder.JSONDecodeError:
        post_job_failure(
            job_id,
            "Enrollment file for program_key={} at {} is not valid JSON".format(
                program_key, json_filepath
            )
        )
        return None


def _get_program(job_id, program_key):
    """
    Load a Program by key. Fails job and returns None if key invalid.
    """
    try:
        return Program.objects.get(key=program_key)
    except Program.DoesNotExist:
        post_job_failure(job_id, "Bad program key: {}".format(program_key))
        return None


@shared_task(bind=True)
def debug_task(self, *args, **kwargs):
    """
    A task for debugging.  Will dump the context of the task request
    to the log as a DEBUG message.
    """
    log.debug('Request: {0!r}'.format(self.request))


@shared_task(base=UserTask, bind=True)
def debug_user_task(self, user_id, text):
    """
    A user task for debugging.  Creates user artifact containing given text.
    """
    UserTaskArtifact.objects.create(status=self.status, text=text)
