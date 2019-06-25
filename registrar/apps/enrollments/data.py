"""
Module for syncing data with external services.
"""
import json
import logging
from collections import namedtuple
from datetime import datetime
from itertools import groupby
from posixpath import join as urljoin

from django.conf import settings
from django.core.cache import cache
from edx_rest_api_client import client as rest_client
from requests.exceptions import HTTPError
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_207_MULTI_STATUS,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from registrar.apps.enrollments.constants import (
    ENROLLMENT_ERROR_DUPLICATED,
    ENROLLMENT_ERROR_INTERNAL,
    LMS_ENROLLMENT_WRITE_MAX_SIZE,
    PROGRAM_CACHE_KEY_TPL,
    PROGRAM_CACHE_TIMEOUT,
)
from registrar.apps.enrollments.serializers import (
    CourseEnrollmentSerializer,
    ProgramEnrollmentSerializer,
)


logger = logging.getLogger(__name__)

DISCOVERY_PROGRAM_API_TPL = 'api/v1/programs/{}/'
LMS_PROGRAM_ENROLLMENTS_API_TPL = 'api/program_enrollments/v1/programs/{}/enrollments/'
LMS_PROGRAM_COURSE_ENROLLMENTS_API_TPL = 'api/program_enrollments/v1/programs/{}/courses/{}/enrollments/'


DiscoveryCourseRun = namedtuple(
    'DiscoveryCourseRun',
    ['key', 'external_key', 'title', 'marketing_url'],
)


class DiscoveryProgram(object):
    """
    Data about a program from Course Discovery service.

    Is loaded from Discovery service and cached indefinitely until invalidated.

    Attributes:
        * version (int)
        * loaded (datetime): When data was loaded from Course Discovery
        * uuid (str): Program UUID-4
        * title (str): Program title
        * url (str): Program marketing-url
        * active_curriculum_uuid (str): UUID-4 of active curriculum.
        * course_runs (list[DiscoveryCourseRun]):
            Flattened list of all course runs in program
    """

    # If we change the schema of this class, bump the `class_version`
    # so that all old entries will be ignored.
    class_version = 1

    def __init__(self, **kwargs):
        self.loaded = datetime.now()
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def get(cls, program_uuid, client=None):
        """
        Get a DiscoveryProgram instance, either by loading it from the cache,
        or query the Course Discovery service if it is not in the cache.

        Raises HTTPError if program is not cached and Discover returns error.
        Raises ValidationError if program is not cached and Discovery returns
            data in a format we don't like.
        """
        key = PROGRAM_CACHE_KEY_TPL.format(uuid=program_uuid)
        program = cache.get(key)
        if not (program and program.version == cls.class_version):
            program = cls.load_from_discovery(program_uuid, client)
            cache.set(key, program, PROGRAM_CACHE_TIMEOUT)
        return program

    @classmethod
    def load_from_discovery(cls, program_uuid, client=None):
        """
        Load a DiscoveryProgram instance from the Course Discovery service.

        Raises HTTPError if program is not cached AND Discovery returns error.
        """
        url = urljoin(
            settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/'
        ).format(
            program_uuid
        )
        program_data = _make_request('GET', url, client).json()
        return cls.from_json(program_uuid, program_data)

    @classmethod
    def from_json(cls, program_uuid, program_data):
        """
        Builds a DiscoveryProgram instance from JSON data that has been
        returned by the Course Discovery service.json
        """
        program_title = program_data.get('title')
        program_url = program_data.get('marketing_url')
        # this make two temporary assumptions (zwh 03/19)
        #  1. one *active* curriculum per program
        #  2. no programs are nested within a curriculum
        try:
            curriculum = next(
                c for c in program_data.get('curricula', [])
                if c.get('is_active')
            )
        except StopIteration:
            logger.exception(
                'Discovery API returned no active curricula for program {}'.format(
                    program_uuid
                )
            )
            return DiscoveryProgram(
                version=cls.class_version,
                uuid=program_uuid,
                title=program_title,
                url=program_url,
                active_curriculum_uuid=None,
                course_runs=[],
            )
        active_curriculum_uuid = curriculum.get("uuid")
        course_runs = [
            DiscoveryCourseRun(
                key=course_run.get('key'),
                external_key=course_run.get('external_key'),
                title=course_run.get('title'),
                marketing_url=course_run.get('marketing_url'),
            )
            for course in curriculum.get("courses", [])
            for course_run in course.get("course_runs", [])
        ]
        return DiscoveryProgram(
            version=cls.class_version,
            uuid=program_uuid,
            title=program_title,
            url=program_url,
            active_curriculum_uuid=active_curriculum_uuid,
            course_runs=course_runs,
        )

    def find_course_run(self, course_key):
        """
        Given a course key, return the course_run with that `key` or `external_key`
        """
        for course_run in self.course_runs:
            if course_key == course_run.key or course_key == course_run.external_key:
                return course_run

    def get_external_course_key(self, course_key):
        """
        Given a course key, return the external course key for that course_run.
        The course key passed in may be an external or internal course key.
        """
        course_run = self.find_course_run(course_key)
        if course_run:
            return course_run.external_key

    def get_course_key(self, course_key):
        """
        Given a course key, return the internal course key for that course run.
        The course key passed in may be an external or internal course key.
        """
        course_run = self.find_course_run(course_key)
        if course_run:
            return course_run.key


