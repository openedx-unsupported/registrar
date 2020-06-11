"""
This module defines constants for permission codenames
and sets of permissions that can be used as roles.
"""
import re
from collections import namedtuple

from guardian.shortcuts import assign_perm


APP_PREFIX = 'core.'

# Non-prefixed names of permissions.
# In general, the prefixed versions (without _KEY) should be used, because
# non-prefixed permission names break when you attempt to assign or check them
# globally.
ORGANIZATION_READ_METADATA_KEY = 'organization_read_metadata'
ORGANIZATION_READ_ENROLLMENTS_KEY = 'organization_read_enrollments'
ORGANIZATION_WRITE_ENROLLMENTS_KEY = 'organization_write_enrollments'
ORGANIZATION_READ_REPORTS_KEY = 'read_reports'

PROGRAM_READ_METADATA_KEY = 'program_read_metadata'
PROGRAM_READ_ENROLLMENTS_KEY = 'program_read_enrollments'
PROGRAM_WRITE_ENROLLMENTS_KEY = 'program_write_enrollments'
PROGRAM_READ_REPORTS_KEY = 'program_read_reports'


# A user with this permission can read any metadata about an organization.
ORGANIZATION_READ_METADATA = APP_PREFIX + ORGANIZATION_READ_METADATA_KEY


# A user with this permission can read any enrollment data in an organization.
ORGANIZATION_READ_ENROLLMENTS = APP_PREFIX + ORGANIZATION_READ_ENROLLMENTS_KEY


# A user with this permission can write any enrollment data contained in an organization.
ORGANIZATION_WRITE_ENROLLMENTS = APP_PREFIX + ORGANIZATION_WRITE_ENROLLMENTS_KEY


# A user with this permission can read any reports of an organization.
ORGANIZATION_READ_REPORTS = APP_PREFIX + ORGANIZATION_READ_REPORTS_KEY


# A user with this permission can read any metadata about a program.
PROGRAM_READ_METADATA = APP_PREFIX + PROGRAM_READ_METADATA_KEY


# A user with this permission can read any enrollment data in a program.
PROGRAM_READ_ENROLLMENTS = APP_PREFIX + PROGRAM_READ_ENROLLMENTS_KEY


# A user with this permission can write any enrollment data contained in a program.
PROGRAM_WRITE_ENROLLMENTS = APP_PREFIX + PROGRAM_WRITE_ENROLLMENTS_KEY


# A user with this permission can read any reports of a program.
PROGRAM_READ_REPORTS = APP_PREFIX + PROGRAM_READ_REPORTS_KEY


ORGANIZATION_PERMISSIONS = {
    ORGANIZATION_READ_METADATA,
    ORGANIZATION_READ_ENROLLMENTS,
    ORGANIZATION_WRITE_ENROLLMENTS,
    ORGANIZATION_READ_REPORTS,
}


PROGRAM_PERMISSIONS = {
    PROGRAM_READ_METADATA,
    PROGRAM_READ_ENROLLMENTS,
    PROGRAM_WRITE_ENROLLMENTS,
    PROGRAM_READ_REPORTS,
}


# A user with this permission can view the status of all jobs.
# A user without it can only view their own.
# This permission should be reserved for edX staff.
JOB_GLOBAL_READ_KEY = 'job_global_read'
JOB_GLOBAL_READ = APP_PREFIX + JOB_GLOBAL_READ_KEY


# APIPermission:
# Associate corresponding Organization-level and Program-level permissions.
#
# When an "APIPermission" is checked against a user and a program, it is sufficient for
# the user to have permission on the program directly OR permission on the program's
# managing organization.
#
# Fields:
#     name (str)
#     organization_permission (str): App-qualified Organization permission string.
#     program_permission (str): App-qualified Program permission string.
#     enables_enrollment_management (bool):
#         Whether the granting of this permission implies that enrollment management
#         is enabled for the target program.
APIPermission = namedtuple('APIPermission', [
    'name',
    'organization_permission',
    'program_permission',
    'enables_enrollment_management',
])


API_READ_METADATA = APIPermission(
    name='read_metadata',
    organization_permission=ORGANIZATION_READ_METADATA,
    program_permission=PROGRAM_READ_METADATA,
    enables_enrollment_management=False,
)

API_READ_ENROLLMENTS = APIPermission(
    name='read_enrollments',
    organization_permission=ORGANIZATION_READ_ENROLLMENTS,
    program_permission=PROGRAM_READ_ENROLLMENTS,
    enables_enrollment_management=True,
)

API_WRITE_ENROLLMENTS = APIPermission(
    name='write_enrollments',
    organization_permission=ORGANIZATION_WRITE_ENROLLMENTS,
    program_permission=PROGRAM_WRITE_ENROLLMENTS,
    enables_enrollment_management=True,
)

API_READ_REPORTS = APIPermission(
    name='read_reports',
    organization_permission=ORGANIZATION_READ_REPORTS,
    program_permission=PROGRAM_READ_REPORTS,
    enables_enrollment_management=False,
)

