"""
Python API for Registrar 'jobs', which are a thin abstraction around UserTasks.

A 'job' is an asynchronous operation with a creation date-time, state, and
result URL. Every job is identified by a UUID-4 (called a job_id).

In its current implementation, every job is run by a single UserTask,
which is type of user-specific Celery task that saves its status
(UserTaskStatus) and produces persisted output (UserTaskArtifacts).
The job_id is equal to the UserTask ID. If this module were to be extended
in the future to include retrying tasks, the job_id could be decoupled
from the UserTask ID. For this reason, we attempt not to expose the relationship
between job_ids and UserTask IDs outside of this module.
"""

from collections import namedtuple
import logging
import uuid

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from user_tasks.models import UserTaskArtifact, UserTaskStatus

from registrar.apps.core.job_storage import get_job_result_store
from registrar.apps.core.permissions import JOB_GLOBAL_READ


JobStatus = namedtuple('JobStatus', ['created', 'state', 'result'])

logger = logging.getLogger(__name__)

_RESULT_ARTIFACT_NAME = 'Job Result'
_RESULT_STORAGE = get_job_result_store()


def start_job(user, task_fn, *args, **kwargs):
    """
    Start a new job

    Arguments.
        user (User): User who owns the job.
        task_fn: UserTask function that will be invoked to perform job.
            The first three parameters of the function should be
            `self` (the Celery task instance), `job_id`, and `user_id`.
            They will be passed in automatically. The function may take
            additional parameters.
        *args/**kwargs: Additional arguments to pass to task_fn.

    Returns: str
        UUID-4 job ID string.
    """
    job_id = str(uuid.uuid4())
    task_fn.apply_async([job_id, user.id] + list(args), kwargs, task_id=job_id)
    return job_id


def get_job_status(user, job_id):
    """
    Get the status of a job.

    Arguments:
        user (User): User attempting to read job status.
        job_id (str): UUID-4 job ID string.

    Raises:
        PermissionDenied: User may not read job status.
            Only (1) the creator of the job, and (2) users
            granted who have been `JOB_GLOBAL_READ` may read a job's status.
    """
    try:
        task_status = UserTaskStatus.objects.get(task_id=job_id)
    except UserTaskStatus.DoesNotExist:
        raise ObjectDoesNotExist("No such job: {}".format(job_id))
    if user.has_perm(JOB_GLOBAL_READ) or user == task_status.user:
        return JobStatus(
            task_status.created,
            task_status.state,
            _get_result(job_id, task_status),
        )
    else:
        raise PermissionDenied()


def _get_result(job_id, task_status):
    """
    Get the result URL of a job.

    Will be stored in the `result` field of the first
    UserTaskArtifact with the name `_RESULT_ARTIFACT_NAME`
    of `task_status`.

    Arguments:
        job_id (str): UUID-4 job ID string.
        task_status (UserTaskStatus)

    Returns: str|NoneType
        Returns URL, or None if no result.
    """
    artifacts = UserTaskArtifact.objects.filter(
        status=task_status, name=_RESULT_ARTIFACT_NAME
    )
    if artifacts:
        if artifacts.count() > 1:
            logger.error(
                'Multiple UserTaskArtifacts for job ' +
                '(job_id = {}, UserTaskStatus.uuid = {}). '.format(
                    job_id, task_status.uuid
                ) +
                'First artifact will be returned'
            )
        return artifacts.first().url
    else:
        return None


def post_job_success(job_id, results, file_extension):
    """
    Mark a job as Succeeded, providing a result.

    Arguments:
        job_id (str): UUID-4 string identifying Job
        results (str): String containing results of job; to be saved to file.
        file_extension (stR): Desired file extension for result file(e.g. 'json').
    """
    result_url = _RESULT_STORAGE.store(job_id, results, file_extension)
    task_status = UserTaskStatus.objects.get(task_id=job_id)
    _affirm_job_in_progress(job_id, task_status)
    UserTaskArtifact.objects.create(
        status=task_status, name=_RESULT_ARTIFACT_NAME, url=result_url
    )
    task_status.succeed()


def post_job_failure(job_id, message):
    """
    Mark a job as Failed, providing `message` as a reason.

    Logs the message and saves an artifact with the message.
    Intended to be called from the job itself.

    Arguments:
        job_id (str): UUID-4 string identifying Job
        message: the reason the job failed
    """
    task_status = UserTaskStatus.objects.get(task_id=job_id)
    _affirm_job_in_progress(job_id, task_status)
    log_message = "Job {} failed. {}".format(job_id, message)
    logger.error(log_message)
    task_status.fail(log_message)  # Creates UserTaskArtifact with name "Error"


def _affirm_job_in_progress(job_id, task_status):
    """
    Raise a ValueError if job is not currently In Progress.

    Arguments:
        job_id (str): UUID-4 string identifying Job
        task_status (UserTaskStatus): user task status associated with job
    """
    if task_status.state != UserTaskStatus.IN_PROGRESS:
        raise ValueError(
            'Job can only be marked as Succeeded from state In Progress' +
            '(job_id = {})'.format(job_id)
        )
