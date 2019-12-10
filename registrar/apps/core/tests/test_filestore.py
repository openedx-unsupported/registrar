""" Tests for core/filestore.py """

from itertools import product

import boto3
import ddt
import mock
import moto
import requests
from django.test import TestCase

from registrar.apps.core.filestore import (
    FilestoreBase,
    FileSystemFilestore,
    S3Filestore,
    get_enrollment_uploads_filestore,
    get_filestore,
    get_job_results_filestore,
    get_program_reports_filestore,
)
from registrar.apps.core.filestore import logger as filestore_logger


@ddt.ddt
class S3FilestoreTests(TestCase):
    """
    Tests for S3Filestore, which is the default Filestore under test settings.
    """
    test_bucket_1 = 'test-bucket1'
    test_bucket_2 = 'test-bucket2'

    def setUp(self):
        # This is unfortunately duplicated from:
        #   registrar.apps.api.v1.tests.test_views:S3MockMixin.
        # It would be ideal to move that mixin to a utilities file and re-use
        # it here, but moto seems to have a bug/"feature" where it only works
        # in modules that explicitly import it.
        super().setUp()
        self._s3_mock = moto.mock_s3()
        self._s3_mock.start()
        conn = boto3.resource('s3')
        conn.create_bucket(Bucket=self.test_bucket_1)
        conn.create_bucket(Bucket=self.test_bucket_2)

    def tearDown(self):
        self._s3_mock.stop()
        super().tearDown()

    bucket_variants = (test_bucket_1, test_bucket_2)
    location_variants = ('', 'bucketprefix/')
    prefix_variants = ("", "prefix", "prefix/withslashes/")
    path_variants = ("file.txt", "folder/file.txt")
    contents_variants = ("filecontents!", "")

    @ddt.data(
        *product(
            bucket_variants,
            location_variants,
            prefix_variants,
            path_variants,
            contents_variants,
        )
    )
    @ddt.unpack
    def test_s3_filestore(self, bucket, location, prefix, path, contents):
        filestore = get_filestore(bucket, prefix)
        with mock.patch.object(filestore.backend, 'location', new=location):
            url = filestore.store(path, contents)
            self.assertTrue(filestore.exists(path))
            self.assertIn(location, url)
            response = requests.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, contents)
            retrieved = filestore.retrieve(path)
            self.assertEqual(retrieved, contents)
            filestore.delete(path)
            self.assertFalse(filestore.exists(path))

    @mock.patch.object(filestore_logger, 'exception', autospec=True)
    def test_s3_filestore_not_found(self, mock_log_exception):
        filestore = get_filestore(self.test_bucket_1, "prefix")
        with mock.patch.object(filestore.backend, 'location', new="bucketprefix/"):
            retrieved = filestore.retrieve("file.txt")
            self.assertIsNone(retrieved)
            mock_log_exception.assert_called_once()

    def test_s3_noop_delete(self):
        filestore = get_filestore(self.test_bucket_1, "")
        self.assertFalse(filestore.exists("x.txt"))
        filestore.delete("x.txt")


@ddt.ddt
class FilestoreTests(TestCase):
    """
    Basic tests for Filestores in general.
    """
    @ddt.data(
        get_enrollment_uploads_filestore,
        get_job_results_filestore,
        get_program_reports_filestore,
    )
    def test_get_filestores(self, get_filestore_function):
        filestore = get_filestore_function()
        assert isinstance(filestore, FilestoreBase)

    @ddt.data(FileSystemFilestore, S3Filestore)
    def test_initialize_filestore_classes(self, filestore_class):
        filestore_class('test-bucket', 'test/path')
