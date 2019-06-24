from os import environ
import yaml

from registrar.settings.base import *
from registrar.settings.utils import get_env_setting, get_logger_config


DEBUG = False
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ['*']

LOGGING = get_logger_config()

# This may be overridden by the YAML in REGISTRAR_CFG, but it should be here as a default.
MEDIA_STORAGE_BACKEND = {}

# Keep track of the names of settings that represent dicts. Instead of overriding the values in base.py,
# the values read from disk should UPDATE the pre-configured dicts.
DICT_UPDATE_KEYS = ('JWT_AUTH',)

CONFIG_FILE = get_env_setting('REGISTRAR_CFG')
with open(CONFIG_FILE, encoding='utf-8') as f:
    config_from_yaml = yaml.safe_load(f)

    # Remove the items that should be used to update dicts, and apply them separately rather
    # than pumping them into the local vars.
    dict_updates = {key: config_from_yaml.pop(key, None) for key in DICT_UPDATE_KEYS}

    for key, value in dict_updates.items():
        if value:
            vars()[key].update(value)

    vars().update(config_from_yaml)
    vars().update(MEDIA_STORAGE_BACKEND)

DB_OVERRIDES = dict(
    PASSWORD=environ.get('DB_MIGRATION_PASS', DATABASES['default']['PASSWORD']),
    ENGINE=environ.get('DB_MIGRATION_ENGINE', DATABASES['default']['ENGINE']),
    USER=environ.get('DB_MIGRATION_USER', DATABASES['default']['USER']),
    NAME=environ.get('DB_MIGRATION_NAME', DATABASES['default']['NAME']),
    HOST=environ.get('DB_MIGRATION_HOST', DATABASES['default']['HOST']),
    PORT=environ.get('DB_MIGRATION_PORT', DATABASES['default']['PORT']),
)

for override, value in DB_OVERRIDES.items():
    DATABASES['default'][override] = value

CELERY_ALWAYS_EAGER = (
    os.environ.get("CELERY_ALWAYS_EAGER", "false").lower() == "true"
)

# Configuration has an issue where it, by default, renders
# `JWT_PUBLIC_SIGNING_JWK_SET` as the string "None" instead of the value
# `None`. Production environments do not see this issue because the setting
# is always overridden; however, it is an issue on Sandboxes, which use
# the default value.
# As a workaround, manually change the setting to `None` if it is equals
# the string "None".
jwk_setting = 'JWT_PUBLIC_SIGNING_JWK_SET'
if vars().get(jwk_setting) == 'None':
    vars()[jwk_setting] = None
del jwk_setting