def get_program_enrollments(program_uuid, client=None):
    """
    Fetches program enrollments from the LMS.

    Arguments:
        program_uuid (str): UUID-4 string

    Returns: list[dict]
        A list of enrollment dictionaries, validated by
        ProgramEnrollmentSerializer.

    Raises:
        - HTTPError if there is an issue communicating with LMS
        - ValidationError if enrollment data from LMS is invalid
    """
    url = _lms_program_enrollment_url(program_uuid)
    enrollments = _get_all_paginated_results(url, client)
    serializer = ProgramEnrollmentSerializer(data=enrollments, many=True)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def get_course_run_enrollments(program_uuid, course_key, client=None):
    """
    Fetches program course run enrollments from the LMS.

    Arguments:
        program_uuid (str): UUID-4 string
        course_key (str): edX course key identifying course run

    Returns: list[dict]
        A list of enrollment dictionaries, validated by
        CourseEnrollmentSerializer.

    Raises:
        - HTTPError if there is an issue communicating with LMS
        - ValidationError if enrollment data from LMS is invalid
    """
    url = _lms_course_run_enrollment_url(program_uuid, course_key)
    enrollments = _get_all_paginated_results(url, client)
    serializer = CourseEnrollmentSerializer(data=enrollments, many=True)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def write_program_enrollments(method, program_uuid, enrollments, client=None):
    """
    Create or update program enrollments in the LMS.

    Returns: See _write_enrollments.
    """
    url = _lms_program_enrollment_url(program_uuid)
    curriculum_uuid = DiscoveryProgram.get(program_uuid).active_curriculum_uuid
    enrollments = enrollments.copy()
    for enrollment in enrollments:
        enrollment['curriculum_uuid'] = curriculum_uuid
    return _write_enrollments(method, url, enrollments, client)


def write_course_run_enrollments(method, program_uuid, course_id, enrollments, client=None):
    """
    Create or update program course enrollments in the LMS.

    Returns: See _write_enrollments.
    """
    url = _lms_course_run_enrollment_url(program_uuid, course_id)
    return _write_enrollments(method, url, enrollments, client)


