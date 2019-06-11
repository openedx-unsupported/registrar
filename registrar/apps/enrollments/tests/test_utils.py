""" Tests for enrollment utils """

from itertools import cycle
from uuid import uuid4

import ddt
from django.test import TestCase
from user_tasks.models import UserTaskStatus

from registrar.apps.core.tests.factories import OrganizationFactory, UserFactory
from registrar.apps.enrollments.tests.factories import ProgramFactory
from registrar.apps.enrollments.utils import (
    build_enrollment_job_status_name,
    get_processing_jobs_for_user,
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
        task_name = build_enrollment_job_status_name(self.program.key, self.TASK_NAME)
        IsEnrollmentJobProcessingTests.create_dummy_job_status(state, self.user, task_name)
        job_in_progress = is_enrollment_job_processing(self.program.key)
        self.assertEqual(expected, job_in_progress)

    def test_different_program(self):
        task_name = build_enrollment_job_status_name(self.program.key, self.TASK_NAME)
        IsEnrollmentJobProcessingTests.create_dummy_job_status(UserTaskStatus.IN_PROGRESS, self.user, task_name)
        self.assertFalse(is_enrollment_job_processing(self.program2.key))

    def test_wrong_name(self):
        task_name = build_enrollment_job_status_name(self.TASK_NAME, self.program.key)
        IsEnrollmentJobProcessingTests.create_dummy_job_status(UserTaskStatus.IN_PROGRESS, self.user, task_name)
        self.assertFalse(is_enrollment_job_processing(self.program.key))


@ddt.ddt
class GetProcessingJobsForUserTests(EnrollmentJobTests):
    """
    Tests for get_processing_jobs_for_user
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.other_user = UserFactory()
        states = [
            UserTaskStatus.PENDING,
            UserTaskStatus.IN_PROGRESS,
            UserTaskStatus.SUCCEEDED,
            UserTaskStatus.FAILED,
            UserTaskStatus.CANCELED,
            UserTaskStatus.RETRYING,
        ]
        state_cycle = cycle(states)
        for i in range(10):
            cls.create_dummy_job_status(next(state_cycle), cls.other_user, 'noise-status-{}'.format(i))

    @ddt.unpack
    @ddt.data(
        (
            [
                ('a', UserTaskStatus.PENDING),
                ('b', UserTaskStatus.IN_PROGRESS),
                ('c', UserTaskStatus.SUCCEEDED),
                ('d', UserTaskStatus.FAILED),
                ('e', UserTaskStatus.CANCELED),
                ('f', UserTaskStatus.RETRYING),
            ],
            ['a', 'b', 'f']
        ),
        (
            [
                ('a', UserTaskStatus.PENDING),
                ('b', UserTaskStatus.IN_PROGRESS),
                ('c', UserTaskStatus.IN_PROGRESS),
                ('d', UserTaskStatus.RETRYING),
                ('e', UserTaskStatus.RETRYING),
            ],
            ['a', 'b', 'c', 'd', 'e']
        ),
        (
            [
                ('a', UserTaskStatus.SUCCEEDED),
                ('b', UserTaskStatus.SUCCEEDED),
                ('c', UserTaskStatus.SUCCEEDED),
                ('d', UserTaskStatus.FAILED),
                ('e', UserTaskStatus.FAILED),
                ('f', UserTaskStatus.FAILED),
            ],
            []
        ),
        ([], []),
    )
    def test_get_processing_jobs(self, user_tasks, expected):
        for name, state in user_tasks:
            GetProcessingJobsForUserTests.create_dummy_job_status(state, self.user, name)
        processing_jobs = get_processing_jobs_for_user(self.user)
        self.assert_statuses_in(expected, processing_jobs)

    def assert_statuses_in(self, expected_status_names, statuses):
        status_names = [s.name for s in statuses]
        self.assertEqual(len(expected_status_names), len(status_names))
        for expected_status_name in expected_status_names:
            self.assertIn(expected_status_name, status_names)
