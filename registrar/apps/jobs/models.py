""" Models for asychronous jobs. """

import uuid
from django.conf import settings
from django.db import models

from registrar.apps.jobs import states


class Job(models.Model):
    """
    TODO docstring
    """
    class Meta(object):
        app_label = 'jobs'

    STATE_CHOICES = [(state, state) for state in states.ALL]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.UUIDField(editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    original_url = models.URLField()
    created = models.DateTimeField()
    state = models.CharField(
        max_length=11, choices=STATE_CHOICES, default=states.IN_PROGRESS
    )
    result_url = models.URLField(null=True, default=None)

    def __str__(self):
        return 'Job {}'.format(self.id)
