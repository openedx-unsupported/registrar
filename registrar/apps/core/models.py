"""
Core models.
"""
import logging
from collections import namedtuple
from uuid import UUID

from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from guardian.shortcuts import remove_perm
from model_utils.models import TimeStampedModel

from . import discovery_cache
from . import permissions as perms


ACCESS_ADMIN = ('admin', 2)
ACCESS_WRITE = ('write', 1)
ACCESS_READ = ('read', 0)

logger = logging.getLogger(__name__)


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
            (perms.ORGANIZATION_READ_METADATA_KEY, 'View Metadata'),
            (perms.ORGANIZATION_READ_ENROLLMENTS_KEY, 'Read enrollment data'),
            (perms.ORGANIZATION_WRITE_ENROLLMENTS_KEY, 'Write enrollment data'),
            (perms.ORGANIZATION_READ_REPORTS_KEY, 'Read reports data'),
        )
    key = models.CharField(unique=True, max_length=255)
    discovery_uuid = models.UUIDField(db_index=True, null=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        """
        Human-friendly string representation of this organization.
        """
        return self.name

    def __repr__(self):
        """
        Developer-friendly string representation of this organization.
        """
        return "<Organization key={} discovery_uuid={} name={!r}>".format(
            self.key, self.discovery_uuid, self.name
        )


CourseRun = namedtuple(
    "CourseRun",
    ("key", "external_key", "title", "marketing_url"),
)


class Program(TimeStampedModel):
    """
    Table that referrences a course-discovery Program entity.

    .. no_pii::
    """
    class Meta(object):
        app_label = 'core'
        permissions = (
            (perms.PROGRAM_READ_METADATA_KEY, 'View program metadata'),
            (perms.PROGRAM_READ_ENROLLMENTS_KEY, 'Read program enrollment data'),
            (perms.PROGRAM_WRITE_ENROLLMENTS_KEY, 'Write program enrollment data'),
            (perms.PROGRAM_READ_REPORTS_KEY, 'Read program reports data'),
        )
    key = models.CharField(unique=True, max_length=255)
    discovery_uuid = models.UUIDField(db_index=True, null=True)
    managing_organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self):
        """
        Human-friendly string representation of this program.
        """
        return self.title

    def __repr__(self):
        """
        Developer-friendly string representation of this program.
        """
        return "<Program key={} discovery_uuid={} managing_organization={}>".format(
            self.key, self.discovery_uuid, self.managing_organization.key
        )

    @cached_property
    def discovery_data(self):
        """
        Get data about this program from Discovery cache.

        Returns an empty dict if program does not exist in Discovery.
        """
        return discovery_cache.get_program_data(self.discovery_uuid) or {}

    @cached_property
    def title(self):
        """
        Title of the program.

        Falls back to program key if not available.
        """
        return self.discovery_data.get('title') or self.key

    @cached_property
    def url(self):
        """
        URL of the program.

        Falls back to None if not available.
        """
        return self.discovery_data.get('url')

    @cached_property
    def program_type(self):
        """
        Type of the program (Masters, MicroMasters, etc.).

        Falls back to None if not available.
        """
        return self.discovery_data.get('program_type')

    @cached_property
    def is_enrollment_enabled(self):
        """
        Whether Registrar can be used to manage enrollments for this program.

        Falls back to False if not available.
        """
        return self.program_type == 'Masters'

    @cached_property
    def active_curriculum_data(self):
        """
        Dict containing data for active curriculum.

        We define 'active' curriculum as the first one in the list of
        curricula where is_active is True.

        TODO:
        This is a temporary assumption, originally made in March 2019.
        We expect that future programs may have more than one curriculum
        active simultaneously, which will require modifying the API.

        Falls back to empty dict if no active curriculum or if data unavailable.
        """
        try:
            return next(
                c for c in self.discovery_data.get('curricula', [])
                if c.get('is_active')
            )
        except StopIteration:
            logger.exception(
                'Discovery API returned no active curricula for program {}'.format(
                    self.discovery_uuid
                )
            )
            return {}

    @cached_property
    def active_curriculum_uuid(self):
        """
        Get UUID of active curriculum, or None if no active curriculum.

        See `active_curriculum_data` docstring for more details.
        """
        try:
            return UUID(self.active_curriculum_data['uuid'])
        except (KeyError, ValueError):
            return None

    @cached_property
    def course_runs(self):
        """
        Get list of CourseRuns defined in root of active curriculum.

        TODO:
        In March 2019 we made a temporary assumption that the curriculum
        does not contain nested programs.
        We expect that this will need revisiting eventually.
        We expect that future programs may have more than one curriculum

        Also see `active_curriculum_data` docstring details on how the 'active'
        curriculum is determined.

        Falls back to empty list if no active curriculum or if data unavailable.
        """
        return [
            CourseRun(
                key=course_run.get("key"),
                external_key=course_run.get("external_key"),
                title=course_run.get("title"),
                marketing_url=course_run.get("marketing_url"),
            )
            for course in self.active_curriculum_data.get("courses", [])
            for course_run in course.get("course_runs", [])
        ]

    def find_course_run(self, course_id):
        """
        Given a course id, return the course_run with that `key` or `external_key`

        Returns None if course run is not found in the cached program.
        """
        try:
            return next(
                course_run for course_run in self.course_runs
                if course_id in {course_run.key, course_run.external_key}
            )
        except StopIteration:
            return None

    def get_external_course_key(self, course_id):
        """
        Given a course ID, return the external course key for that course_run.
        The course key passed in may be an external or internal course key.

        Returns None if course run is not found in the cached program.
        """
        course_run = self.find_course_run(course_id)
        if course_run:
            return course_run.external_key
        return None

    def get_course_key(self, course_id):
        """
        Given a course ID, return the internal course ID for that course run.
        The course ID passed in may be an external or internal course key.

        Returns None if course run is not found in the cached program.
        """
        course_run = self.find_course_run(course_id)
        if course_run:
            return course_run.key
        return None


