"""
Unit tests for the enrollment.tasks module.
"""
import mock

from django.test import TestCase

from registrar.apps.enrollments import tasks


class DebugTaskTests(TestCase):
    """ Tests for validating that tasks are working properly. """

    @mock.patch('registrar.apps.enrollments.tasks.log', autospec=True)
    def test_debug_task_happy_path(self, mock_logger):
        task = tasks.debug_task.apply([1, 2], kwargs={'foo': 'bar'})
        task.wait()

        self.assertEqual(mock_logger.debug.call_count, 1)
        debug_call_argument = mock_logger.debug.call_args_list[0][0][0]
        self.assertIn("'args': [1, 2]", debug_call_argument)
        self.assertIn("'kwargs': {'foo': 'bar'}", debug_call_argument)
