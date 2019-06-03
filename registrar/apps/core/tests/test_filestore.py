""" Tests for core/filestore.py """

from itertools import product

import boto3
import ddt
import mock
import moto
import requests
from django.conf import settings
from django.test import TestCase

from registrar.apps.core.filestore import get_filestore
from registrar.apps.core.filestore import logger as filestore_logger


@ddt.ddt
class S3FilestoreTests(TestCase):
    """
    Tests for S3Filestore, which is the default Filestore under test settings.
    """

    @classmethod
    def setUpClass(cls):
        # This is unfortunately duplicated from:
        #   registrar.apps.api.v1.tests.test_views:S3MockMixin.
        # It would be ideal to move that mixin to a utilities file and re-use
        # it here, but moto seems to have a bug/"feature" where it only works
        # in modules that explicitly import it.
        super().setUpClass()
        cls._s3_mock = moto.mock_s3()
        cls._s3_mock.start()
        conn = boto3.resource('s3')
        conn.create_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)

    @classmethod
    def tearDownClass(cls):
        cls._s3_mock.stop()
        super().tearDownClass()

    prefix_variants = ("", "prefix", "prefix/withslashes/")
    path_variants = ("file.txt", "folder/file.txt")
    contents_variants = ("filecontents!", "")

    @ddt.data(*(product(prefix_variants, path_variants, contents_variants)))
    @ddt.unpack
    def test_s3_filestore(self, prefix, path, contents):
        filestore = get_filestore(prefix)

        url = filestore.store(path, contents)
        self.assertTrue(filestore.exists(path))
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, contents)
        retrieved = filestore.retrieve(path)
        self.assertEqual(retrieved, contents)

        filestore.delete(path)
        self.assertFalse(filestore.exists(path))

    @mock.patch.object(filestore_logger, 'exception', autospec=True)
    def test_s3_filestore_not_found(self, mock_log_exception):
        filestore = get_filestore("prefix")
        retrieved = filestore.retrieve("file.txt")
        self.assertIsNone(retrieved)
        mock_log_exception.assert_called_once()

    def test_s3_noop_delete(self):
        filestore = get_filestore("")
        self.assertFalse(filestore.exists("x.txt"))
        filestore.delete("x.txt")
