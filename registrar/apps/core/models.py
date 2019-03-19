""" Core models. """

from django.contrib.auth.models import Group
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from guardian.shortcuts import remove_perm
from model_utils.models import TimeStampedModel
from registrar.apps.core import permissions as perms

ACCESS_ADMIN = ('admin', 2)
ACCESS_WRITE = ('write', 1)
ACCESS_READ = ('read', 0)


class User(AbstractUser):
    """
    Custom user model for use with OpenID Connect.

    .. pii:: Stores full name, username, and email address for a user.
    .. pii_types:: name, other
    .. pii_retirement:: local_api

    """
    full_name = models.CharField(_('Full Name'), max_length=255, blank=True, null=True)

    @property
    def access_token(self):
        """ Returns an OAuth2 access token for this user, if one exists; otherwise None.

        Assumes user has authenticated at least once with edX Open ID Connect.
        """
        try:
            return self.social_auth.first().extra_data[u'access_token']
        except Exception:  # pylint: disable=broad-except
            return None

    class Meta(object):
        get_latest_by = 'date_joined'

    def get_full_name(self):
        return self.full_name or super(User, self).get_full_name()

    @python_2_unicode_compatible
    def __str__(self):
        return str(self.get_full_name())


class Organization(TimeStampedModel):
    """
    Model that represents a course-discovery Organization entity.

    .. no_pii::
    """
    class Meta(object):
        app_label = 'core'
        permissions = (
            (perms.ORGANIZATION_READ_METADATA_KEY, 'View Organization Metadata'),
            (perms.ORGANIZATION_READ_ENROLLMENTS_KEY, 'Read Organization enrollment data'),
            (perms.ORGANIZATION_WRITE_ENROLLMENTS_KEY, 'Write Organization enrollment data'),
        )
    key = models.CharField(unique=True, max_length=255)
    discovery_uuid = models.UUIDField(db_index=True, null=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class OrganizationGroup(Group):
    """
    Group subclass to grant select guardian permissions to a group on an organization level

    .. no_pii::
    """
    class Meta(object):
        app_label = 'core'
        verbose_name = 'Organization Group'

    ROLE_CHOICES = (
        (role.name, role.description)
        for role in perms.ORGANIZATION_ROLES
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=255,
        choices=ROLE_CHOICES,
        default=perms.OrganizationReadMetadataRole.name,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Save the value of organization in an attribute, so that when
        # save() is called, we have access to the old value.
        try:
            self._initial_organization = self.organization
        except Organization.DoesNotExist:
            self._initial_organization = None

    @property
    def role_object(self):
        """
        Converts self.role (which is a role name) to its matching Role instance.
        """
        for role in perms.ORGANIZATION_ROLES:
            if self.role == role.name:
                return role
        return None

    # pylint: disable=arguments-differ
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self._initial_organization:
            for perm in perms.ORGANIZATION_PERMISSIONS:
                remove_perm(perm, self, self._initial_organization)
        self.role_object.assign_to_group(self, self.organization)
        self._initial_organization = self.organization

    def __str__(self):
        return 'OrganizationGroup: {} role={}'.format(self.organization.name, self.role)
