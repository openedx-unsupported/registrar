"""
Models relating to learner program and course enrollments.
"""
from django.contrib.auth.models import Group
from django.db import models
from model_utils.models import TimeStampedModel
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


class OrganizationGroup(Group):
    """
    Group subclass to grant select guardian permissions to a group on an organization level

    .. no_pii::
    """
    class Meta(object):
        app_label = 'enrollments'
        verbose_name = 'Organization Group'

    ROLE_CHOICES = (
        (perms.OrganizationReadMetadataRole.name, 'Read Metadata Only'),
        (perms.OrganizationReadEnrollmentsRole.name, 'Read Enrollments Data'),
        (perms.OrganizationReadWriteEnrollmentsRole.name, 'Read and Write Enrollments Data'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=255,
        choices=ROLE_CHOICES,
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
