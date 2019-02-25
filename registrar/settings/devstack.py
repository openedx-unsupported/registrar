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


#####################################################################
# Lastly, see if the developer has any local overrides.
if os.path.isfile(join(dirname(abspath(__file__)), 'private.py')):
    from .private import *  # pylint: disable=import-error
