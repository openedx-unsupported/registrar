""" Interface for starting and retrieving jobs from other apps. """

from datetime import datetime
import logging
import uuid

from django.core.exceptions import PermissionDenied, ValidationError

from registrar.apps.jobs import states
from registrar.apps.jobs.models import Job


logger = logging.getLogger(__name__)


def start_job(user, original_url, task_fn, *args, **kwargs):
    """
    TODO docstring
    """
    task_id = uuid.uuid4()
    job = Job(
        user=user,
        task_id=task_id,
        original_url=original_url,
        created=datetime.now(),
    )
    job.save()
    import pdb; pdb.set_trace()
    task = task_fn.apply_async([job.id] + list(args), kwargs, task_id=task_id)
    return job


def get_job(user, job_id):
    """
    TODO docstring
    """
    try:
        job = Job.objects.get(id=job_id)
    except ValidationError:
        # job_id is not a UUID
        return None
    except Job.DoesNotExist:
        return None
    if user.is_superuser or user == job.user:
        return job
    else:
        raise PermissionDenied()


def post_job_success(job_id, result_url):
    """
    TODO docstring
    """
    logger.error('HEELLOOOOO')
    job = Job.objects.get(id=job_id)
    _assert_in_progress(job)
    job.result_url = result_url
    job.state = states.SUCCEEDED
    job.save()


def post_job_failure(job_id, info=None):
    """
    TODO docstring
    """
    log_str = 'Job {} failed'.format(job_id)
    if info:
        log_str += ': ' + info
    logger.error(log_str)
    job = Job.objects.get(id=job_id)
    _assert_in_progress(job)
    job.state = states.FAILED
    job.save()


def _assert_in_progress(job):
    """
    Raise a ValueError if job is not currently In Progress.
    """
    if job.state != states.IN_PROGRESS:
        raise ValueError(
            'Job can only be marked as Succeeded from state In Progress' +
            '(job_id = {})'.format(job.id)
        )
