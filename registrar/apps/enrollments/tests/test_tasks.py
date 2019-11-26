"""
Unit tests for the enrollment.tasks module.
"""
import json
from collections import OrderedDict, namedtuple
from uuid import UUID

import boto3
import ddt
import mock
import moto
from django.conf import settings
from django.test import TestCase
from requests.exceptions import HTTPError
from rest_framework.exceptions import ValidationError

from registrar.apps.common.data import DiscoveryCourseRun, DiscoveryProgram
from registrar.apps.common.tests.mixins import BaseTaskTestMixin
from registrar.apps.core.constants import UPLOADS_PATH_PREFIX
from registrar.apps.core.filestore import get_filestore
from registrar.apps.core.models import Program
from registrar.apps.enrollments import tasks
from registrar.apps.enrollments.constants import (
    COURSE_ENROLLMENT_ACTIVE,
    COURSE_ENROLLMENT_INACTIVE,
    PROGRAM_ENROLLMENT_ENROLLED,
    PROGRAM_ENROLLMENT_PENDING,
)


FakeRequest = namedtuple('FakeRequest', ['url'])
FakeResponse = namedtuple('FakeResponse', ['status_code'])


uploads_filestore = get_filestore(UPLOADS_PATH_PREFIX)


class BaseEnrollmentTaskTestMixin(BaseTaskTestMixin):
    mock_base = 'registrar.apps.enrollments.data.'


@ddt.ddt
class ListEnrollmentTaskTestMixin(BaseEnrollmentTaskTestMixin):
    """ Tests for enrollment listing task error behavior. """

    # Override in subclass
    enrollment_statuses = (None, None)
    mocked_get_enrollments_method = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.enrollment_data = [
            cls._enrollment('0001', cls.enrollment_statuses[0], True),
            cls._enrollment('0002', cls.enrollment_statuses[1], True),
            cls._enrollment('0003', cls.enrollment_statuses[0], False),
            cls._enrollment('0004', cls.enrollment_statuses[1], False),
        ]

    @staticmethod
    def _enrollment(student_key, status, exists):
        """ Helper to create enrollment record """
        return {
            'student_key': student_key,
            'status': status,
            'account_exists': exists
        }

    @ddt.data(500, 404)
    def test_http_error(self, status_code):
        with mock.patch(self.mock_base + self.mocked_get_enrollments_method) as mock_get_enrollments:
            error = HTTPError(request=FakeRequest('registrar.edx.org'), response=FakeResponse(status_code))
            mock_get_enrollments.side_effect = error
            task = self.spawn_task()
            task.wait()
        expected_msg = "HTTP error {} when getting enrollments at registrar.edx.org".format(status_code)
        self.assert_failed(expected_msg)

    def test_invalid_data(self):
        with mock.patch(self.mock_base + self.mocked_get_enrollments_method) as mock_get_enrollments:
            mock_get_enrollments.side_effect = ValidationError()
            task = self.spawn_task()
            task.wait()
        self.assert_failed("Invalid enrollment data from LMS")

    def test_invalid_format(self):
        with mock.patch(self.mock_base + self.mocked_get_enrollments_method) as mock_get_enrollments:
            mock_get_enrollments.return_value = self.enrollment_data
            exception_raised = False
            try:
                task = self.spawn_task(file_format='invalid-format')
                task.wait()
            except ValueError as e:
                self.assertIn('Invalid file_format', str(e))
                exception_raised = True
        self.assertTrue(exception_raised)


class ListProgramEnrollmentTaskTests(ListEnrollmentTaskTestMixin, TestCase):
    """ Tests for task error behavior. """
    enrollment_statuses = (
        PROGRAM_ENROLLMENT_ENROLLED,
        PROGRAM_ENROLLMENT_PENDING,
    )
    mocked_get_enrollments_method = 'get_program_enrollments'

    def spawn_task(self, program_key=None, **kwargs):
        return tasks.list_program_enrollments.apply_async(
            (
                self.job_id,
                self.user.id,
                kwargs.get('file_format', 'json'),
                program_key or self.program.key,
            ),
            task_id=self.job_id
        )


