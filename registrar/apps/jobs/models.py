""" Models for asychronous jobs. """

import uuid
from django.conf import settings
from django.db import models

from registrar.apps.jobs import states


class Job(models.Model):
    """
    TODO docstring
    """

    STATE_CHOICES = [(state, state) for state in states.ALL]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.UUIDField(editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    original_url = models.URLField()
    created = models.DateTimeField()
    state = models.CharField(max_length=11, choices=STATE_CHOICES, default=IN_PROGRESS)
    result_url = models.URLField(null=True, default=None)

    def succeed(self, result_url):
        """
        TODO docstring
        """
        self._assert_in_progress()
        self.result_url = result_url
        self.state = state.SUCCEEDED

    def fail(self):
        """
        TODO docstring
        """
        self._assert_in_progress()
        self.state = state.FAILED

    def _assert_in_progress(self):
        """
        Raise a ValueError if job is not currently In Progress.
        """
        if self.state != state.IN_PROGRESS:
            raise ValueError(
                'Job can only be marked as Succeeded from state In Progress'
            )
