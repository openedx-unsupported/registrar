""" Tasks for the grades app """
import json

from celery import shared_task
from requests.exceptions import HTTPError
from rest_framework.exceptions import ValidationError
from user_tasks.tasks import UserTask

from registrar.apps.common.tasks import _get_program
from registrar.apps.core.jobs import post_job_failure, post_job_success
from registrar.apps.grades import data
from registrar.apps.grades.constants import GradeReadStatus
from registrar.apps.grades.serializers import serialize_course_run_grades_to_csv


@shared_task(base=UserTask, bind=True)
# pylint: disable=unused-argument
def get_course_run_grades(self, job_id, user_id, file_format, program_key, internal_course_key):
    """
    A user task that reads course run enrollment requests from json_filepath,
    writes them to the LMS, and stores a CSV-formatted results file.
    """
    program = _get_program(job_id, program_key)
    if not program:
        return
    try:
        good, bad, grades = data.get_course_run_grades(
            program.discovery_uuid,
            internal_course_key,
        )
    except HTTPError as err:
        post_job_failure(
            job_id,
            "HTTP error {} when getting grades at {}".format(
                err.response.status_code, err.request.url
            ),
        )
        return
    except ValidationError as err:
        post_job_failure(
            job_id,
            "Invalid grade data from LMS: {}".format(err),
        )
        return

    if good and bad:
        code_str = str(GradeReadStatus.MULTI_STATUS.value)
    elif not good and not bad:
        code_str = str(GradeReadStatus.NO_CONTENT.value)
    elif good:
        code_str = str(GradeReadStatus.OK.value)
    else:
        code_str = str(GradeReadStatus.UNPROCESSABLE_ENTITY.value)

    if file_format == 'json':
        serialized = json.dumps(grades, indent=4)
    elif file_format == 'csv':
        serialized = serialize_course_run_grades_to_csv(grades)
    else:
        raise ValueError('Invalid file_format: {}'.format(file_format))
    post_job_success(job_id, serialized, file_format, text=code_str)
