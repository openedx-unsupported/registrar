"""
Models relating to learner program and course enrollments.
"""
from django.contrib.auth.models import Group
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from registrar.apps.core.models import Organization as Org


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
    managing_organization = models.ForeignKey(Org, related_name='programs')
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
