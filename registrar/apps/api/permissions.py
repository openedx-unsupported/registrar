"""
Utilities related to API permissions.
"""

from registrar.apps.enrollments.models import Organization


def get_user_organizations(user):
    """
    Get set of organizations the user is affiliated with.

    Arguments:
        user (User)

    Returns: set[Organization]
    """
    return set([Organization.objects.get(pk=1)])  # TODO write this method