def _write_enrollments(method, url, enrollments, client=None):
    """
    Arguments:
        method: "POST", "PATCH", or "PUT"
        url: str
        enrollments: list[dict], with at least "student_key" in each dict.
        client (optional)

    Returns:
        tuple(
            good: bool,
            bad: bool,
            results: dict[str: str]
        )
        where:
          * `good` indicates whether at least one enrollment was successful
          * `bad` indicates whether at least one enrollment failed
          * `results` is a dict that maps each student key to a status
            indicating the result of the enrollment operation.
    """
    def key_fn(e):
        return e['student_key']
    # groupby requires sorted input.
    sorted_enrollments = sorted(enrollments, key=key_fn)
    enrollments_by_student = {
        student_key: list(student_enrollments)
        for student_key, student_enrollments
        in groupby(sorted_enrollments, key=key_fn)
    }
    duplicated_student_keys = {
        student_key
        for student_key, student_enrollments in enrollments_by_student.items()
        if len(student_enrollments) > 1
    }
    unique_enrollments = [
        enrollment
        for enrollment in enrollments
        if enrollment['student_key'] not in duplicated_student_keys
    ]
    responses = _do_batched_lms_write(
        method, url, unique_enrollments, LMS_ENROLLMENT_WRITE_MAX_SIZE, client
    )

    good = False
    bad = bool(duplicated_student_keys)
    # By default, mark all enrollments as "internal-error".
    # Under normal circumstances, every processed enrollment will be marked
    # with a status, so if there are any left over, there was indeed an
    # internal error.
    results = {
        student_key: ENROLLMENT_ERROR_INTERNAL
        for student_key in enrollments_by_student
    }
    results.update({
        student_key: ENROLLMENT_ERROR_DUPLICATED
        for student_key in duplicated_student_keys
    })
    for response in responses:
        unexpected_status = False
        unexpected_data = True
        if response.status_code == HTTP_200_OK:
            good = True
        elif response.status_code == HTTP_207_MULTI_STATUS:
            good = True
            bad = True
        elif response.status_code == HTTP_422_UNPROCESSABLE_ENTITY:
            bad = True
        else:
            unexpected_status = True
            bad = True
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = None
        if isinstance(response_data, dict):
            # Only update with student keys that were passed in
            # so we don't get things like "developer_message" in results.
            student_data = {
                student_key: status
                for student_key, status in response_data.items()
                if student_key in results and isinstance(status, str)
            }
            results.update(student_data)
            unexpected_data = not set(response_data).issubset(student_data)
        if unexpected_status or unexpected_data:
            logger.error(
                (
                    "While writing enrollments to LMS, " +
                    "received unexpected response to request {} {}. " +
                    "Status: {}, Body: {}"
                ).format(
                    method, url, response.status_code, response.text
                )
            )
    return good, bad, results


def _lms_program_enrollment_url(program_uuid):
    """
    Given a program UUID, get the LMS URL for program enrollments.
    """
    endpoint_path = LMS_PROGRAM_ENROLLMENTS_API_TPL.format(program_uuid)
    return urljoin(settings.LMS_BASE_URL, endpoint_path)


def _lms_course_run_enrollment_url(program_uuid, course_id):
    """
    Given a program UUID and an edX course ID,
    get the LMS URL for course run enrollments.
    """
    endpoint_path = LMS_PROGRAM_COURSE_ENROLLMENTS_API_TPL.format(
        program_uuid, course_id
    )
    return urljoin(settings.LMS_BASE_URL, endpoint_path)


def _get_all_paginated_results(url, client=None):
    """
    Builds a list of all results from a cursor-paginated endpoint.

    Repeatedly performs request on 'next' URL until 'next' is null.
    """
    if not client:  # pragma: no branch
        client = _get_client(settings.LMS_BASE_URL)
    results = []
    next_url = url
    while next_url:
        response_data = _make_request('GET', next_url, client).json()
        results += response_data['results']
        next_url = response_data.get('next')
    return results


def _do_batched_lms_write(method, url, items, items_per_batch, client=None):
    """
    Make a series of requests to the LMS, each using a
    `items_per_batch`-sized chunk of the list `items` as input data.

    Returns: list[HTTPResonse]
        A list of responses, returned in order of the requests made.
    """
    client = client or _get_client(settings.LMS_BASE_URL)
    responses = []
    for i in range(0, len(items), items_per_batch):
        sub_items = items[i:(i + items_per_batch)]
        try:
            response = _make_request(method, url, client, json=sub_items)
        except HTTPError as e:
            response = e.response
        responses.append(response)
    return responses


def _make_request(method, url, client, **kwargs):
    """
    Helper method to make an http request using
    an authN'd client.
    """
    if method not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:  # pragma: no cover
        raise Exception('invalid http method: ' + method)

    if not client:
        client = _get_client(settings.LMS_BASE_URL)

    response = client.request(method, url, **kwargs)

    if response.status_code >= 200 and response.status_code < 300:
        return response
    else:
        response.raise_for_status()


def _get_client(host_base_url):
    """
    Returns an authenticated edX REST API client.
    """
    client = rest_client.OAuthAPIClient(
        host_base_url,
        settings.BACKEND_SERVICE_EDX_OAUTH2_KEY,
        settings.BACKEND_SERVICE_EDX_OAUTH2_SECRET,
    )
    client._check_auth()  # pylint: disable=protected-access
    if not client.auth.token:  # pragma: no cover
        raise 'No Auth Token'
    return client
