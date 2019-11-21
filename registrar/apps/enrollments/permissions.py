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

# These permissions should not be assigned to any use on Registrar.
# These are the permissions we created to prevent any users from accessing
# the enrollments reports on Micromasters programs. Registrar right now
# does not facilitate the enrollments of Micromasters programs, hence
# there is no enrollment mechanism that is valid associated with Micromasters
# programs. No user should have the permissions below
PROGRAM_READ_ENROLLMENTS = APP_PREFIX + PROGRAM_READ_ENROLLMENTS_KEY
PROGRAM_WRITE_ENROLLMENTS = APP_PREFIX + PROGRAM_WRITE_ENROLLMENTS_KEY
