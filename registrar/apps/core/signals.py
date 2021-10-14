"""
Django signal handlers.
"""
from logging import getLogger

from .models import (
    Organization,
    OrganizationGroup,
    PendingUserGroup,
    Program,
    ProgramOrganizationGroup,
)


logger = getLogger(__name__)


def handle_user_post_save(sender, **kwargs):  # pylint: disable=unused-argument
    """
    If a pending user group record exists, add the user to the group and delete the pending record.
    """
    user_instance = kwargs.get("instance")

    pending_groups = PendingUserGroup.objects.filter(user_email=user_instance.email)
    for pending_group in pending_groups:
        logger.info(
            'add user %(email)s to group %(group)s',
            {'email': user_instance.email, 'group': pending_group.group}
        )
        user_instance.groups.add(pending_group.group)

    pending_groups.delete()


def handle_organization_group_pre_save(sender, instance, **kwargs):   # pylint: disable=unused-argument
    """
    Save previous organization value so guardian permissions can be cleaned up on save
    """
    # pylint: disable=protected-access
    if instance.id:
        existing_org_group = OrganizationGroup.objects.get(pk=instance.id)
        try:
            instance._initial_organization = existing_org_group.organization
        except Organization.DoesNotExist:   # pragma: no cover
            instance._initial_organization = None
    else:
        instance._initial_organization = None


def handle_program_group_pre_save(sender, instance, **kwargs):   # pylint: disable=unused-argument
    """
    Save previous program value so guardian permissions can be cleaned up on save
    """
    # pylint: disable=protected-access
    if instance.id:
        existing_program_group = ProgramOrganizationGroup.objects.get(pk=instance.id)
        try:
            instance._initial_program = existing_program_group.program
        except Program.DoesNotExist:   # pragma: no cover
            instance._initial_program = None
    else:
        instance._initial_program = None
