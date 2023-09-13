from registrar.settings.local import *
from registrar.settings.utils import get_logger_config


ALLOWED_HOSTS = ['*']

LOGGING = get_logger_config(debug=True, dev_env=True, local_loglevel='DEBUG')
del LOGGING['handlers']['local']

SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')
LANGUAGE_CODE = os.environ.get('LANGUAGE_CODE', 'en')

CELERY_TASK_ALWAYS_EAGER = (
    os.environ.get("CELERY_ALWAYS_EAGER", "false").lower() == "true"
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': os.environ.get('CACHE_LOCATION', 'memcached:11211'),
        "OPTIONS": {"no_delay": True, "ignore_exc": True, "use_pooling": True},
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'regsitrar'),
        'USER': os.environ.get('DB_USER', 'regsitrar001'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'password'),
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', 3306),
        'ATOMIC_REQUESTS': False,
        'CONN_MAX_AGE': 60,
    }
}

STATICFILES_STORAGE = os.environ.get('STATICFILES_STORAGE', 'django.contrib.staticfiles.storage.StaticFilesStorage')
STATIC_URL = os.environ.get('STATIC_URL', '/static/')

LMS_BASE_URL = 'http://edx.devstack.lms:18000'
DISCOVERY_BASE_URL = 'http://edx.devstack.discovery:18381'

# Set these to the correct values for your OAuth2/OpenID Connect provider (e.g., devstack)
SOCIAL_AUTH_EDX_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_KEY', 'registrar-sso-key')
SOCIAL_AUTH_EDX_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_SECRET', 'registrar-sso-secret')
SOCIAL_AUTH_EDX_OAUTH2_ISSUER = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_ISSUER', 'http://localhost:18000')
SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT', 'http://edx.devstack.lms:18000')
SOCIAL_AUTH_EDX_OAUTH2_LOGOUT_URL = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_LOGOUT_URL', 'http://localhost:18000/logout')
SOCIAL_AUTH_EDX_OAUTH2_PUBLIC_URL_ROOT = os.environ.get(
    'SOCIAL_AUTH_EDX_OAUTH2_PUBLIC_URL_ROOT', 'http://localhost:18000',
)

# OAuth2 variables specific to backend service API calls.
BACKEND_SERVICE_EDX_OAUTH2_KEY = os.environ.get('BACKEND_SERVICE_EDX_OAUTH2_KEY', 'registrar-backend-service-key')
BACKEND_SERVICE_EDX_OAUTH2_SECRET = os.environ.get('BACKEND_SERVICE_EDX_OAUTH2_SECRET', 'registrar-backend-service-secret')
BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL = os.environ.get(
    'BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL', 'http://edx.devstack.lms:18000/oauth2',
)

JWT_AUTH['JWT_ISSUERS'].append({
    'AUDIENCE': 'lms-key',
    'ISSUER': 'http://localhost:18000/oauth2',
    'SECRET_KEY': 'lms-secret',
})

JWT_AUTH.update({
    # Must match public signing key used in LMS.
    'JWT_PUBLIC_SIGNING_JWK_SET': (
        '{"keys": [{"kid": "devstack_key", "e": "AQAB", "kty": "RSA", "n": "smKFSYowG6nNUAdeqH1jQQnH1PmIHphzBmwJ5vRf1vu'
        '48BUI5VcVtUWIPqzRK_LDSlZYh9D0YFL0ZTxIrlb6Tn3Xz7pYvpIAeYuQv3_H5p8tbz7Fb8r63c1828wXPITVTv8f7oxx5W3lFFgpFAyYMmROC'
        '4Ee9qG5T38LFe8_oAuFCEntimWxN9F3P-FJQy43TL7wG54WodgiM0EgzkeLr5K6cDnyckWjTuZbWI-4ffcTgTZsL_Kq1owa_J2ngEfxMCObnzG'
        'y5ZLcTUomo4rZLjghVpq6KZxfS6I1Vz79ZsMVUWEdXOYePCKKsrQG20ogQEkmTf9FT_SouC6jPcHLXw"}]}'
    ),
})

SEGMENT_KEY = os.environ.get('SEGMENT_KEY', None)

#####################################################################
# Lastly, see if the developer has any local overrides.
if os.path.isfile(join(dirname(abspath(__file__)), 'private.py')):
    from .private import *  # pylint: disable=import-error

API_ROOT = 'http://localhost:18734/api'
