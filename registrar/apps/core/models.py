""" Core models. """

from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from guardian.shortcuts import remove_perm
from model_utils.models import TimeStampedModel

from registrar.apps.common.data import DiscoveryProgram
from registrar.apps.core import permissions as perms


ACCESS_ADMIN = ('admin', 2)
ACCESS_WRITE = ('write', 1)
ACCESS_READ = ('read', 0)


class User(AbstractUser):
    """
    Custom user model for use with OpenID Connect.

    .. pii:: Stores full name, username, and email address for a user
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
        return str(self.username)


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
        return self.name  # pragma: no cover


class Program(TimeStampedModel):
    """
    Table that referrences a course-discovery Program entity.

    .. no_pii::
    """
    class Meta(object):
        app_label = 'core'

    key = models.CharField(unique=True, max_length=255)
    discovery_uuid = models.UUIDField(db_index=True, null=True)
    managing_organization = models.ForeignKey(Organization, related_name='programs')

    @property
    def discovery_program(self):
        return DiscoveryProgram.get(self.discovery_uuid)

    @property
    def title(self):
        return self._get_cached_field('title')

    @property
    def url(self):
        return self._get_cached_field('url')

    @property
    def program_type(self):
        return self._get_cached_field('program_type')

    def _get_cached_field(self, field):
        """
        Returns the specified field from a cached Discovery program.
        If the program is not found in the cache it is loaded from discovery
        """
        discovery_program = DiscoveryProgram.get(self.discovery_uuid)
        val = getattr(discovery_program, field)
        return val

    def __str__(self):
        return self.key  # pragma: no cover


class OrganizationGroup(Group):
    """
    Group subclass to grant select guardian permissions to a group on an organization level.

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
        except Organization.DoesNotExist:   # pragma: no cover
            self._initial_organization = None

    @property
    def role_object(self):
        """
        Converts self.role (which is a role name) to its matching Role instance.
        """
        for role in perms.ORGANIZATION_ROLES:
            if self.role == role.name:
                return role
        return None  # pragma: no cover

    # pylint: disable=arguments-differ
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self._initial_organization:  # pragma: no branch
            for perm in perms.ORGANIZATION_PERMISSIONS:
                remove_perm(perm, self, self._initial_organization)
        self.role_object.assign_to_group(self, self.organization)
        self._initial_organization = self.organization

    def __str__(self):
        return 'OrganizationGroup: {} role={}'.format(self.organization.name, self.role)


class PendingUserOrganizationGroup(TimeStampedModel):
    """
    Organization Membership model for user who have not yet been created in the user table

    .. pii:: stores the user email address field for pending users.
             The pii data gets deleted after a real user gets created
    .. pii_types:: email_address
    .. pii_retirement:: local_api
    """
    class Meta(object):
        ordering = ['created']
        unique_together = ('user_email', 'organization_group')

    user_email = models.EmailField()
    organization_group = models.ForeignKey(OrganizationGroup)

    def __str__(self):
        """
        Return human-readable string representation
        """
        return "<PendingUserOrganizationGroup {ID}>: {organization_name} - {user_email} - {role}".format(
            ID=self.id,
            organization_name=self.organization_group.organization.name,
            user_email=self.user_email,
            role=self.organization_group.role,
        )

    def __repr__(self):
        """
        Return uniquely identifying string representation.
        """
        return self.__str__()  # pragma: no cover


class JobPermissionSupport(models.Model):
    """
    'Model' allowing us to define permissions related to jobs, which do not
    have a model associated with them (they are simply an abstraction around
    UserTasks).

    We set Meta.managed to False so that a database table is not created.

    .. no_pii::
    """

    class Meta:
        managed = False  # Do not create a database table
        permissions = (
            (perms.JOB_GLOBAL_READ_KEY, 'Global Job status reading'),
        )
