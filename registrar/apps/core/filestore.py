""" Utilities for storing files in a backend-agnostic way. """
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage, get_storage_class

from registrar.apps.api.utils import to_absolute_api_url


class FilestoreBase(object):
    """
    Abstract base class for file stores.
    """

    def __init__(self, backend):
        self.backend = backend

    def store(self, path, contents):
        """
        Store a file.

        Arguments:
            path: Path to file within filestore.
            contents: Contents of file.

        Returns: str
            URL to result
        """
        self.backend.save(path, ContentFile(bytes(contents, 'utf-8')))
        return self.get_url(path)

    def get_url(self, path):
        """
        Given the path of a file in the store, return a URL to the file.

        Must be overriden in subclass.
        """
        raise NotImplementedError  # pragma: no cover


class FileSystemFilestore(FilestoreBase):
    """
    File storage using Django's FileStorageBackend.
    """

    def get_url(self, path):
        """
        Given the path of a file in the store, return a URL to the file.
        """
        return to_absolute_api_url(settings.MEDIA_URL, path)  # pragma: no cover


class S3Filestore(FilestoreBase):
    """
    File storege using S3Boto3Storage.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import boto3
        self.s3_client = boto3.client('s3')

    def get_url(self, path):
        """
        Given the path of a file in the store, return a URL to the file.

        Generates a signed GET URL to the resource that expires in the
        configured amount of time.
        """
        params = {
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': path,
        }
        return self.s3_client.generate_presigned_url('get_object', Params=params)


def get_filestore():
    """
    Return an instance of a FilestoreBase subclass, based on the
    configured default storage backend.
    """
    class_name = get_storage_class().__name__
    if class_name == 'FileSystemStorage':
        return FileSystemFilestore(default_storage)
    elif class_name == 'S3Boto3Storage':
        return S3Filestore(default_storage)
    else:  # pragma: no cover
        raise ImproperlyConfigured(
            'Unsupported storage backend for filestore: {}'.format(class_name)
        )
