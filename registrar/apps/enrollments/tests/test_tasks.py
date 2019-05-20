"""
Unit tests for the enrollment.tasks module.
"""
from collections import namedtuple
import uuid
import mock

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from requests.exceptions import HTTPError
from user_tasks.models import UserTaskArtifact, UserTaskStatus

from registrar.apps.core.tests.factories import UserFactory, OrganizationFactory
from registrar.apps.enrollments import tasks
from registrar.apps.enrollments.tests.factories import ProgramFactory
from registrar.apps.enrollments.constants import (
    PROGRAM_ENROLLMENT_ENROLLED,
    PROGRAM_ENROLLMENT_PENDING,
    COURSE_ENROLLMENT_ACTIVE,
    COURSE_ENROLLMENT_INACTIVE,
)

FakeRequest = namedtuple('FakeRequest', ['url'])
FakeResponse = namedtuple('FakeResponse', ['status_code'])


class EnrollmentTestsMixin(object):
    """ Tests for task error behavior. """
    enrollment_statuses = (None, None)
    mocked_get_enrollments_method = None
    mock_base = 'registrar.apps.enrollments.tasks.'

    def setUp(self):
        self.user = UserFactory()
        org = OrganizationFactory(name='STEM Institute')
        self.program = ProgramFactory(managing_organization=org)
        self.enrollment_data = [
            self._enrollment('0001', self.enrollment_statuses[0], True),
            self._enrollment('0002', self.enrollment_statuses[1], True),
            self._enrollment('0003', self.enrollment_statuses[0], False),
            self._enrollment('0004', self.enrollment_statuses[1], False),
        ]

    def spawn_task(self, program, file_format='json'):
        """ Overridden in children """
        pass  # pragma: no cover

    def _enrollment(self, student_key, status, exists):
        """ Helper to create enrollment record """
        return {
            'student_key': student_key,
            'status': status,
            'account_exists': exists
        }

    def test_program_not_found(self):
        task = self.spawn_task("program-nonexistant")
        task.wait()

        status = UserTaskStatus.objects.get(task_id=task.id)
        self.assertEqual(status.state, UserTaskStatus.FAILED)
        self.assertIn("Bad program key", status.artifacts.first().text)

    def test_http_error(self):
        with mock.patch(self.mock_base + self.mocked_get_enrollments_method) as mock_get_enrollments:
            error = HTTPError(request=FakeRequest('registrar.edx.org'), response=FakeResponse(500))
            mock_get_enrollments.side_effect = error
            task = self.spawn_task(self.program.key)
            task.wait()

        status = UserTaskStatus.objects.get(task_id=task.id)
        self.assertEqual(status.state, UserTaskStatus.FAILED)
        self.assertIn("HTTP error 500 when getting enrollments at registrar.edx.org", status.artifacts.first().text)

    def test_invalid_data(self):
        with mock.patch(self.mock_base + self.mocked_get_enrollments_method) as mock_get_enrollments:
            mock_get_enrollments.side_effect = ValidationError()
            task = self.spawn_task(self.program.key)
            task.wait()

        status = UserTaskStatus.objects.get(task_id=task.id)
        self.assertEqual(status.state, UserTaskStatus.FAILED)
        error_text = status.artifacts.first().text
        self.assertIn("Invalid enrollment data from LMS", error_text)

    def test_invalid_format(self):
        with mock.patch(self.mock_base + self.mocked_get_enrollments_method) as mock_get_enrollments:
            mock_get_enrollments.return_value = self.enrollment_data
            exception_raised = False
            try:
                task = self.spawn_task(self.program.key, 'invalid-format')
                task.wait()
            except ValueError as e:
                self.assertIn('Invalid file_format', str(e))
                exception_raised = True
        self.assertTrue(exception_raised)


class ProgramEnrollmentTaskTests(EnrollmentTestsMixin, TestCase):
    """ Tests for task error behavior. """
    enrollment_statuses = (
        PROGRAM_ENROLLMENT_ENROLLED,
        PROGRAM_ENROLLMENT_PENDING,
    )
    mocked_get_enrollments_method = 'get_program_enrollments'

    def spawn_task(self, program, file_format='json'):
        job_id = str(uuid.uuid4())
        return tasks.list_program_enrollments.apply_async(
            (
                job_id,
                self.user.id,
                file_format,
                program
            ),
            task_id=job_id
        )


class CourseEnrollmentTaskTests(EnrollmentTestsMixin, TestCase):
    """ Tests for task error behavior. """
    enrollment_statuses = (
        COURSE_ENROLLMENT_ACTIVE,
        COURSE_ENROLLMENT_INACTIVE,
    )
    mocked_get_enrollments_method = 'get_course_run_enrollments'

    def spawn_task(self, program, file_format='json'):
        job_id = str(uuid.uuid4())
        return tasks.list_course_run_enrollments.apply_async(
            (
                job_id,
                self.user.id,
                file_format,
                program,
                'course-1'
            ),
            task_id=job_id
        )


class DebugTaskTests(TestCase):
    """ Tests for validating that tasks are working properly. """

    @mock.patch('registrar.apps.enrollments.tasks.log', autospec=True)
    def test_debug_task_happy_path(self, mock_logger):
        task = tasks.debug_task.apply_async([1, 2], kwargs={'foo': 'bar'})
        task.wait()

        self.assertEqual(mock_logger.debug.call_count, 1)
        debug_call_argument = mock_logger.debug.call_args_list[0][0][0]
        self.assertIn("'args': [1, 2]", debug_call_argument)
        self.assertIn("'kwargs': {'foo': 'bar'}", debug_call_argument)

    def test_debug_user_task_happy_path(self):
        TEST_TEXT = "lorem ipsum"

        user = UserFactory()
        task = tasks.debug_user_task.apply_async((user.id, TEST_TEXT))
        task.wait()

        status = UserTaskStatus.objects.get(task_id=task.id)
        self.assertEqual(status.state, UserTaskStatus.SUCCEEDED)

        artifact = UserTaskArtifact.objects.get(status__user=user)
        self.assertEqual(artifact.text, TEST_TEXT)
