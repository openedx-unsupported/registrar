"""
Utilities related to API permissions.
"""

from rest_framework import permissions

class ProgramReadOnlyViewSetPermission(permissions.BasePermission):
    """
    Limit users to only be able to view program listings for
    organizations with which they are affiliated.
    """
    message = 'You are not permitted to view this set of programs.'

    def has_permission(self, request, view):
        if user.is_staff():
            return True
        org_key = request.GET('org', None)
        return (
            org_key is not None and
            org_key.lower() in get_user_organizations(request.user)
        )

    def has_object_permission(self, request, view, program):
        if user.is_staff():
            return True
        org_keys = set(org.key for org in program.organizations)
        user_org_keys = get_user_organization_keys(request.user)
        return len(org_keys.intersection(user_org_keys)) > 0


def get_user_organization_keys(user):
    """

    Get set of keys for organizations the user is affiliated with.

    Arguments:
        user (User)

    Returns: set[str]
    """
    return set(['gt'])  # TODO: Write this function
