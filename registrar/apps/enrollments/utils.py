""" Utilities for the enrollments app """
from user_tasks.models import UserTaskStatus


USER_TASK_STATUS_PROCESSING_STATES = [
    UserTaskStatus.PENDING,
    UserTaskStatus.IN_PROGRESS,
    UserTaskStatus.RETRYING,
]


def build_enrollment_job_status_name(program_key, task_name):
    """
    Build the UserTaskStatus.name for the given task and program

    Arguments:
        program_key (str): program key for the program we're writing enrollments
        task_name (str): the name of the task that is being executed
    """
    return "{}:{}".format(program_key, task_name)


def is_enrollment_job_processing(program_key):
    """
    Returns whether or not a bulk enrollment job for a particular program
    is currently processing (in progress, pending, or retrying)

    Used to ensure only one bulk task can be run at a time for a program.

    Arguments:
        program_key (str): program key for the program we're checking
    """
    program_prefix = build_enrollment_job_status_name(program_key, '')
    return UserTaskStatus.objects.filter(
        name__startswith=program_prefix,
        state__in=USER_TASK_STATUS_PROCESSING_STATES,
    ).exists()


def get_processing_jobs_for_user(user):
    """
    Get the statuses of any processing jobs for the given user

    Arguments:
        user (User): User attempting to read job statuses.

    Returns: queryset of processing UserTaskStatuses for the given user
    """
    return UserTaskStatus.objects.filter(
        user=user,
        state__in=USER_TASK_STATUS_PROCESSING_STATES
    )
