"""
Defines constants used by the registrar api.
"""

ENROLLMENT_WRITE_MAX_SIZE = 25
UPLOAD_FILE_MAX_SIZE = 5 * 1024 * 1024

# Waffle flag to allow assigning a CourseAccessRole when uploading enrollments
ENABLE_COURSE_ROLE_MANAGEMENT_WAFFLE = 'enable_course_role_management'

TRACKING_CATEGORY = 'Registrar API'
