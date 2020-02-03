"""
Tests for jobs.py functions.

Most jobs.py functions are indirectly tested by view tests,
so we only test a subset of them here.
"""

from itertools import cycle

import ddt
from django.test import TestCase
from user_tasks.models import UserTaskStatus

from ..jobs import get_processing_jobs_for_user
from .factories import UserFactory


@ddt.ddt
class GetProcessingJobsForUserTests(TestCase):
    """
    Tests for get_processing_jobs_for_user
    """

    job_ids = [
        'a8f72677-f38f-46bb-883d-bd4e35b72f19',
        '7a881fc6-e9d3-4d0d-b906-2c6462f9895c',
        'a58fb3b3-b9e6-45f5-a58c-9f0950c2df01',
        '382c6037-a25b-40f3-b6f2-d0952052a4f7',
        '29737d91-2fd5-473c-987c-12225aed3a20',
        '59acb9b1-e828-4fa2-a79a-0d41e5b29c29',
    ]
    noise_job_ids = [
        '3e977168-d03a-4809-bae5-f908e8c372d4',
        'ca062aa0-2ea0-460b-9570-502b9ff79aac',
        'b7cb10ea-40dc-4e93-a0e5-37bd92385855',
        'dec5b1dc-3451-4366-9556-75c89e814163',
        '0372690c-90f5-4fb3-bb46-b6ca77c266e2',
        '2776bae4-480d-45c0-8caf-5dbed317fb2e',
        '6af666b0-4f57-4385-af18-34eb17cfb1da',
        'd96a2e89-d4a4-4559-a58e-a93d0c5df994',
        '4d2b8ce9-5c20-4824-b41c-dd0b62827bb0',
        'eecb0454-afe2-4780-9958-5724b9986e53',
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.other_user = UserFactory()
        cls.user = UserFactory()
        states = [
            UserTaskStatus.PENDING,
            UserTaskStatus.IN_PROGRESS,
            UserTaskStatus.SUCCEEDED,
            UserTaskStatus.FAILED,
            UserTaskStatus.CANCELED,
            UserTaskStatus.RETRYING,
        ]
        state_cycle = cycle(states)
        for job_id in cls.noise_job_ids:
            cls.create_dummy_job_status(
                job_id, next(state_cycle), cls.other_user
            )

    @classmethod
    def create_dummy_job_status(cls, job_id, state, user):
        return UserTaskStatus.objects.create(
            state=state,
            user=user,
            task_id=job_id,
            total_steps=1,
        )

    @ddt.unpack
    @ddt.data(
        (
            [
                (0, UserTaskStatus.PENDING),
                (1, UserTaskStatus.IN_PROGRESS),
                (2, UserTaskStatus.SUCCEEDED),
                (3, UserTaskStatus.FAILED),
                (4, UserTaskStatus.CANCELED),
                (5, UserTaskStatus.RETRYING),
            ],
            {0, 1, 5},
        ),
        (
            [
                (0, UserTaskStatus.PENDING),
                (1, UserTaskStatus.IN_PROGRESS),
                (2, UserTaskStatus.IN_PROGRESS),
                (3, UserTaskStatus.RETRYING),
                (4, UserTaskStatus.RETRYING),
            ],
            {0, 1, 2, 3, 4},
        ),
        (
            [
                (0, UserTaskStatus.SUCCEEDED),
                (1, UserTaskStatus.SUCCEEDED),
                (2, UserTaskStatus.SUCCEEDED),
                (3, UserTaskStatus.FAILED),
                (4, UserTaskStatus.FAILED),
                (5, UserTaskStatus.FAILED),
            ],
            set(),
        ),
        ([], set()),
    )
    def test_get_processing_jobs(self, user_tasks, expected_jobs_ns):
        for n, state in user_tasks:
            self.create_dummy_job_status(self.job_ids[n], state, self.user)
        actual_jobs = get_processing_jobs_for_user(self.user)
        actual_job_ids = {j.job_id for j in actual_jobs}
        expected_job_ids = {self.job_ids[n] for n in expected_jobs_ns}
        self.assertEqual(actual_job_ids, expected_job_ids)
