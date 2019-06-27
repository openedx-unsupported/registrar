""" Utilities for storing files in a backend-agnostic way. """

import logging
import posixpath

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage, get_storage_class

from registrar.apps.api.utils import to_absolute_api_url


logger = logging.getLogger(__name__)


class FilestoreBase(object):
    """
    Abstract base class for file stores.
    """

    def __init__(self, backend, path_prefix=""):
        self.backend = backend
        self.path_prefix = path_prefix

    def store(self, path, contents):
        """
        Store a file.

        Arguments:
            path: Path to file within filestore.
                Will be prefixed by `self.path_prefix`.
            contents: Contents of file.

        Returns: str
            URL to result
        """
        full_path = self.get_full_path(path)
        self.backend.save(full_path, ContentFile(bytes(contents, 'utf-8')))
        return self.get_url(path)

    def retrieve(self, path):
        """
        Retrieve the contents of a file.

        Arguments:
            path: Path to file within filestore.
                Will be prefixed by `self.path_prefix`.

        Returns: str
            UTF-8 decoded file contents.
        """
        full_path = self.get_full_path(path)
        try:
            with self.backend.open(full_path, 'r') as f:
                content = f.read()
                return content if isinstance(content, str) else content.decode('utf-8')
        except IOError as e:
            logger.exception(
                "Could not read file stored at path {}: {}".format(
                    full_path, e
                )
            )
            return None

    def delete(self, path):
        """
        Delete a file.

        Arguments:
            path: Path to file within filestore.
                Will be prefixed by `self.path_prefix`.
        """
        full_path = self.get_full_path(path)
        self.backend.delete(full_path)

    def exists(self, path):
        """
        Check whether a file exists.

        Arguments:
            path: Path to file within filestore.
                Will be prefixed by `self.path_prefix`.

        Returns: bool
        """
        full_path = self.get_full_path(path)
        return self.backend.exists(full_path)

    def get_url(self, path):
        """
        Given the path of a file in the store, return a URL to the file.
        Path will be prefixed by `self.path_prefix`.
        """
        full_path = self.get_full_path(path)
        return self.backend.url(full_path)

    def get_full_path(self, path):
        """
        Apply `self.path_prefix` to `path`. Use POSIX path joining.
        """
        return posixpath.join(self.path_prefix, path)


class FileSystemFilestore(FilestoreBase):
    """
    File storage using Django's FileStorageBackend.
    """

    def get_url(self, path):
        """
        Given the path of a file in the store, return a URL to the file.
        Path will be prefixed by `self.path_prefix`.
        """
        return to_absolute_api_url(settings.MEDIA_URL, self.get_full_path(path))  # pragma: no cover


class S3Filestore(FilestoreBase):
    """
    File storage using S3Boto3Storage.
    """
    pass


def get_filestore(path_prefix=""):
    """
    Return an instance of a FilestoreBase subclass, based on the
    configured default storage backend.
    """
    class_name = get_storage_class().__name__
    if class_name == 'FileSystemStorage':  # pragma: no cover
        return FileSystemFilestore(default_storage, path_prefix)
    elif class_name == 'S3Boto3Storage':
        return S3Filestore(default_storage, path_prefix)
    else:  # pragma: no cover
        raise ImproperlyConfigured(
            'Unsupported storage backend for filestore: {}'.format(class_name)
        )
