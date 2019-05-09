""" Miscellaneous utilities not specific to any app. """
import csv
from io import StringIO
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

    Returns: set[Organization]
    """
    user_groups = user.groups.all()
    user_organizations = set()
    for group in user_groups:
        try:
            user_org_group = OrganizationGroup.objects.get(id=group.id)
            user_organizations.add(user_org_group.organization)
        except OrganizationGroup.DoesNotExist:
            pass
    return user_organizations


def serialize_to_csv(items, field_names, include_headers=False):
    """
    Serialize items into a CSV-formatted string. Column headers optional.

    Booleans are serialized as True and False
    Uses Windows-style line endings ('\r\n').
    Trailing newline is included.

    Arguments:
        items (list[dict])
        field_names (tuple[str])
        include_headers (bool)

    Returns: str
    """
    outfile = StringIO()
    writer = csv.DictWriter(outfile, fieldnames=field_names)
    if include_headers:
        writer.writeheader()
    for item in items:
        writer.writerow(item)
    return outfile.getvalue()
