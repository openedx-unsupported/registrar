"""
Module for syncing data with external services.
"""
from posixpath import join as urljoin
from requests.exceptions import HTTPError

from django.conf import settings
from edx_rest_api_client import client as rest_client

from registrar.apps.enrollments.serializers import (
    ProgramEnrollmentSerializer,
)


def get_client(host_base_url):
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


def get_discovery_program(program_uuid, client=None):
    """
    Fetches program data from discovery service, given a program UUID.
    """
    url = urljoin(settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/').format(program_uuid)
    return _make_request('GET', url, client).json()


def write_program_enrollments(program_uuid, enrollments, update=False, client=None):
    """
    Create or update program enrollments in the LMS.

    Returns:
        A HTTP response object that includes both response data and status_code
    """
    url = urljoin(settings.LMS_BASE_URL, 'api/program_enrollments/v1/programs/{}/enrollments/').format(program_uuid)

    method = 'PATCH' if update else 'POST'

    try:
        return _make_request(method, url, client, data=enrollments)
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
