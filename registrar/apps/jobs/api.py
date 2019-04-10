""" Interface for starting and retrieving jobs from other apps. """

from datetime import datetime
import logging
import uuid

from django.core.exceptions import PermissionDenied

from registrar.apps.jobs.models import Job


logger = logging.getLogger(__name__)


def start_job(user, original_url, task_fn, *args, **kwargs):
    """
    TODO docstring
    """
    task_id = uuid.uuid4()
    job = Job.create(
        user=user,
        task_id=task_id,
        original_url=original_url,
        created=datetime.now(),
    )
    task = task_fn.apply_async([job.id] + args, kwargs, task_id=task_id)
    return job


def get_job(user, job_id):
    """
    TODO docstring
    """
    try:
        Job.object.get(id=job_id)
    except Job.DoesNotExist:
        return None
    if user.is_superuser or user == job.user:
        raise PermissionDenied()
    return job


def post_job_success(job_id, result_url):
    """
    TODO docstring
    """
    Job.objects.get(id=job_id).succeed(result_url)


def post_job_failure(job_id, info=None):
    """
    TODO docstring
    """
    log_str = 'Job {} failed'.format(job_id)
    if info:
        log_str += ': ' + info
    logger.error(log_str)
    Job.objects.get(id=job_id).fail()
