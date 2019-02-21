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
        url = request.get_full_path()
        is_list_endpoint = (
            url.endswith('programs') or
            url.endswith('programs/')
        )
        # If we are querying individual objects, let has_object_permission handle it
        if not is_list_endpoint:
            return True
        org_key = request.GET.get('org', None)
        return can_user_access_organization(request.user, org_key)

    def has_object_permission(self, request, view, program):
        for org in program.organizations.all():
            if can_user_access_organization(request.user, org):
                return True
        else:
            return False


def can_user_access_organization(user, org_key):
    """
    Returns whether the given user can perform operations on a given
    organization.

    Arguments:
        user (User)
        org_key (str): if None, refers to 'all organizations'

    Returns: bool
    """
    if user.is_staff:
        return True
    if org_key is None:
        return False
    org_key_lower = org_key.lower()
    return org_key_lower == 'gt'  # TODO: Finish writing this function
