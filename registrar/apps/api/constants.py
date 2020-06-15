"""
Defines constants used by the registrar api.
"""
from registrar.apps.core import permissions as perms


ENROLLMENT_WRITE_MAX_SIZE = 25
UPLOAD_FILE_MAX_SIZE = 5 * 1024 * 1024

# Waffle flag to allow assigning a CourseAccessRole when uploading enrollments
ENABLE_COURSE_ROLE_MANAGEMENT_WAFFLE = 'enable_course_role_management'

TRACKING_CATEGORY = 'Registrar API'

# To be deprecated with upcoming program manager changes (01/2020)
LEGACY_PERMISSION_QUERY_PARAMS = {
    'metadata': perms.API_READ_METADATA,
    'read': perms.API_READ_ENROLLMENTS,
    'write': perms.API_WRITE_ENROLLMENTS,
}
