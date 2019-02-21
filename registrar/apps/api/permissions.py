"""
Utilities related to API permissions.
"""

def get_user_organization_keys(user):
    """
    Get set of keys for organizations the user is affiliated with.

    Arguments:
        user (User)

    Returns: set[str]
    """
    return set(['gt', 'uta'])  # TODO: Write this function
