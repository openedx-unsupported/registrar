
from __future__ import absolute_import

import time

from celery import shared_task
from user_tasks.models import UserTaskArtifact, UserTaskStatus
from user_tasks.tasks import UserTask


@shared_task(base=UserTask, bind=True)
def list_enrollments(self, user_id, program_key, original_url):  # pylint: disable=unused-argument
    """
    A user task for debugging.  Creates user artifact containing given text.
    """
    time.sleep(20)
    UserTaskArtifact.objects.create(status=self.status)


def invoke_program_enrollment_listing(user, program_key, original_url):
    task_args = (user.id, program_key, original_url)
    task_id = list_enrollments.apply_async(task_args).task_id
    job_id = UserTaskStatus.objects.get(task_id=task_id).uuid
    return job_id