class ListCourseRunEnrollmentTaskTests(ListEnrollmentTaskTestMixin, TestCase):
    """ Tests for task error behavior. """
    enrollment_statuses = (
        COURSE_ENROLLMENT_ACTIVE,
        COURSE_ENROLLMENT_INACTIVE,
    )
    mocked_get_enrollments_method = 'get_course_run_enrollments'
    internal_course_key = 'course-1'
    external_course_key = 'external_course_key'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for enrollment in cls.enrollment_data:
            enrollment['course_id'] = cls.external_course_key

    def spawn_task(self, program_key=None, **kwargs):
        return tasks.list_course_run_enrollments.apply_async(
            (
                self.job_id,
                self.user.id,
                kwargs.get('file_format', 'json'),
                program_key or self.program.key,
                self.internal_course_key,
                self.external_course_key,
            ),
            task_id=self.job_id
        )


class ListAllCourseRunEnrollmentTaskTests(ListEnrollmentTaskTestMixin, TestCase):
    """ Tests for task error behavior. """
    enrollment_statuses = (
        COURSE_ENROLLMENT_ACTIVE,
        COURSE_ENROLLMENT_INACTIVE,
    )
    mocked_get_enrollments_method = 'get_course_run_enrollments'
    course_key = 'course-1'
    external_course_key = 'external_course_key'
    default_course_run = {'key': 'course-key', 'external_key': 'external-key'}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for enrollment in cls.enrollment_data:
            enrollment['course_id'] = cls.external_course_key

    def setUp(self):
        super().setUp()
        program_patcher = mock.patch.object(DiscoveryProgram, 'get')
        self.mocked_discovery_program = program_patcher.start()
        self.mocked_discovery_program.return_value = DiscoveryProgram(
            course_runs=[
                DiscoveryCourseRun(
                    key='course-key',
                    external_key='external-key',
                    title='title',
                    marketing_url='www',
                )
            ]
        )
        self.addCleanup(program_patcher.stop)

    def spawn_task(self, program_key=None, **kwargs):
        return tasks.list_all_course_run_enrollments.apply_async(
            (
                self.job_id,
                self.user.id,
                kwargs.get('file_format', 'json'),
                program_key or self.program.key,
            ),
            task_id=self.job_id
        )


class WriteEnrollmentTaskTestMixin(BaseEnrollmentTaskTestMixin):
    """
    Tests common for both program and course-run enrollment writing tasks.
    """
    json_filepath = "testfile.csv"
    mock_function = None  # Override in subclass
    expected_fieldnames = None  # Override in subclass

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

    def tearDown(self):
        super().tearDown()
        uploads_filestore.delete(self.json_filepath)

    def mock_write_enrollments(self, any_successes, any_failures):
        """
        Creates a mock function that returns results normally returned
        by an enrollment-writing function.
        """
        raise NotImplementedError()  # pragma: no cover

    def test_empty_list_file(self):
        uploads_filestore.store(self.json_filepath, "[]")
        with mock.patch(
                self.mock_base + self.mock_function,
                new=self.mock_write_enrollments(False, False),
        ):
            self.spawn_task().wait()
        self.assert_succeeded(','.join(self.expected_fieldnames) + "\r\n", "204")

    def test_no_such_file(self):
        self.spawn_task().wait()
        self.assert_failed(
            "Enrollment file for program_key={} not found at {}".format(
                self.program.key, self.json_filepath
            )
        )

    def test_file_not_json(self):
        uploads_filestore.store(self.json_filepath, "this is not valid json")
        self.spawn_task().wait()
        self.assert_failed(
            "Enrollment file for program_key={} at {} is not valid JSON".format(
                self.program.key, self.json_filepath
            )
        )


