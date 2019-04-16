""" Utilities for storing the results of jobs. """

from urllib.parse import urljoin

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage, get_storage_class


class JobResultStorageBase(object):
    """
    Abstract base class for job result storage backends.
    """

    def __init__(self, backend):
        self.backend = backend

    def store(self, job_id, results, file_extension):
        """
        Store the result of a job (in a fashion determined by the backend).

        Arguments:
            job_id (str): UUID-4 job ID string.
            results (str): Content of result file.
            file_extension (str): Extension that result file should have.

        Returns: str
            URL to result
        """
        result_path = 'job-results/{}.{}'.format(job_id, file_extension)
        self.backend.save(result_path, ContentFile(bytes(results, 'utf-8')))
        return self._get_url(result_path)

    def _get_url(self, result_path):
        """
        Given the path of a job result, return a URL to the result.

        Must be overriden in subclass.
        """
        raise NotImplementedError


class FileSystemJobResultStorage(JobResultStorageBase):
    """
    Job result storage using Django's FileStorageBackend.
    """

    def _get_url(self, result_path):
        """
        Given the path of a job result, return a URL to the result.

        TODO: This doesn't work, because we don't currently have a way to
        return absolute URLs outisde the context of a request. We end up
        just returning something along the lines of '/media/abcd.json'.
        """
        return urljoin(settings.MEDIA_URL, result_path)


class S3JobResultStorage(JobResultStorageBase):
    """
    Job result storage using S3Boto3Storage.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import boto3
        self.s3_client = boto3.client('s3')

    def _get_url(self, result_path):
        """
        Given the path of a job result, return a URL to the result.

        Generates a signed GET URL to the resource that expires in the
        configured amount of time.
        """
        params = {
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': result_path,
        }
        return self.s3_client.generate_presigned_url('get_object', Params=params)


def get_job_result_store():
    """
    Return an instance of a JobResultStorageBase subclass, based on the
    configured default storage backend.
    """
    class_name = get_storage_class().__name__
    if class_name == 'S3Boto3Storage':
        return S3JobResultStorage(default_storage)
    elif class_name == 'FileSystemStorage':
        return FileSystemJobResultStorage(default_storage)
    else:
        raise ImproperlyConfigured(
            'Unsupported storage backend for job reults: {}'.format(class_name)
        )
