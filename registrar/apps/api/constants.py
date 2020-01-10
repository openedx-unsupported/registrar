"""
Defines constants used by the registrar api.
"""
from registrar.apps.core import permissions as perms


ENROLLMENT_WRITE_MAX_SIZE = 25
UPLOAD_FILE_MAX_SIZE = 5 * 1024 * 1024

TRACKING_CATEGORY = 'Registrar API'

PERMISSION_QUERY_PARAM_MAP = {
    'metadata': perms.APIReadMetadataPermission,
    'read': perms.APIReadEnrollmentsPermission,
    'write': perms.APIWriteEnrollmentsPermission,
}

ENROLLMENT_PERMISSIONS_LIST = [
    perms.APIReadEnrollmentsPermission,
    perms.APIWriteEnrollmentsPermission,
]
