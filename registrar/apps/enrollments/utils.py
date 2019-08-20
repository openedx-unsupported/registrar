""" Utilities for the enrollments app """

from registrar.apps.core.jobs import recent_processing_job_with_prefix_exists


SEPARATOR = ':'
WRITE_PREFIX = 'write'

# Jobs older than this many minutes will NOT block enrollment writing
# for the associated program.
# This is because jobs get stuck permanently in Pending sometimes, which means
# we'd have to modify the DB to un-block writes for associated program.
# We can safely assume that jobs over 30 minutes old will never complete.
# If we add long-running write jobs to Registrar, then this number may need
# to be increased.
MAX_AGE_MINUTES_FOR_BLOCKING_JOB = 30


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
    is currently processing (in progress, pending, or retrying),
    ignoring jobs over `MAX_AGE_MINUTES_FOR_BLOCKING_JOB` minutes old.

    Used to ensure only one bulk task can be run at a time for a program.

    Arguments:
        program_key (str): program key for the program we're checking
    """
    prefix = "{key}{sep}{write}{sep}".format(
        key=program_key,
        sep=SEPARATOR,
        write=WRITE_PREFIX,
    )
    return recent_processing_job_with_prefix_exists(
        prefix, MAX_AGE_MINUTES_FOR_BLOCKING_JOB
    )
