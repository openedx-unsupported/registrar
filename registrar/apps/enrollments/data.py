"""
Module for syncing data with external services.
"""
from posixpath import join as urljoin

from django.conf import settings
from edx_rest_api_client import client as rest_client
from user_tasks.models import UserTaskStatus

from registrar.apps.enrollments.tasks import list_program_enrollments


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
    return _get_request(url, client)


def get_lms_user_by_email(email, client=None):
    """
    TODO: the LMS doesn't currently expose an endpoint
    to get accounts by email address.  I have an edx-platform
    branch to do this.
    """
    url = urljoin(settings.LMS_BASE_URL, 'api/user/v1/accounts?email={}').format(email)
    return _get_request(url, client)


def invoke_program_enrollment_listing(user, program_key, original_url):
    """
    TODO docstring
    """
    task_id = list_program_enrollments.delay(
        user.id, program_key, original_url,
    ).task_id
    job_id = UserTaskStatus.objects.get(task_id=task_id).uuid
    return job_id


# pylint: disable=unused-argument
def enroll_in_course(user, course_id, client=None):
    """
    TODO: LMS enrollment API only allows you to enroll
    the currently logged-in user (I think).
    """
    pass


def _get_request(url, client=None):
    """
    Helper method to make a GET request using
    an authN'd client.
    """
    if not client:
        client = get_client(settings.LMS_BASE_URL)

    response = client.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()
