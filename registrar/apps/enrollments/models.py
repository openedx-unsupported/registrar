"""
Models relating to learner program and course enrollments.
"""
from django.db import models
from model_utils.models import TimeStampedModel

from registrar.apps.core.models import Organization


class Program(TimeStampedModel):
    """
    Table that referrences a course-discovery Program entity.

    .. no_pii::
    """
    class Meta(object):
        app_label = 'enrollments'

    key = models.CharField(unique=True, max_length=255)
    discovery_uuid = models.UUIDField(db_index=True, null=True)
    title = models.CharField(max_length=255, null=True)
    managing_organization = models.ForeignKey(Organization, related_name='programs')
    url = models.URLField(null=True)

    def __str__(self):
        return self.title
