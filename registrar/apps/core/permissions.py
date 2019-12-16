"""
This module defines constants for permission codenames
and sets of permissions that can be used as roles.
"""
from guardian.shortcuts import assign_perm


APP_PREFIX = 'core.'

# Non-prefixed names of Organization permissions.
# In general, the prefixed versions (without _KEY) should be used, because
# non-prefixed permission names break when you attempt to assign or check them
# globally.
READ_METADATA_KEY = 'organization_read_metadata'
READ_ENROLLMENTS_KEY = 'organization_read_enrollments'
WRITE_ENROLLMENTS_KEY = 'organization_write_enrollments'
READ_REPORTS_KEY = 'read_reports'


# A user with this permission can read any metadata about an organization or prgram.
READ_METADATA = APP_PREFIX + READ_METADATA_KEY


# A user with this permission can read any enrollment data in an organization or program.
READ_ENROLLMENTS = APP_PREFIX + READ_ENROLLMENTS_KEY


# A user with this permission can write any enrollment data contained in an organization or program.
WRITE_ENROLLMENTS = APP_PREFIX + WRITE_ENROLLMENTS_KEY


# A user with this permission can read any reports of an organization or a program.
READ_REPORTS = APP_PREFIX + READ_REPORTS_KEY


PERMISSIONS = {
    READ_METADATA,
    READ_ENROLLMENTS,
    WRITE_ENROLLMENTS,
    READ_REPORTS,
}


# A user with this permission can view the status of all jobs.
# A user without it can only view their own.
# This permission should be reserved for edX staff.
JOB_GLOBAL_READ_KEY = 'job_global_read'
JOB_GLOBAL_READ = APP_PREFIX + JOB_GLOBAL_READ_KEY


class RoleBase(object):
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


class ReadMetadataRole(RoleBase):
    """
    The least-privileged role, it may only read metadata about an organization or a program.
    """
    name = 'organization_read_metadata'
    description = 'Read Metadata Only'
    permissions = (
        READ_METADATA,
    )


class ReadEnrollmentsRole(RoleBase):
    """
    This role is allowed to access metadata and enrollment data, but cannot modify anything.
    """
    name = 'organization_read_enrollments'
    description = 'Read Enrollments Data'
    permissions = (
        READ_METADATA,
        READ_ENROLLMENTS,
    )


class ReadWriteEnrollmentsRole(RoleBase):
    """
    This role is allowed to access metadata and enrollment data.
    It can also create and modify data about enrollments.
    """
    name = 'organization_read_write_enrollments'
    description = 'Read and Write Enrollments Data'
    permissions = (
        READ_METADATA,
        READ_ENROLLMENTS,
        WRITE_ENROLLMENTS,
    )


class ReadReportRole(RoleBase):
    """
    This role is allowed to access metadata and reports, but cannot modify anything.
    """
    name = 'read_reports'
    description = 'Read Reports'
    permissions = (
        READ_METADATA,
        READ_REPORTS,
    )


ROLES = [
    ReadMetadataRole,
    ReadEnrollmentsRole,
    ReadWriteEnrollmentsRole,
    ReadReportRole
]
