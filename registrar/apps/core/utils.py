""" Miscellaneous utilities not specific to any app. """
import re

from registrar.apps.core.models import OrganizationGroup


def name_to_key(name):
    """
    Returns a 'key-like' version of a name.

    Example:
        name_to_key("Master's in Computer Science") =>
            'masters-in-computer-science'
    """
    name2 = name.replace(' ', '-').replace('_', '-').lower()
    return re.sub(r'[^a-z0-9-]', '', name2)


def get_user_organizations(user):
    """
    Get the Org Group of the user passed in.
    """
    user_groups = user.groups.all()
    user_organizations = []
    for group in user_groups:
        try:
            user_org_group = OrganizationGroup.objects.get(id=group.id)
            if user_org_group.organization:
                user_organizations.append(user_org_group.organization)
        except OrganizationGroup.DoesNotExist:
            pass
    return user_organizations
