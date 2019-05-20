""" General utilities for unit tests. """

import json
from functools import wraps

import responses
from django.conf import settings


def mock_oauth_login(fn):
    """
    Mock request to authenticate registrar as a backend client
    """
    # pylint: disable=missing-docstring
    @wraps(fn)
    def inner(self, *args, **kwargs):
        responses.add(
            responses.POST,
            settings.LMS_BASE_URL + '/oauth2/access_token',
            body=json.dumps({'access_token': 'abcd', 'expires_in': 60}),
            status=200
        )
        return fn(self, *args, **kwargs)
    return inner
