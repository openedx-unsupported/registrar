import os
import tempfile

from registrar.settings.base import *


# IN-MEMORY TEST DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
}
# END IN-MEMORY TEST DATABASE

LMS_BASE_URL = 'https://lms-service-base'
DISCOVERY_BASE_URL = 'https://discovery-service-base'

OAUTH2_PROVIDER_URL = 'https://test-provider/oauth2'
SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = OAUTH2_PROVIDER_URL

JWT_AUTH['JWT_ISSUERS'] = [{
    'SECRET_KEY': SOCIAL_AUTH_EDX_OAUTH2_SECRET,
    'ISSUER': OAUTH2_PROVIDER_URL,
    'AUDIENCE': SOCIAL_AUTH_EDX_OAUTH2_KEY,
}]

# CELERY
CELERY_TASK_ALWAYS_EAGER = True

# Results
CELERY_TASK_IGNORE_RESULT = True

results_dir = tempfile.TemporaryDirectory()
CELERY_RESULT_BACKEND = f'file://{results_dir.name}'

# Celery environment variables are not available in travis
# Hence providing memory as broker for test suite
CELERY_BROKER_URL = 'memory://localhost/'

# END CELERY

# Media
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_LOCATION = ''
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 3600
AWS_DEFAULT_ACL = None
REGISTRAR_BUCKET = 'registrar-test'
PROGRAM_REPORTS_BUCKET = 'program-reports-test'

# Publicly-exposed base URLs for service and API, respectively
API_ROOT = 'http://localhost/api'
