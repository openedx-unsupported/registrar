""" Tests for enrollment utils """

from uuid import uuid4

import ddt
from django.test import TestCase
from user_tasks.models import UserTaskStatus

from registrar.apps.core.tests.factories import OrganizationFactory, UserFactory
from registrar.apps.enrollments.tests.factories import ProgramFactory
from registrar.apps.enrollments.utils import (
    build_enrollment_job_status_name,
    is_enrollment_job_processing,
)


class EnrollmentJobTests(TestCase):
    """ Tests for enrollment job util functions """
    TASK_NAME = "test-dummy-task"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory()
        cls.org = OrganizationFactory(name='Test Organization')
        cls.program = ProgramFactory(
            managing_organization=cls.org,
        )
        cls.program2 = ProgramFactory(
            managing_organization=cls.org,
        )

    @classmethod
    def create_dummy_job_status(cls, state, user, name):
        return UserTaskStatus.objects.create(
            state=state,
            name=name,
            user=user,
            task_id=uuid4(),
            total_steps=1,
        )


@ddt.ddt
class IsEnrollmentJobProcessingTests(EnrollmentJobTests):
    """
    Tests for is_enrollment_job_processing
    """

    @ddt.unpack
    @ddt.data(
        (UserTaskStatus.PENDING, True),
        (UserTaskStatus.IN_PROGRESS, True),
        (UserTaskStatus.SUCCEEDED, False),
        (UserTaskStatus.FAILED, False),
        (UserTaskStatus.CANCELED, False),
        (UserTaskStatus.RETRYING, True),
    )
    def test_job_processing(self, state, expected):
        task_name = build_enrollment_job_status_name(self.program.key, 'write', self.TASK_NAME)
        self.create_dummy_job_status(state, self.user, task_name)
        job_in_progress = is_enrollment_job_processing(self.program.key)
        self.assertEqual(expected, job_in_progress)

    def test_different_program(self):
        task_name = build_enrollment_job_status_name(self.program.key, 'write', self.TASK_NAME)
        self.create_dummy_job_status(UserTaskStatus.IN_PROGRESS, self.user, task_name)
        self.assertFalse(is_enrollment_job_processing(self.program2.key))

    def test_wrong_name(self):
        task_name = build_enrollment_job_status_name(self.TASK_NAME, 'write', self.program.key)
        self.create_dummy_job_status(UserTaskStatus.IN_PROGRESS, self.user, task_name)
        self.assertFalse(is_enrollment_job_processing(self.program.key))
