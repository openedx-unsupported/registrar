""" Core models. """

from django.contrib.auth.models import Group
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
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
            (perms.ORGANIZATION_READ_METADATA, 'View Organization Metadata'),
            (perms.ORGANIZATION_READ_ENROLLMENTS, 'Read Organization enrollment data'),
            (perms.ORGANIZATION_WRITE_ENROLLMENTS, 'Read and Write Organization enrollment data'),
        )
    key = models.CharField(unique=True, max_length=255)
    discovery_uuid = models.UUIDField(db_index=True, null=True)
    name = models.CharField(max_length=255)

    def check_access(self, user, access_level):
        """
        Check whether the user has the access level to the organziation.

        Arguments:
            user (User)
            org (Organization)
            access_level

        Returns: bool
        """
        # TODO: We can't write this method right now, because we haven't
        #       implemented auth and roles yet. For now, return True for
        #       ACCESS_READ checks and False for higher-level checks, except
        #       in the case of staff.
        if access_level[1] >= ACCESS_WRITE[1]:
            return user.is_staff
        else:
            return True

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

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=255,
        choices=perms.ROLE_CHOICES,
        default=perms.OrganizationReadMetadataRole.name,
    )

    # pylint: disable=arguments-differ
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for role in perms.ORG_GROUP_ROLES:
            if self.role is role.name:
                role.assign_to_group(self, self.organization)
                break

    def __str__(self):
        return 'OrganizationGroup: {} role={}'.format(self.organization.name, self.role)


class PendingOrganizationUserRole(TimeStampedModel):
    """
    Organization Membership model for user who have not yet been created in the user table

    .. pii:: stores the user email address field for pending users. The pii data gets deleted after a real user gets created
    .. pii_types: email address
    .. pii_retirement:: local_api
    """
    class Meta(object):
        ordering = ['created']


    user_email = models.EmailField(null=False, blank=False, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=255,
        choices=perms.ROLE_CHOICES,
        default=perms.OrganizationReadMetadataRole.name,
    )

    def __str__(self):
        """
        Return human-readable string representation
        """
        return "<PendingOrganizationUserRole {ID}>: {organization_name} - {user_email} - {role}".format(
            ID=self.id,
            organization_name=self.organization.name,
            user_email=self.user_email,
            role=self.role,
        )

    def __repr__(self):
        """
        Return uniquely identifying string representation.
        """
        return self.__str__()