@ddt.ddt
class WriteProgramEnrollmentTaskTests(WriteEnrollmentTaskTestMixin, TestCase):
    """
    Tests for write_program_enrollments task.
    """
    mock_function = 'write_program_enrollments'
    expected_fieldnames = ('student_key', 'status')

    def spawn_task(self, program_key=None, **kwargs):
        return tasks.write_program_enrollments.apply_async(
            (
                self.job_id,
                self.user.id,
                self.json_filepath,
                program_key or self.program.key,
            ),
            task_id=self.job_id
        )

    def mock_write_enrollments(self, any_successes, any_failures):
        """
        Create mock for data.write_program_enrollments

        Mock will return `any_successes`, `any_failures`, and `enrollments`
        echoed back as a dictionary.
        """
        def inner(_method, program_uuid, enrollments):
            """ Mock for data.write_program_enrollments. """
            self.assertIsInstance(program_uuid, UUID)
            results = OrderedDict([
                (enrollment['student_key'], enrollment['status'])
                for enrollment in enrollments
            ])
            return any_successes, any_failures, results
        return inner

    @ddt.data(
        (True, False, "200"),
        (True, True, "207"),
        (False, True, "422"),
    )
    @ddt.unpack
    def test_success(self, any_successes, any_failures, expected_code_str):
        enrolls = [
            {'student_key': 'john', 'status': 'x'},
            {'student_key': 'bob', 'status': 'y'},
            {'student_key': 'serena', 'status': 'z'},
        ]
        uploads_filestore.store(self.json_filepath, json.dumps(enrolls))
        with mock.patch(
                self.mock_base + self.mock_function,
                new=self.mock_write_enrollments(any_successes, any_failures),
        ):
            self.spawn_task().wait()
        self.assert_succeeded(
            "student_key,status\r\n"
            "john,x\r\n"
            "bob,y\r\n"
            "serena,z\r\n",
            expected_code_str,
        )


@ddt.ddt
class WriteCourseRunEnrollmentTaskTests(WriteEnrollmentTaskTestMixin, TestCase):
    """
    Tests for write_course_run_enrollments task.
    """
    mock_function = 'write_course_run_enrollments'
    expected_fieldnames = ('course_id', 'student_key', 'status')

    def setUp(self):
        super().setUp()
        self.patcher = mock.patch.object(Program, 'discovery_program')
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def spawn_task(self, program_key=None, **kwargs):
        return tasks.write_course_run_enrollments.apply_async(
            (
                self.job_id,
                self.user.id,
                self.json_filepath,
                program_key or self.program.key,
            ),
            task_id=self.job_id
        )

    def mock_write_enrollments(self, any_successes, any_failures):
        """
        Create mock for data.write_course_run_enrollments.

        Mock will return `any_successes`, `any_failures`, and `enrollments`
        echoed back as a dictionary.
        """
        # pylint: disable=unused-argument
        def inner(_method, program_uuid, course_key, enrollments):
            """ Mock for data.write_course_run_enrollments. """
            self.assertIsInstance(program_uuid, UUID)
            results = OrderedDict([
                (enrollment['student_key'], enrollment['status'])
                for enrollment in enrollments
            ])
            return any_successes, any_failures, results
        return inner

    @ddt.data(
        (True, False, "200"),
        (True, True, "207"),
        (False, True, "422"),
    )
    @ddt.unpack
    def test_success_status(self, any_successes, any_failures, expected_code_str):
        self.program.discovery_program.get_course_key.side_effect = lambda x: x + '-internal'
        enrolls = [
            {'student_key': 'john', 'status': 'x', 'course_id': 'course-1'},
            {'student_key': 'bob', 'status': 'y', 'course_id': 'course-1'},
            {'student_key': 'serena', 'status': 'z', 'course_id': 'course-2'},
        ]
        uploads_filestore.store(self.json_filepath, json.dumps(enrolls))
        with mock.patch(
                self.mock_base + self.mock_function,
                new=self.mock_write_enrollments(any_successes, any_failures),
        ):
            self.spawn_task().wait()
        self.assert_succeeded(
            "course_id,student_key,status\r\n"
            "course-1,john,x\r\n"
            "course-1,bob,y\r\n"
            "course-2,serena,z\r\n",
            expected_code_str,
        )

    def test_success_invalid_course_id(self):
        self.program.discovery_program.get_course_key.side_effect = {'course-1': 'course-1-internal'}.get
        enrolls = [
            {'student_key': 'john', 'status': 'x', 'course_id': 'course-1'},
            {'student_key': 'bob', 'status': 'y', 'course_id': 'course-1'},
            {'student_key': 'serena', 'status': 'z', 'course_id': 'invalid-course'},
        ]
        uploads_filestore.store(self.json_filepath, json.dumps(enrolls))
        with mock.patch(
                self.mock_base + self.mock_function,
                new=self.mock_write_enrollments(True, False),
        ):
            self.spawn_task().wait()
        self.assert_succeeded(
            "course_id,student_key,status\r\n"
            "course-1,john,x\r\n"
            "course-1,bob,y\r\n"
            "invalid-course,serena,course-not-found\r\n",
            "207",
        )
