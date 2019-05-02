"""
Module for syncing data with external services.
"""
from posixpath import join as urljoin

from django.core.cache import cache
from django.conf import settings
from requests.exceptions import HTTPError

from edx_rest_api_client import client as rest_client

from registrar.apps.enrollments.constants import PROGRAM_CACHE_KEY_TPL
from registrar.apps.enrollments.serializers import (
    ProgramEnrollmentSerializer,
)
from registrar.apps.enrollments.utils import get_active_curriculum


class DiscoveryProgram(object):
    """
    Data about a program from Course Discovery service.

    Is loaded from Discovery service and cached indefinitely until invalidated.

    Attributes:
        * uuid (UUID)
        * active_curriculum_uuid (UUID)
        * course_runs (list[dict]), where each dict contains keys:
            - 'course_id'
            - 'course_title'
            - 'course_url'
    """
    version = 0  # Bump to invalidate cache.

    def __init__(self, program_uuid, validated_program_data):
        """
        Initialize from discovery API response dict.
        """
        self.uuid = program_uuid
        active_curriculum = get_active_curriculum(validated_program_data)
        self.active_curriculum_uuid = active_curriculum["uuid"]
        self.course_runs = [
            course_run
            for course_run in course["course_runs"]
            for course in active_curriculum["courses"]
        ]

    @classmethod
    def get(cls, program_uuid, client=None):
        """
        Get a DiscoveryProgram instance, either by loading it from the cache,
        or query the Course Discovery service if it is not in the cache.

        Raises HTTPError if program is not cached and Discover returns error.
        Raises ValidationError if program is not cached and Discovery returns
            data in a format we don't like.
        """
        key = PROGRAM_CACHE_KEY_TPL.format(version=cls.version, uuid=program_uuid)
        program = cache.get(key)
        if not program:
            program = cls._load_from_discovery(program_uuid, client)
            cache.set(version, program, None)
        return program

    @classmethod
    def _load_from_discovery(cls, program_uuid, client=None):
        """
        Load a DiscoveryProgram instance from the Course Discovery service.

        Raises HTTPError if program is not cached and Discover returns error.
        Raises ValidationError if program is not cached and Discovery returns
            data in a format we don't like.
        """
        url = urljoin(
            settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/'
        ).format(
            program_uuid
        )
        try:
            data = _make_request('GET', url, client).json()
        except HTTPError:
            error_string = (
                'Discovery API returned error while fetching data for program {}: {} '.format(
                    uuid, error.response.status_code
                )
            )
            raise Exception(error_string)
        serializer = DiscoveryProgramSerializer(data=data)
        if not serializer.is_valid():
            raise ValidationError(
                "Discovery API returned invalid data for program {}: {}".format(
                    program_uuid, serializer.errors
                )
            )
        return serializer.validated_data


def write_program_enrollments(program_uuid, enrollments, update=False, client=None):
    """
    Create or update program enrollments in the LMS.

    Returns:
        A HTTP response object that includes both response data and status_code
    """
    url = urljoin(settings.LMS_BASE_URL, 'api/program_enrollments/v1/programs/{}/enrollments/').format(program_uuid)

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
    url = urljoin(
        settings.LMS_BASE_URL,
        'api/program_enrollments/v1/programs/{}/enrollments'.format(program_uuid),
    )
    enrollments = _get_all_paginated_results(url, client)
    ProgramEnrollmentSerializer(
        data=enrollments, many=True
    ).is_valid(
        raise_exception=True
    )
    return enrollments


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
    url = urljoin(
        settings.LMS_BASE_URL,
        'api/program_enrollments/v1/programs/{}/courses/{}/enrollments'.format(
            program_uuid, course_id
        ),
    )
    enrollments = _get_all_paginated_results(url, client)
    CourseEnrollmentSerializer(
        data=enrollments, many=True
    ).is_valid(
        raise_exception=True
    )
    return enrollments


def _get_all_paginated_results(url, client=None):
    """
    Builds a list of all results from a cursor-paginated endpoint.

    Repeatedly performs request on 'next' URL until 'next' is null.
    """
    if not client:
        client = get_client(settings.LMS_BASE_URL)
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
    if method not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
        raise Exception('invalid http method: ' + method)

    if not client:
        client = get_client(settings.LMS_BASE_URL)

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
        settings.BACKEND_SERVICE_EDX_OAUTH2_SECRET
    )
    client._check_auth()  # pylint: disable=protected-access
    if not client.auth.token:
        raise 'No Auth Token'
    return client
