"""
This module contains the celery task definitions for the enrollment project.
"""
import json
from collections import OrderedDict, namedtuple

from celery import shared_task
from celery.utils.log import get_task_logger
from requests.exceptions import HTTPError
from rest_framework.exceptions import ValidationError
from user_tasks.tasks import UserTask

from registrar.apps.common.tasks import _get_program
from registrar.apps.core.constants import UPLOADS_PATH_PREFIX
from registrar.apps.core.filestore import get_filestore
from registrar.apps.core.jobs import post_job_failure, post_job_success
from registrar.apps.core.utils import serialize_to_csv
from registrar.apps.enrollments import data
from registrar.apps.enrollments.constants import EnrollmentWriteStatus
from registrar.apps.enrollments.serializers import (
    serialize_course_run_enrollments_to_csv,
    serialize_enrollment_results_to_csv,
    serialize_program_enrollments_to_csv,
)
from registrar.apps.enrollments.utils import build_enrollment_job_status_name


log = get_task_logger(__name__)
uploads_filestore = get_filestore(UPLOADS_PATH_PREFIX)


class EnrollmentReadTask(UserTask):
    """
    Base class for enrollment-reading tasks.
    Expects instances to have `program_key` field.
    """

    # pylint: disable=abstract-method

    @classmethod
    def generate_name(cls, arguments_dict):
        """
        Predictably sets name in such a way that other parts of the codebase
        can query for the state of enrollment writing tasks.
        """
        return build_enrollment_job_status_name(
            arguments_dict['program_key'],
            'read',
            cls.__name__,  # Name of specific task.
        )


# pylint: disable=unused-argument
@shared_task(base=EnrollmentReadTask, bind=True)
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


@shared_task(base=EnrollmentReadTask, bind=True)
def list_course_run_enrollments(
        self,
        job_id,
        user_id,
        file_format,
        program_key,
        internal_course_key,
        external_course_key,
):
    """
    A user task for retrieving program course run enrollments from LMS.
    """
    program = _get_program(job_id, program_key)
    if not program:
        return None

    try:
        enrollments = data.get_course_run_enrollments(
            program.discovery_uuid,
            internal_course_key,
            external_course_key,
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


@shared_task(base=EnrollmentReadTask, bind=True)
def list_all_course_run_enrollments(self, job_id, user_id, file_format, program_key):
    """
    A user task for retrieving all course enrollments within a given program from LMS.
    """
    program = _get_program(job_id, program_key)
    if not program:
        return None

    results = []
    for course_run in program.discovery_program.course_runs:
        try:
            enrollments = data.get_course_run_enrollments(
                program.discovery_uuid,
                course_run.key,
                course_run.external_key,
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

        results.extend(enrollments)

    if file_format == 'json':
        serialized = json.dumps(results, indent=4)
    elif file_format == 'csv':
        serialized = serialize_course_run_enrollments_to_csv(results)
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
        """
        return build_enrollment_job_status_name(
            arguments_dict['program_key'],
            'write',
            cls.__name__,  # Name of specific task.
        )


@shared_task(base=EnrollmentWriteTask, bind=True)
def write_program_enrollments(
        self, job_id, user_id, json_filepath, program_key
):
    """
    A user task that reads program enrollment requests from json_filepath,
    writes them to the LMS, and stores a CSV-formatted results file.
    """
    program = _get_program(job_id, program_key)
    if not program:
        return

    requests = _load_enrollment_requests(job_id, program_key, json_filepath)
    if requests is None:
        return

    any_successes, any_failures, response_json = data.write_program_enrollments(
        'PUT', program.discovery_uuid, requests
    )

    if any_successes and any_failures:
        code_str = str(EnrollmentWriteStatus.MULTI_STATUS.value)
    elif any_successes:
        code_str = str(EnrollmentWriteStatus.OK.value)
    elif any_failures:
        code_str = str(EnrollmentWriteStatus.UNPROCESSABLE_ENTITY.value)
    else:
        # This only happens if no enrollments are given.
        code_str = str(EnrollmentWriteStatus.NO_CONTENT.value)

    results_str = serialize_enrollment_results_to_csv(response_json)
    post_job_success(job_id, results_str, "csv", text=code_str)


CourseEnrollmentResponseItem = namedtuple(
    'CourseEnrollmentResponseItem',
    ['course_id', 'student_key', 'status'],
)


@shared_task(base=EnrollmentWriteTask, bind=True)
def write_course_run_enrollments(
        self, job_id, user_id, json_filepath, program_key
):
    """
    A user task that reads course run enrollment requests from json_filepath,
    writes them to the LMS, and stores a CSV-formatted results file.
    """
    program = _get_program(job_id, program_key)
    if not program:
        return

    requests = _load_enrollment_requests(job_id, program_key, json_filepath)
    if requests is None:
        return

    requests_by_course_key = OrderedDict()
    for request in requests:
        requested_course_key = request.pop('course_id')
        if requested_course_key not in requests_by_course_key:
            requests_by_course_key[requested_course_key] = []
        requests_by_course_key[requested_course_key].append(request)

    successes = []
    failures = []
    course_responses = []

    for requested_course_key, course_requests in requests_by_course_key.items():
        # we don't know if the requested key was an external key or internal key,
        # so convert it before making requests to the LMS.
        internal_course_key = program.discovery_program.get_course_key(requested_course_key)

        successes_in_course, failures_in_course, status_by_student_key = data.write_course_run_enrollments(
            'PUT', program.discovery_uuid, internal_course_key, course_requests
        )

        course_responses.extend([
            CourseEnrollmentResponseItem(requested_course_key, student_key, status)._asdict()
            for student_key, status in status_by_student_key.items()
        ])
        successes.append(successes_in_course)
        failures.append(failures_in_course)

    if any(successes) and any(failures):
        code_str = str(EnrollmentWriteStatus.MULTI_STATUS.value)
    elif any(successes):
        code_str = str(EnrollmentWriteStatus.OK.value)
    elif any(failures):
        code_str = str(EnrollmentWriteStatus.UNPROCESSABLE_ENTITY.value)
    else:
        # This only happens if no enrollments are given.
        code_str = str(EnrollmentWriteStatus.NO_CONTENT.value)

    results_str = serialize_to_csv(course_responses, CourseEnrollmentResponseItem._fields, include_headers=True)
    post_job_success(job_id, results_str, "csv", text=code_str)


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
