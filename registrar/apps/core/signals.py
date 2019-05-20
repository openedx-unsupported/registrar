"""
Django signal handlers.
"""
from logging import getLogger

from registrar.apps.core.models import PendingUserOrganizationGroup


logger = getLogger(__name__)


def handle_user_post_save(sender, **kwargs):  # pylint: disable=unused-argument
    """
    If a pending user organization group record exists, add the user to the
    OrganizationGroup and delete the pending record.
    """
    user_instance = kwargs.get("instance")
    pending_org_groups = PendingUserOrganizationGroup.objects.filter(user_email=user_instance.email)
    for pending_group in pending_org_groups:
        logger.info(
            'add organization_group {} into user group for user {}'.format(
                pending_group.organization_group, user_instance.email
            )
        )
        user_instance.groups.add(pending_group.organization_group)

    pending_org_groups.delete()
