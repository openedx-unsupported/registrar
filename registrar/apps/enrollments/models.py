"""
Models relating to learner program and course enrollments.
"""
from datetime import datetime

from django.contrib.auth.models import Group
from django.db import models
from model_utils.models import TimeStampedModel
from pytz import UTC
from simple_history.models import HistoricalRecords

from registrar.apps.enrollments import permissions as perms


ACCESS_ADMIN = ('admin', 2)
ACCESS_WRITE = ('write', 1)
ACCESS_READ = ('read', 0)


class Organization(TimeStampedModel):
    """
    Model that represents a course-discovery Organization entity.

    .. no_pii::
    """
    class Meta(object):
        app_label = 'enrollments'
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


class OrgGroup(Group):
    class Meta(object):
        app_label = 'enrollments'
        verbose_name = 'Organization Group'

    ROLE_CHOICES = (
        (perms.OrganizationReadMetadataRole.name, 'Read an Organization Metadata'),
        (perms.OrganizationReadEnrollmentsRole.name, 'Read Enrollments Data'),
        (perms.OrganizationReadWriteEnrollmentsRole.name, 'Read and Write Enrollments Data'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=255,
        choices=ROLE_CHOICES,
        default=perms.OrganizationReadMetadataRole.name,
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.role == perms.OrganizationReadMetadataRole.name:
            perms.OrganizationReadMetadataRole.assign_to_group(self, self.organization)
        elif self.role == perms.OrganizationReadEnrollmentsRole.name:
            perms.OrganizationReadEnrollmentsRole.assign_to_group(self, self.organization)
        elif self.role ==  perms.OrganizationReadWriteEnrollmentsRole.name:
            perms.OrganizationReadWriteEnrollmentsRole.assign_to_group(self, self.organization)

    def __str__(self):
        return 'OrgGroup: {} role={}'.format(self.organization.name, self.role)


class OrgGroupFutureMembership(TimeStampedModel):
    """
    Represents the fact that an API-client/user, who does not currently
    have a corresponding ``core.User`` record, can join an existing ``OrgGroup`
    once the ``core.User`` record has been created.

    .. pii: The ``email`` field contains pii in the form of the email address of an API user.
    .. pii_retirement:: local_api
    """
    email = models.EmailField(db_index=True)
    org_group = models.ForeignKey(OrgGroup, db_index=True, related_name='org_group_future_memberships')
    membership_created_at = models.DateTimeField(db_index=True, null=True, blank=True)

    def add_user_to_group(self, user):
        """
        If this future membership hasn't already been marked as created,
        add the given user to the group.  Checks that the given user's
        email field matches this future membership's email field.
        """
        if user.email != self.email:
            raise Exception('Emails for future group membership addition do not match: {} != {}'.format(
                user.email,
                self.email
            ))

        if self.membership_created_at is not None:
            return

        user.groups.add(self.org_group)
        self.membership_created_at = datetime.utcnow()
        self.save()

    def __str__(self):
        return 'Future Org Memberhship: email={}, group={}'.format(self.email, self.org_group)


class Program(TimeStampedModel):
    """
    Table that referrences a course-discovery Program entity.

    .. no_pii::
    """
    class Meta(object):
        app_label = 'enrollments'

    key = models.CharField(unique=True, max_length=255)
    discovery_uuid = models.UUIDField(db_index=True, null=True)
    title = models.CharField(max_length=255)
    managing_organization = models.ForeignKey(Organization, related_name='programs')
    url = models.URLField(null=True)

    def check_access(self, user, access_level):
        """
        Check whether the user has the access level to the program.

        Currently, simply checks whether user has access level to the program's
        managing organization.

        Arguments:
            user (User)
            program (Program)
            access_level

        Returns: bool
        """
        return self.managing_organization.check_access(user, access_level)

    def __str__(self):
        return self.title


class Learner(TimeStampedModel):
    """
    Model that represents an LMS user who may be enrolled in programs and courses.

    .. pii:: The ``email`` field contains pii in the form of the email address of a learner.
    .. pii_types:: email_address
    .. pii_retirement:: local_api
    """
    PENDING = 'pending'
    ACCOUNT_CREATED = 'account_created'
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (ACCOUNT_CREATED, 'Account Created'),
    )

    lms_id = models.IntegerField(db_index=True, null=True)

    # for storing id field provided by org
    external_id = models.CharField(max_length=255, db_index=True, null=True)

    email = models.EmailField(db_index=True)
    status = models.CharField(
        max_length=64,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    history = HistoricalRecords()


class LearnerProgramEnrollment(TimeStampedModel):
    """
    Model that represents the relationship between a Learner and a Program.

    .. no_pii::
    """
    class Meta(object):
        app_label = 'enrollments'
        unique_together = [
            ('learner', 'program')
        ]

    PENDING = 'pending'
    ENROLLED = 'enrolled'
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (ENROLLED, 'Enrolled'),
    )

    # we shouldn't be able to delete any of these fields out from under
    # ourselves if an enrollment record is using them.
    learner = models.ForeignKey(Learner, on_delete=models.PROTECT)
    program = models.ForeignKey(Program, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=64,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    history = HistoricalRecords()
