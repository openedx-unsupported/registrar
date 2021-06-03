"""
Utils for reading and writing data to other services using REST.
"""
from django.conf import settings
from edx_rest_api_client import client as rest_client
from requests.exceptions import HTTPError


def get_all_paginated_responses(url, client=None, expected_error_codes=None):
    """
    Builds a list of all responses from a cursor-paginated endpoint.

    Repeatedly performs request on 'next' URL until 'next' is null.

    Returns: list[HTTPResonse]
        A list of responses, returned in order of the requests made.
    """
    if not client:  # pragma: no branch
        client = get_client(settings.LMS_BASE_URL)
    if not expected_error_codes:  # pragma: no cover
        expected_error_codes = set()
    responses = []
    next_url = url
    while next_url:
        try:
            response = make_request('GET', next_url, client)
        except HTTPError as e:
            if e.response.status_code in expected_error_codes:
                response = e.response
            else:
                raise e
        responses.append(response)
        next_url = response.json().get('next')
    return responses


def get_all_paginated_results(url, client=None):
    """
    Builds a list of all results from a cursor-paginated endpoint.

    Repeatedly performs request on 'next' URL until 'next' is null.
    """
    if not client:  # pragma: no branch
        client = get_client(settings.LMS_BASE_URL)
    results = []
    next_url = url
    while next_url:
        response_data = make_request('GET', next_url, client).json()
        results += response_data['results']
        next_url = response_data.get('next')
    return results


def do_batched_lms_write(method, url, items, items_per_batch, client=None):
    """
    Make a series of requests to the LMS, each using a
    `items_per_batch`-sized chunk of the list `items` as input data.

    Returns: list[HTTPResonse]
        A list of responses, returned in order of the requests made.
    """
    client = client or get_client(settings.LMS_BASE_URL)
    responses = []
    for i in range(0, len(items), items_per_batch):
        sub_items = items[i:(i + items_per_batch)]
        try:
            response = make_request(method, url, client, json=sub_items)
        except HTTPError as e:
            response = e.response
        responses.append(response)
    return responses


# pylint: disable=inconsistent-return-statements
def make_request(method, url, client, **kwargs):
    """
    Helper method to make an http request using
    an authN'd client.
    """
    if method not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:  # pragma: no cover
        raise Exception('invalid http method: ' + method)

    if not client:
        client = get_client(settings.LMS_BASE_URL)

    response = client.request(method, url, **kwargs)

    if response.status_code >= 200 and response.status_code < 300:
        return response
    else:
        response.raise_for_status()


def get_client(host_base_url):
    """
    Returns an authenticated edX REST API client.
    """
    client = rest_client.OAuthAPIClient(
        host_base_url,
        settings.BACKEND_SERVICE_EDX_OAUTH2_KEY,
        settings.BACKEND_SERVICE_EDX_OAUTH2_SECRET,
    )
    client._ensure_authentication()  # pylint: disable=protected-access
    if not client.auth.token:  # pragma: no cover
        raise Exception('No Auth Token')
    return client
