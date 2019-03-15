"""
This module defines constants for permission codenames
and sets of permissions that can be used as roles.
"""
from guardian.shortcuts import assign_perm


APP_PREFIX = 'core.'


# A user with this permission can read any metadata
# about an organization, including metadata about
# its programs and courses therein.
ORGANIZATION_READ_METADATA = APP_PREFIX + 'organization_read_metadata'


# A user with this permission can read any enrollment data contained
# in the scope of an organization, i.e. the organization's
# program enrollments and program-course enrollments.
ORGANIZATION_READ_ENROLLMENTS = APP_PREFIX + 'organization_read_enrollments'


# A user with this permission can write any enrollment data contained
# in the scope of an organization, i.e. the organization's
# program enrollments and program-course enrollments.
ORGANIZATION_WRITE_ENROLLMENTS = APP_PREFIX + 'organization_write_enrollments'


ORGANIZATION_PERMISSIONS = {
    ORGANIZATION_READ_METADATA,
    ORGANIZATION_READ_ENROLLMENTS,
    ORGANIZATION_WRITE_ENROLLMENTS,
}


class OrganizationRole(object):
    """
    A collection of Organization access permissions that can be assigned
    to a Group or OrganizationGroup.
    """

    name = None
    description = None
    permissions = ()

    @classmethod
    def assign_to_group(cls, group, organization):
        """
        For the given organization, assigns all permissions under this role
        to the given group.
        """
        for permission in cls.permissions:
            assign_perm(permission, group, organization)


class OrganizationReadMetadataRole(OrganizationRole):
    """
    The least-privileged organization-scoped role, it may only
    read metadata about an organization's programs and courses.
    """
    name = 'organization_read_metadata'
    description = 'Read Metadata Only'
    permissions = (
        ORGANIZATION_READ_METADATA,
    )


class OrganizationReadEnrollmentsRole(OrganizationRole):
    """
    This role is allowed to access organization metadata and
    enrollment data, but cannot modify anything.
    """
    name = 'organization_read_enrollments'
    description = 'Read Enrollments Data'
    permissions = (
        ORGANIZATION_READ_METADATA,
        ORGANIZATION_READ_ENROLLMENTS,
    )


class OrganizationReadWriteEnrollmentsRole(OrganizationRole):
    """
    This role is allowed to access organization metadata and
    enrollment data.  It can also create and modify data
    about enrollments in programs and courses within an organization.
    """
    name = 'organization_read_write_enrollments'
    description = 'Read and Write Enrollments Data'
    permissions = (
        ORGANIZATION_READ_METADATA,
        ORGANIZATION_READ_ENROLLMENTS,
        ORGANIZATION_WRITE_ENROLLMENTS,
    )


ORGANIZATION_ROLES = [
    OrganizationReadMetadataRole,
    OrganizationReadEnrollmentsRole,
    OrganizationReadWriteEnrollmentsRole
]
