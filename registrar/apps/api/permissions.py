"""
Utilities related to API permissions.
"""

from registrar.apps.enrollments.models import Organization


def get_user_organizations(user):  # pylint: disable=unused-argument
    """
    Get set of organizations the user is affiliated with.

    Arguments:
        user (User)

    Returns: set[Organization]
    """
    # TODO write this method; remove pylint disable
    return set([Organization.objects.get(pk=1)])
