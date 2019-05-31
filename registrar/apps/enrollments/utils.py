""" Utilities for the enrollments app """

from registrar.apps.core.jobs import processing_job_with_prefix_exists


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
    return processing_job_with_prefix_exists(program_prefix)
