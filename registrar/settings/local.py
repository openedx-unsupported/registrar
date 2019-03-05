from registrar.settings.base import *

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
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'registrar',
        'USER': 'registrar001',
        'PASSWORD': 'password',
        'HOST': 'registrar-db',
        'PORT': '3306',
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

    MIDDLEWARE_CLASSES += (
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
SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = 'http://edx.devstack.lms:18000'
SOCIAL_AUTH_EDX_OAUTH2_PUBLIC_URL_ROOT = 'http://localhost:18000'
SOCIAL_AUTH_EDX_OAUTH2_LOGOUT_URL = 'http://localhost:18000/logout'
SOCIAL_AUTH_EDX_OAUTH2_ISSUER = SOCIAL_AUTH_EDX_OAUTH2_PUBLIC_URL_ROOT

# OAuth2 variables specific to backend service API calls.
BACKEND_SERVICE_EDX_OAUTH2_KEY = 'registrar-backend-service-key'
BACKEND_SERVICE_EDX_OAUTH2_SECRET = 'registrar-backend-service-secret'

ENABLE_AUTO_AUTH = True

LMS_BASE_URL = 'http://edx.devstack.lms:18000'
DISCOVERY_BASE_URL = 'http://edx.devstack.discovery:18381'

#####################################################################
# Lastly, see if the developer has any local overrides.
if os.path.isfile(join(dirname(abspath(__file__)), 'private.py')):
    from .private import *  # pylint: disable=import-error
