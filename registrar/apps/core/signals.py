"""
Django signal handlers.
"""
from logging import getLogger

from .models import (
    Organization,
    OrganizationGroup,
    PendingUserGroup,
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
            'add user {} to group {}'.format(
                user_instance.email, pending_group.group
            )
        )
        user_instance.groups.add(pending_group.group)

    pending_groups.delete()

def handle_organization_group_pre_save(sender, instance, **kwargs):
    """
    Save previous organization value so guardian permissions can be cleaned up on save
    """
    if instance.id:
        existing_org_group = OrganizationGroup.objects.get(pk=instance.id)
        try:
            instance._initial_organization = existing_org_group.organization
        except Organization.DoesNotExist:
            instance._initial_organization = None
    else:
        instance._initial_organization = None

def handle_program_group_pre_save(sender, instance, **kwargs):
    """
    Save previous program value so guardian permissions can be cleaned up on save
    """
    if instance.id:
        existing_program_group = ProgramOrganizationGroup.objects.get(pk=instance.id)
        try:
            instance._initial_program = existing_program_group.program
        except Program.DoesNotExist:
            instance._initial_program = None
    else:
        instance._initial_program = None