API_PERMISSIONS = [
    API_READ_METADATA,
    API_READ_ENROLLMENTS,
    API_WRITE_ENROLLMENTS,
    API_READ_REPORTS,
]

API_PERMISSIONS_BY_NAME = {
    api_permission.name: api_permission
    for api_permission in API_PERMISSIONS
}

API_ENROLLMENT_PERMISSIONS = [
    api_permission for api_permission in API_PERMISSIONS
    if api_permission.enables_enrollment_management
]


class RoleBase:
    """
    A collection of access permissions that can be assigned
    to a group in an organization or program.
    """

    name = None
    description = None
    permissions = ()

    @classmethod
    def assign_to_group(cls, group, model):
        """
        For the given model (organization or program), assigns all permissions under this role
        to the given group.
        """
        for permission in cls.permissions:
            assign_perm(permission, group, model)


class OrganizationReadMetadataRole(RoleBase):
    """
    The least-privileged role, it may only read metadata about an organization.
    """
    name = 'organization_read_metadata'
    description = 'Read Organization Metadata Only'
    permissions = (
        ORGANIZATION_READ_METADATA,
    )


class OrganizationReadEnrollmentsRole(RoleBase):
    """
    This role is allowed to access organization metadata and enrollment data, but cannot modify anything.
    """
    name = 'organization_read_enrollments'
    description = 'Read Organization Enrollments Data'
    permissions = (
        ORGANIZATION_READ_METADATA,
        ORGANIZATION_READ_ENROLLMENTS,
    )


class OrganizationReadWriteEnrollmentsRole(RoleBase):
    """
    This role is allowed to access organization metadata and enrollment data.
    It can also create and modify data about organization enrollments.
    """
    name = 'organization_read_write_enrollments'
    description = 'Read and Write Organization Enrollments Data'
    permissions = (
        ORGANIZATION_READ_METADATA,
        ORGANIZATION_READ_ENROLLMENTS,
        ORGANIZATION_WRITE_ENROLLMENTS,
    )


class OrganizationReadReportRole(RoleBase):
    """
    This role is allowed to access organization metadata and reports, but cannot modify anything.
    """
    name = 'organization_read_reports'
    description = 'Read Organization Reports'
    permissions = (
        ORGANIZATION_READ_METADATA,
        ORGANIZATION_READ_REPORTS,
    )


class ProgramReadMetadataRole(RoleBase):
    """
    The least-privileged role, it may only read metadata about a program.
    """
    name = 'program_read_metadata'
    description = 'Read Program Metadata Only'
    permissions = (
        PROGRAM_READ_METADATA,
    )


class ProgramReadEnrollmentsRole(RoleBase):
    """
    This role is allowed to access program metadata and program enrollment data, but cannot modify anything.
    """
    name = 'program_read_enrollments'
    description = 'Read Program Enrollments Data'
    permissions = (
        PROGRAM_READ_METADATA,
        PROGRAM_READ_ENROLLMENTS,
    )


class ProgramReadWriteEnrollmentsRole(RoleBase):
    """
    This role is allowed to access program metadata and program enrollment data.
    It can also create and modify data about program enrollments.
    """
    name = 'program_read_write_enrollments'
    description = 'Read and Write Program Enrollments Data'
    permissions = (
        PROGRAM_READ_METADATA,
        PROGRAM_READ_ENROLLMENTS,
        PROGRAM_WRITE_ENROLLMENTS,
    )


class ProgramReadReportRole(RoleBase):
    """
    This role is allowed to access program metadata and reports, but cannot modify anything.
    """
    name = 'program_read_reports'
    description = 'Read Program Reports'
    permissions = (
        PROGRAM_READ_METADATA,
        PROGRAM_READ_REPORTS,
    )


ORGANIZATION_ROLES = [
    OrganizationReadMetadataRole,
    OrganizationReadEnrollmentsRole,
    OrganizationReadWriteEnrollmentsRole,
    OrganizationReadReportRole,
]


PROGRAM_ROLES = [
    ProgramReadMetadataRole,
    ProgramReadEnrollmentsRole,
    ProgramReadWriteEnrollmentsRole,
    ProgramReadReportRole,
]


def _build_db_to_api_permissions():
    """
    Return a dict mappping each permission string to a corresponding
    APIPermission. Two versions of each string are mapped, one with
    the app prefix (used by django functions) and another without
    (used by guardian)
    """
    permission_map = {}
    for api_permission in API_PERMISSIONS:
        db_permissions = [
            api_permission.organization_permission, api_permission.program_permission
        ]
        for db_perm in db_permissions:
            # map permission string that includes app name
            permission_map[db_perm] = api_permission
            # strip app name from permission to match guardian's usage
            match = re.match(r'\w+\.(\w+)', db_perm)
            if match:  # pragma: no branch
                db_perm = match.groups()[0]
                permission_map[db_perm] = api_permission
    return permission_map


DB_TO_API_PERMISSION_MAPPING = _build_db_to_api_permissions()
