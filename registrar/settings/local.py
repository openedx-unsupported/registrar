from corsheaders.defaults import default_headers as corsheaders_default_headers

from registrar.settings.base import *
from registrar.settings.utils import get_logger_config

DEBUG = True

# CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
# END CACHE CONFIGURATION

# DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}
# END DATABASE CONFIGURATION

# EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# END EMAIL CONFIGURATION

# TOOLBAR CONFIGURATION
# See: http://django-debug-toolbar.readthedocs.org/en/latest/installation.html
if os.environ.get('ENABLE_DJANGO_TOOLBAR', False):
    INSTALLED_APPS += (
        'debug_toolbar',
    )

    MIDDLEWARE += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    DEBUG_TOOLBAR_PATCH_SETTINGS = False

INTERNAL_IPS = ('127.0.0.1',)
# END TOOLBAR CONFIGURATION

# AUTHENTICATION
# Use a non-SSL URL for authorization redirects
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False

# Set these to the correct values for your OAuth2/OpenID Connect provider (e.g., devstack)
SOCIAL_AUTH_EDX_OAUTH2_KEY = 'registrar-sso-key'
SOCIAL_AUTH_EDX_OAUTH2_SECRET = 'registrar-sso-secret'

# OAuth2 variables specific to backend service API calls.
BACKEND_SERVICE_EDX_OAUTH2_KEY = 'registrar-backend-service-key'
BACKEND_SERVICE_EDX_OAUTH2_SECRET = 'registrar-backend-service-secret'

ENABLE_AUTO_AUTH = True

# LOGGING
LOGGING = get_logger_config(debug=DEBUG, dev_env=True, local_loglevel='DEBUG')

# Publicly-exposed base URLs for service and API
API_ROOT = 'http://localhost:8000/api'

# CORS
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_WHITELIST = (
    'http://localhost:1976',
)
CORS_ALLOW_HEADERS = corsheaders_default_headers + (
    'use-jwt-cookie',
)

CELERY_TASK_ALWAYS_EAGER = True

# File storage.
# Because S3 storage is not available for locally-run Registrar,
# these "bucket names" will just be used as top-level folders in the
# media directory.
REGISTRAR_BUCKET = 'registrar'
PROGRAM_REPORTS_BUCKET = 'program-reports'

#####################################################################
# Lastly, see if the developer has any local overrides.
if os.path.isfile(join(dirname(abspath(__file__)), 'private.py')):
    from .private import *  # pylint: disable=import-error
