"""
Tests for common tasks
"""
from django.test import TestCase
from user_tasks.models import UserTaskArtifact, UserTaskStatus

from .. import tasks
from .factories import UserFactory


class DebugTaskTests(TestCase):
    """ Tests for validating that tasks are working properly. """

    def test_debug_task_happy_path(self):
        with self.assertLogs(level='DEBUG') as log:
            task = tasks.debug_task.apply_async([1, 2], kwargs={'foo': 'bar'})
            task.wait()

        log_message = log.records[0].getMessage()
        self.assertIn("'args': [1, 2]", log_message)
        self.assertIn("'kwargs': {'foo': 'bar'}", log_message)

    def test_debug_user_task_happy_path(self):
        TEST_TEXT = "lorem ipsum"

        user = UserFactory()
        task = tasks.debug_user_task.apply_async((user.id, TEST_TEXT))
        task.wait()

        status = UserTaskStatus.objects.get(task_id=task.id)
        self.assertEqual(status.state, UserTaskStatus.SUCCEEDED)

        artifact = UserTaskArtifact.objects.get(status__user=user)
        self.assertEqual(artifact.text, TEST_TEXT)
