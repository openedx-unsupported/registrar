""" Interface for starting and retrieving jobs from other apps. """

from datetime import datetime
import uuid

from django.core.exceptions import PermissionDenied

from registrar.apps.jobs.models import Job


def start_job(user, original_url, task_fn, *args, **kwags):
    """
    TODO docstring
    """
    task_id = uuid.uuid4()
    task = task_fn.apply_async([user] + args, kwargs, task_id=task_id)
    return Job.create(
        user=user,
        task_id=task_id,
        original_url=original_url,
        created=datetime.now(),
    )


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
