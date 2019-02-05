"""
Module for syncing data with external services.
"""
import os
from posixpath import join as urljoin

from django.conf import settings

from edx_rest_api_client import client as rest_client


CLIENT_ID = os.getenv('EDX_REST_API_CLIENT_ID')
CLIENT_SECRET = os.getenv('EDX_REST_API_CLIENT_SECRET')


def get_client(host_base_url):
    """
    Returns an authenticated edX REST API client.
    """
    client = rest_client.OAuthAPIClient(host_base_url, CLIENT_ID, CLIENT_SECRET)
    client._check_auth()  # pylint: disable=protected-access
    if not client.auth.token:
        raise 'No Auth Token'
    return client


REST_CLIENT = get_client(settings.LMS_BASE_URL)


def get_discovery_program(program_uuid):
    """
    Fetches program data from discovery service, given a program UUID.
    """
    url = urljoin(settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}').format(program_uuid)
    return _get_request(url)


def get_lms_user_by_email(email):
    """
    TODO: the LMS doesn't currently expose an endpoint
    to get accounts by email address.  I have an edx-platform
    branch to do this.
    """
    url = urljoin(settings.LMS_BASE_URL, 'api/user/v1/accounts?email={}').format(email)
    return _get_request(url)


# pylint: disable=unused-argument
def enroll_in_course(user, course_id):
    """
    TODO: LMS enrollment API only allows you to enroll
    the currently logged-in user (I think).
    """
    pass


def _get_request(url):
    """
    Helper method to make a GET request using
    an authN'd client.
    """
    response = REST_CLIENT.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()