class OrganizationGroup(Group):
    """
    Group subclass to grant select guardian permissions to a group on an organization level.

    .. no_pii::
    """
    objects = models.Manager()

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


class ProgramOrganizationGroup(Group):
    """
    Group subclass to grant select guardian permissions to a group on a program level.

    .. no_pii::
    """

    objects = models.Manager()

    class Meta(object):
        app_label = 'core'
        verbose_name = 'Program Group'

    ROLE_CHOICES = (
        (role.name, role.description)
        for role in perms.PROGRAM_ROLES
    )

    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    granting_organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=255,
        choices=ROLE_CHOICES,
        default=perms.ProgramReadMetadataRole.name,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self._initial_program = self.program
        except Program.DoesNotExist:   # pragma: no cover
            self._initial_program = None

    @property
    def role_object(self):
        """
        Converts self.role (which is a role name) to its matching Role instance.
        """
        for role in perms.PROGRAM_ROLES:
            if self.role == role.name:  # pragma: no branch
                return role
        return None  # pragma: no cover

    # pylint: disable=arguments-differ
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self._initial_program:  # pragma: no branch
            for perm in perms.PROGRAM_PERMISSIONS:
                remove_perm(perm, self, self._initial_program)
        self.role_object.assign_to_group(self, self.program)
        self._initial_program = self.program

    def __str__(self):
        return 'ProgramOrganizationGroup: {} role={}'.format(self.program.title, self.role)  # pragma: no cover


class PendingUserGroup(TimeStampedModel):
    """
    Membership model for user who have not yet been created in the user table

    .. pii:: stores the user email address field for pending users.
             The pii data gets deleted after a real user gets created
    .. pii_types:: email_address
    .. pii_retirement:: local_api
    """
    class Meta(object):
        ordering = ['created']
        unique_together = ('user_email', 'group')

    user_email = models.EmailField()
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    def __str__(self):
        """
        Return human-readable string representation
        """
        if isinstance(self.group, OrganizationGroup):
            return "<PendingUserGroup {ID}>: {organization_name} - {user_email} - {role}".format(
                ID=self.id,
                organization_name=self.group.organization.name,
                user_email=self.user_email,
                role=self.group.role,
            )

        if isinstance(self.group, ProgramOrganizationGroup):  # pragma: no branch
            return "<PendingUserGroup {ID}>: {organization_name} - {program_name} - {user_email} - {role}".format(
                ID=self.id,
                organization_name=self.group.granting_organization.name,
                program_name=self.group.program.key,
                user_email=self.user_email,
                role=self.group.role,
            )

        return "<PendingUserGroup {ID}>: {group_name} - {user_email}".format(
            ID=self.id,
            group_name=self.group.name,
            user_email=self.user_email,
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
