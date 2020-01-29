"""
Django signal handlers.
"""
from logging import getLogger

from registrar.apps.core.models import PendingUserGroup


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
