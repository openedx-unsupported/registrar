"""
Models relating to learner program and course enrollments.
"""
from django.db import models
from model_utils.models import TimeStampedModel

from registrar.apps.core.models import Organization
from registrar.apps.enrollments.data import DiscoveryProgram


class Program(TimeStampedModel):
    """
    Table that referrences a course-discovery Program entity.

    .. no_pii::
    """
    class Meta(object):
        app_label = 'enrollments'

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
