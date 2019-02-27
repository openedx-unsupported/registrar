from registrar.settings.local import *
from registrar.settings.utils import get_logger_config


ALLOWED_HOSTS = ['*']

LOGGING = get_logger_config(debug=True, dev_env=True, local_loglevel='DEBUG')
del LOGGING['handlers']['local']

SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')
LANGUAGE_CODE = os.environ.get('LANGUAGE_CODE', 'en')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': os.environ.get('CACHE_LOCATION', 'memcached:12211'),
    }
}

REGISTRAR_SERVICE_USER = os.environ.get('REGISTRAR_SERVICE_USER', 'registrar_service_user')

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

JWT_AUTH = {
    'JWT_ISSUERS': [
        {
            'AUDIENCE': 'lms-key',
            'ISSUER': 'http://edx.devstack.lms:18000/oauth2',
            'SECRET_KEY': 'lms-secret',
        },
    ],
}
JWT_AUTH = {
    'JWT_ALGORITHM': 'HS256',
    'JWT_DECODE_HANDLER': 'edx_rest_framework_extensions.auth.jwt.decoder.jwt_decode_handler',
    'JWT_VERIFY_AUDIENCE': False,
    'JWT_AUTH_COOKIE': 'edx-jwt-cookie',
    'JWT_ISSUERS': [
        {
            'AUDIENCE': 'lms-key',
            'ISSUER': 'http://localhost:18000/oauth2',
            'SECRET_KEY': 'lms-secret',
        },
    ],
}
JWT_AUTH.update({
    # Must match public signing key used in LMS.
    'JWT_PUBLIC_SIGNING_JWK_SET': (
        '{"keys": [{"kid": "devstack_key", "e": "AQAB", "kty": "RSA", "n": "smKFSYowG6nNUAdeqH1jQQnH1PmIHphzBmwJ5vRf1vu'
        '48BUI5VcVtUWIPqzRK_LDSlZYh9D0YFL0ZTxIrlb6Tn3Xz7pYvpIAeYuQv3_H5p8tbz7Fb8r63c1828wXPITVTv8f7oxx5W3lFFgpFAyYMmROC'
        '4Ee9qG5T38LFe8_oAuFCEntimWxN9F3P-FJQy43TL7wG54WodgiM0EgzkeLr5K6cDnyckWjTuZbWI-4ffcTgTZsL_Kq1owa_J2ngEfxMCObnzG'
        'y5ZLcTUomo4rZLjghVpq6KZxfS6I1Vz79ZsMVUWEdXOYePCKKsrQG20ogQEkmTf9FT_SouC6jPcHLXw"}]}'
    ),
})


#####################################################################
# Lastly, see if the developer has any local overrides.
if os.path.isfile(join(dirname(abspath(__file__)), 'private.py')):
    from .private import *  # pylint: disable=import-error
