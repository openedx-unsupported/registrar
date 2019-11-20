"""
This module defines constants for permission codenames
and sets of permissions that can be used as roles.
"""
from guardian.shortcuts import assign_perm

APP_PREFIX = 'enrollments.'

# Non-prefixed names of program enrollment read permissions
PROGRAM_READ_ENROLLMENTS_KEY = 'program_read_enrollments'

# Non-prefixed names of program enrollment write permissions
PROGRAM_WRITE_ENROLLMENTS_KEY = 'program_write_enrollments'

# A user with this permission can read program data report associated
# with the program. This permission do not allow program enrollments
# nor program course enrollment reads or writes
PROGRAM_READ_ENROLLMENTS = APP_PREFIX + PROGRAM_READ_ENROLLMENTS_KEY
PROGRAM_WRITE_ENROLLMENTS = APP_PREFIX + PROGRAM_WRITE_ENROLLMENTS_KEY




class ProgramRole(object):
    """
    A collection of Program permissions that can be assigned
    to a Group or ProgramGroup.
    """

    name = None
    description = None
    permissions = ()

    @classmethod
    def assign_to_group(cls, group, program):
        """
        For the given program, assigns all permissions under this role
        to the given group.
        """
        for permission in cls.permissions:
            assign_perm(permission, group, program)


class ProgramReadEnrollmentsRole(ProgramRole):
    """
    The least-privileged program-scoped role, it may only
    read enrollments about a program and its courses.
    """
    name = 'program_read_enrollments'
    description = 'Read Enrollments Only'
    permissions = (
        PROGRAM_READ_ENROLLMENTS,
    )

class ProgramReadWriteEnrollmentsRole(ProgramRole):
    """
    The read and write privileged program-scoped role, it may read
    and write enrollments about a program and its courses.
    """
    name = 'program_read_write_enrollments'
    description = 'Read and Write Enrollments'
    permissions = (
        PROGRAM_READ_ENROLLMENTS, PROGRAM_WRITE_ENROLLMENTS,
    )
