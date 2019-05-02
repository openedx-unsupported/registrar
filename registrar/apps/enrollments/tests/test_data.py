"""
Tests for enrollments/data.py

Much of data.py is not tested in this file because it is already implicitly
tested by our view tests.
"""
from datetime import datetime
from posixpath import join as urljoin
import uuid

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
import mock
from requests.exceptions import HTTPError
import responses
from rest_framework.exceptions import ValidationError

from registrar.apps.core.tests.utils import mock_oauth_login
from registrar.apps.enrollments.data import (
    DiscoveryCourseRun,
    DiscoveryProgram,
    get_course_run_enrollments,
    get_program_enrollments,
)


class GetEnrollmentsTestMixin(object):
    """ Common tests for enrollment-getting functions """

    lms_url = None  # Override in subclass
    status_choices = None  # Override in subclass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.good_data_1 = [
            {
                'student_key': 'abcd',
                'account_exists': True,
                'status': cls.status(0),
            },
            {
                'student_key': 'efgh',
                'account_exists': False,
                'status': cls.status(4),
            },
        ]
        cls.good_data_2 = [
            {
                'student_key': 'ijkl',
                'account_exists': False,
                'status': cls.status(2),
            },
            {
                'student_key': 'mnop',
                'account_exists': True,
                'status': cls.status(3),
            },
        ]
        cls.bad_data = [
            {
                'student_key': 'qrst',
                'account_exists': True,
                'status': 'this-is-not-a-status',
            },
        ]

    @classmethod
    def status(cls, i):
        return cls.status_choices[i % len(cls.status_choices)]

    def get_enrollments(self):
        """ Override in subclass """
        raise NotImplementedError

    @mock_oauth_login
    @responses.activate
    def test_get_enrollments(self):
        responses.add(
            responses.GET,
            self.lms_url,
            status=200,
            json={'next': self.lms_url + "?cursor=xxx", 'results': self.good_data_1},
        )
        responses.add(
            responses.GET,
            self.lms_url,
            status=200,
            json={'next': None, 'results': self.good_data_2},
        )
        enrolls = self.get_enrollments()
        self.assertCountEqual(enrolls, self.good_data_1 + self.good_data_2)

    @mock_oauth_login
    @responses.activate
    def test_get_enrollments_bad_data(self):
        responses.add(
            responses.GET,
            self.lms_url,
            status=200,
            json={'next': None, 'results': self.good_data_1 + self.bad_data},
        )
        with self.assertRaises(ValidationError):
            self.get_enrollments()

    @mock_oauth_login
    @responses.activate
    def test_get_enrollments_500(self):
        responses.add(responses.GET, self.lms_url, status=500)
        with self.assertRaises(HTTPError):
            self.get_enrollments()


class GetProgramEnrollmentsTestCase(GetEnrollmentsTestMixin, TestCase):
    """ Tests for data.get_program_enrollments """

    program_uuid = '7fbefaa4-c0e8-431b-af69-8d3ddde543a2'
    lms_url = '{}/api/program_enrollments/v1/programs/{}/enrollments'.format(
        settings.LMS_BASE_URL, program_uuid
    )
    status_choices = ['enrolled', 'pending', 'suspended', 'canceled']

    def get_enrollments(self):
        return get_program_enrollments(self.program_uuid)


class GetCourseRunEnrollmentsTestCase(GetEnrollmentsTestMixin, TestCase):
    """ Tests for data.get_course_run_enrollments """

    program_uuid = 'ce5ea4c8-666e-429c-9d2c-a5698f86f6fb'
    course_id = 'course-v1:ABCx+Subject-101+Term'
    lms_url = '{}/api/program_enrollments/v1/programs/{}/courses/{}/enrollments'.format(
        settings.LMS_BASE_URL, program_uuid, course_id
    )
    status_choices = ['active', 'inactive']

    def get_enrollments(self):
        return get_course_run_enrollments(self.program_uuid, self.course_id)


class GetDiscoveryProgramTestCase(TestCase):
    """ Test get_discovery_program function """

    program_uuid = str(uuid.uuid4())
    curriculum_uuid = str(uuid.uuid4())
    discovery_url = urljoin(settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/').format(program_uuid)
    course_run_1 = {
        'key': '0001',
        'uuid': '0000-0001',
        'title': 'Test Course 1',
        'marketing_url': 'https://stem-institute.edx.org/masters-in-cs/test-course-1',
    }
    programs_response = {
        'curricula': [{
            'uuid': curriculum_uuid,
            'is_active': True,
            'courses': [{'course_runs': [course_run_1]}],
        }],
    }
    expected_program = DiscoveryProgram(
        version=0,
        loaded=datetime.now(),
        uuid=program_uuid,
        active_curriculum_uuid=curriculum_uuid,
        course_runs=[
            DiscoveryCourseRun(
                course_run_1['key'],
                course_run_1['title'],
                course_run_1['marketing_url'],
            ),
        ],
    )

    def setUp(self):
        super().setUp()
        cache.clear()

    def assert_discovery_programs_equal(self, this_program, that_program):
        """ Asserts DiscoveryProgram equality, ignoring `loaded` field. """
        self.assertEqual(this_program.version, 1)
        self.assertEqual(this_program.uuid, that_program.uuid)
        self.assertEqual(this_program.active_curriculum_uuid, that_program.active_curriculum_uuid)
        self.assertEqual(this_program.course_runs, that_program.course_runs)

    @mock_oauth_login
    @responses.activate
    def test_get_discovery_program_success(self):
        """
        Verify initial call returns data from the discovery service and additional function
        calls return from cache.

        Note: TWO calls are initially made to discovery in order to obtain an auth token and then
        request data.
        """
        responses.add(
            responses.GET,
            self.discovery_url,
            json=self.programs_response,
            status=200
        )
        loaded_program = DiscoveryProgram.get(self.program_uuid)
        self.assert_discovery_programs_equal(loaded_program, self.expected_program)
        self.assertEqual(len(responses.calls), 2)

        # this should return the same object from cache
        loaded_program = DiscoveryProgram.get(self.program_uuid)
        self.assert_discovery_programs_equal(loaded_program, self.expected_program)
        self.assertEqual(len(responses.calls), 2)

    @mock_oauth_login
    @responses.activate
    def test_get_discovery_program_error(self):
        """
        Verify if an error occurs when requesting discovery data an exception is
        thown and the cache is not polluted.
        """
        responses.add(
            responses.GET,
            self.discovery_url,
            json={'message': 'everything is broken'},
            status=500
        )

        with self.assertRaises(HTTPError):
            DiscoveryProgram.get(self.program_uuid)

        responses.replace(
            responses.GET,
            self.discovery_url,
            json=self.programs_response,
            status=200
        )
        loaded_program = DiscoveryProgram.get(self.program_uuid)
        self.assert_discovery_programs_equal(loaded_program, self.expected_program)

    @mock_oauth_login
    @responses.activate
    def test_get_discovery_cache_versioning(self):
        """
        Verify that bumping the version of the cache invalidates old
        entries.
        """
        responses.add(
            responses.GET,
            self.discovery_url,
            json=self.programs_response,
            status=200
        )
        DiscoveryProgram.get(self.program_uuid)
        self.assertEqual(len(responses.calls), 2)
        bumped_version = DiscoveryProgram.class_version + 1
        with mock.patch.object(DiscoveryProgram, 'class_version', bumped_version):
            DiscoveryProgram.get(self.program_uuid)
        self.assertEqual(len(responses.calls), 4)
