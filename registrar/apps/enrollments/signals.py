"""
Defines signals and receivers for the enrollments app.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from registrar.apps.core.models import User
from .models import OrgGroupFutureMembership


logger = logging.getLogger(__name__)


@receiver(post_save, sender=User, dispatch_uid='user_created_callback')
def user_created_callback(sender, instance, created, **kwargs):
    """
    Args:
        sender - The ``core.User`` class.
        instance - The instance of ``core.User`` that was saved.
        created - Boolean indicating if a new ``core.User`` record was created.
    """
    logger.info('\n\n\nTESTESTETSETSETSETSETSET\n\n\n')
    if not created:
        return
    for future_membership in OrgGroupFutureMembership.objects.filter(
            email=instance.email, membership_created_at=None
    ):
        try:
            future_membership.add_user_to_group(instance)
        except:
            #TODO: something
            raise
