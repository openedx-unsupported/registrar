"""
Django signal handlers.
"""
from logging import getLogger

from registrar.apps.core.models import (
    PendingUserGroup,
    PendingUserOrganizationGroup,
)


logger = getLogger(__name__)


def handle_user_post_save(sender, **kwargs):  # pylint: disable=unused-argument
    """
    If a pending user group record exists, add the user to the group and delete the pending record.

    Since PendingUserOrganizationGroup is deprecated and is replaced by PendingUserGroup, for backward
    compatibility, if an existing PendingUserOrganizationGroup record exists, we shall still consume
    it upon user's first-time login and delete the PendingUserOrganizationGroup record.
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

    pending_org_groups = PendingUserOrganizationGroup.objects.filter(user_email=user_instance.email)
    for pending_group in pending_org_groups:
        logger.info(
            'add user {} to organization_group {} '.format(
                user_instance.email, pending_group.organization_group
            )
        )
        user_instance.groups.add(pending_group.organization_group)

    pending_org_groups.delete()
