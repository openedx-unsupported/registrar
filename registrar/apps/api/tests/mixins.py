"""
Mixins for Registrar API tests.
"""
import json
from time import time

import jwt
from django.conf import settings

JWT_AUTH = 'JWT_AUTH'


class JwtMixin(object):
    """ Mixin with JWT-related helper functions. """

    JWT_ISSUER_OBJ = getattr(settings, JWT_AUTH)['JWT_ISSUERS'][0]

    def generate_token(self, payload, secret=None):
        """Generate a JWT token with the provided payload."""
        secret = secret or self.JWT_ISSUER_OBJ['SECRET_KEY']
        token = jwt.encode(payload, secret)
        return token

    def generate_id_token(self, user, admin=False, ttl=5, **overrides):
        """Generate a JWT id_token that looks like the ones currently
        returned by the edx oauth provider."""

        payload = self.default_payload(user=user, admin=admin, ttl=ttl)
        payload.update(overrides)
        return self.generate_token(payload)

    def default_payload(self, user, admin=False, ttl=5):
        """Generate a bare payload, in case tests need to manipulate
        it directly before encoding."""
        now = int(time())

        return {
            "iss": self.JWT_ISSUER_OBJ['ISSUER'],
            "sub": user.pk,
            "aud": self.JWT_ISSUER_OBJ['AUDIENCE'],
            "nonce": "dummy-nonce",
            "exp": now + ttl,
            "iat": now,
            "preferred_username": user.username,
            "administrator": admin,
            "email": user.email,
            "locale": "en",
            "name": user.full_name,
        }

    def generate_jwt_header(self, user, admin=False, ttl=5, **overrides):
        """Generate a jwt header value for AUTHORIZATION"""
        jwt_token = self.generate_id_token(user, admin, ttl, **overrides).decode('utf-8')
        return 'JWT {token}'.format(token=jwt_token)


class AuthRequestMixin(JwtMixin):
    """
    Mixin with authenticated get/post/put/patch/delete helper functions.

    Expects implementing classes to provide ``self.client`` attribute.

    Also tests that endpoint returns a 401 if unauthenticated.
    """
    # Define in subclasss
    api_root = None  # Prepended to all non-absolute request URLs
    method = None  # Used in test_unauthenticated
    path = None  # Used in test_unauthenticated

    def test_unauthenticated(self):
        response = self.request(self.method, self.api_root + self.path, None)
        self.assertEqual(response.status_code, 401)

    def get(self, path, user):
        """
        Perform a GET on the given path, optionally with a user.
        """
        return self.request('get', path, user)

    def post(self, path, data, user):
        """
        Perform a POST on the given path, optionally with a user.
        """
        return self.request('post', path, user, data)

    def put(self, path, data, user):
        """
        Perform a PUT on the given path, optionally with a user.
        """
        return self.request('put', path, user, data)

    def patch(self, path, data, user):
        """
        Perform a PATCH on the given path, optionally with a user.
        """
        return self.request('patch', path, user, data)

    def delete(self, path, user):
        """
        Perform a DELETE on the given, optionally with a user.
        """
        return self.request('delete', path, user)

    def request(self, method, path, user, data=None):
        """
        Perform an HTTP request of the given method.

        If user is not None, include a JWT auth header.
        """
        kwargs = {'follow': True}
        if user:
            kwargs['HTTP_AUTHORIZATION'] = self.generate_jwt_header(
                user, admin=user.is_staff,
            )
        if data:
            kwargs['data'] = json.dumps(data)
            kwargs['content_type'] = 'application/json'
        if not (path.startswith('http://') or path.startswith('https://')):
            path = self.api_root + path
        return getattr(self.client, method.lower())(path, **kwargs)
