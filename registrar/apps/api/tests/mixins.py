"""
Mixins for Registrar API tests.
"""
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
