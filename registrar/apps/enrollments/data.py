"""
Module for syncing data with external services.
"""
import logging
from collections import namedtuple
from datetime import datetime
from posixpath import join as urljoin

from django.conf import settings
from django.core.cache import cache
from edx_rest_api_client import client as rest_client
from requests.exceptions import HTTPError

from registrar.apps.enrollments.constants import PROGRAM_CACHE_KEY_TPL
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
    ['key', 'title', 'marketing_url'],
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
            cache.set(key, program, None)
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
        returned by the Course Discovery service.
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


def write_program_enrollments(program_uuid, enrollments, update=False, client=None):
    """
    Create or update program enrollments in the LMS.

    Returns:
        A HTTP response object that includes both response data and status_code
    """
    url = urljoin(settings.LMS_BASE_URL, LMS_PROGRAM_ENROLLMENTS_API_TPL.format(program_uuid))

    method = 'PATCH' if update else 'POST'

    try:
        return _make_request(method, url, client, json=enrollments)
    except HTTPError as e:
        response = e.response
        if response.status_code == 422:
            return response
        raise


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
    url = urljoin(settings.LMS_BASE_URL, LMS_PROGRAM_ENROLLMENTS_API_TPL.format(program_uuid))
    enrollments = _get_all_paginated_results(url, client)
    serializer = ProgramEnrollmentSerializer(data=enrollments, many=True)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def get_course_run_enrollments(program_uuid, course_id, client=None):
    """
    Fetches program course run enrollments from the LMS.

    Arguments:
        program_uuid (str): UUID-4 string
        course_id (str): edX course key identifying course run

    Returns: list[dict]
        A list of enrollment dictionaries, validated by
        CourseEnrollmentSerializer.

    Raises:
        - HTTPError if there is an issue communicating with LMS
        - ValidationError if enrollment data from LMS is invalid
    """
    url = urljoin(settings.LMS_BASE_URL, LMS_PROGRAM_COURSE_ENROLLMENTS_API_TPL.format(program_uuid, course_id))
    enrollments = _get_all_paginated_results(url, client)
    serializer = CourseEnrollmentSerializer(data=enrollments, many=True)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def write_program_course_enrollments(program_uuid, course_key, enrollments, update=False, client=None):
    """
    Create or update program course enrollments in the LMS.

    Returns:
        A HTTP response object that includes both response data and status_code
    """
    url = urljoin(settings.LMS_BASE_URL, LMS_PROGRAM_COURSE_ENROLLMENTS_API_TPL).format(program_uuid, course_key)

    method = 'PATCH' if update else 'POST'

    try:
        return _make_request(method, url, client, json=enrollments)
    except HTTPError as e:
        response = e.response
        if response.status_code == 422:
            return response
        raise


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
