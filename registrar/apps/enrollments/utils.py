""" Utilities for the enrollments app """

from registrar.apps.core.jobs import processing_job_with_prefix_exists


SEPARATOR = ':'
WRITE_PREFIX = 'write'


def build_enrollment_job_status_name(program_key, action, task_name):
    """
    Build the UserTaskStatus.name for the given program, action, and task name.

    Arguments:
        program_key (str): The key of the program the task is acting on.
        action (str): The type of action performed by the task (e.g. "read" or "write").
        task_name (str): The name of the task that is being executed.
    """
    return SEPARATOR.join((program_key, action, task_name))


def is_enrollment_write_blocked(program_key):
    """
    Returns whether or not a bulk enrollment job for a particular program
    is currently processing (in progress, pending, or retrying).

    Used to ensure only one bulk write task can be run at a time for a program.

    Arguments:
        program_key (str): program key for the program we're checking
    """
    prefix = "{key}{sep}{write}{sep}".format(
        key=program_key,
        sep=SEPARATOR,
        write=WRITE_PREFIX,
    )
    return processing_job_with_prefix_exists(prefix)
