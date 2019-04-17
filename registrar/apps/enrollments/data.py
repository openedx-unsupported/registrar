"""
Module for syncing data with external services.
"""
from posixpath import join as urljoin
from requests.exceptions import HTTPError

from django.conf import settings

from edx_rest_api_client import client as rest_client


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


def post_lms_program_enrollment(program_uuid, enrollments, client=None):
    """
    Enroll students in a program

    Returns:
        A HTTP response object that includes both response data and status_code
    """
    url = urljoin(settings.LMS_BASE_URL, 'api/program_enrollments/v1/programs/{}/enrollments/').format(program_uuid)

    try:
        return _make_request('POST', url, client, data=enrollments)
    except HTTPError as e:
        response = e.response
        if response.status_code == 422:
            return response
        raise


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
