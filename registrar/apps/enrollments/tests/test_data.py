"""
Tests for enrollments/data.py

Much of data.py is not tested in this file because it is already implicitly
tested by our view tests.
"""

import json
import uuid
from datetime import datetime
from posixpath import join as urljoin

import ddt
import mock
import responses
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from requests.exceptions import HTTPError
from rest_framework.exceptions import ValidationError

from registrar.apps.core.tests.utils import mock_oauth_login
from registrar.apps.enrollments.data import (
    DISCOVERY_PROGRAM_API_TPL,
    LMS_PROGRAM_COURSE_ENROLLMENTS_API_TPL,
    LMS_PROGRAM_ENROLLMENTS_API_TPL,
    DiscoveryCourseRun,
    DiscoveryProgram,
    get_course_run_enrollments,
    get_program_enrollments,
    write_program_course_enrollments,
    write_program_enrollments,
)


class GetEnrollmentsTestMixin(object):
    """ Common tests for enrollment-getting functions """

    lms_url = None  # Override in subclass
    status_choices = None  # Override in subclass
    curriculum_uuid_in_input = False  # Override in subclass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.good_input_1 = [
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
        cls.good_input_2 = [
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
        cls.bad_input = [
            {
                'student_key': 'qrst',
                'account_exists': True,
                'status': 'this-is-not-a-status',
            },
        ]
        cls.good_output = [
            enrollment.copy()
            for enrollment in cls.good_input_1 + cls.good_input_2
        ]
        all_input = cls.good_input_1 + cls.good_input_2 + cls.bad_input
        if cls.curriculum_uuid_in_input:
            for enrollment in all_input:
                enrollment['curriculum_uuid'] = str(uuid.uuid4())

    @classmethod
    def status(cls, i):
        return cls.status_choices[i % len(cls.status_choices)]

    def get_enrollments(self):
        """ Override in subclass """
        raise NotImplementedError  # pragma: no cover

    @mock_oauth_login
    @responses.activate
    def test_get_enrollments(self):
        responses.add(
            responses.GET,
            self.lms_url,
            status=200,
            json={'next': self.lms_url + "?cursor=xxx", 'results': self.good_input_1},
        )
        responses.add(
            responses.GET,
            self.lms_url,
            status=200,
            json={'next': None, 'results': self.good_input_2},
        )
        enrolls = self.get_enrollments()
        self.assertCountEqual(enrolls, self.good_output)

    @mock_oauth_login
    @responses.activate
    def test_get_enrollments_bad_input(self):
        responses.add(
            responses.GET,
            self.lms_url,
            status=200,
            json={'next': None, 'results': self.bad_input},
        )
        with self.assertRaises(ValidationError):
            self.get_enrollments()

    @mock_oauth_login
    @responses.activate
    def test_get_enrollments_500(self):
        responses.add(responses.GET, self.lms_url, status=500)
        with self.assertRaises(HTTPError):
            self.get_enrollments()

    @mock_oauth_login
    @responses.activate
    def test_get_enrollments_404(self):
        responses.add(responses.GET, self.lms_url, status=404)
        with self.assertRaisesRegex(HTTPError, '404 Client Error: Not Found'):
            self.get_enrollments()


class GetProgramEnrollmentsTestCase(GetEnrollmentsTestMixin, TestCase):
    """ Tests for data.get_program_enrollments """

    program_uuid = '7fbefaa4-c0e8-431b-af69-8d3ddde543a2'
    lms_url = urljoin(settings.LMS_BASE_URL, LMS_PROGRAM_ENROLLMENTS_API_TPL.format(program_uuid))
    status_choices = ['enrolled', 'pending', 'suspended', 'canceled']
    curriculum_uuid_in_input = True

    def get_enrollments(self):
        return get_program_enrollments(self.program_uuid)


class GetCourseRunEnrollmentsTestCase(GetEnrollmentsTestMixin, TestCase):
    """ Tests for data.get_course_run_enrollments """

    program_uuid = 'ce5ea4c8-666e-429c-9d2c-a5698f86f6fb'
    course_id = 'course-v1:ABCx+Subject-101+Term'
    lms_url = urljoin(settings.LMS_BASE_URL, LMS_PROGRAM_COURSE_ENROLLMENTS_API_TPL.format(program_uuid, course_id))
    status_choices = ['active', 'inactive']
    curriculum_uuid_in_input = False

    def get_enrollments(self):
        return get_course_run_enrollments(self.program_uuid, self.course_id)


class WriteEnrollmentsTestMixin(object):
    """
    Common tests for program and course enrollment writing functionality
    """
    program_key = '99999999-aaaa-bbbb-cccc-123412341234'
    course_key = 'course-v1:edX+DemoX+Demo_Course'
    ok_response = {
        'tom': 'active',
        'lucy': 'active',
        'craig': 'inactive',
        'sheryl': 'inactive',
    }
    unprocessable_response = {
        'ted': 'duplicate',
        'bill': 'conflict',
    }

    def write_enrollments(self, enrollments):
        """ Overridden in child classes """
        pass  # pragma: no cover

    @mock_oauth_login
    @responses.activate
    def test_create_enrollments_happy_path(self):
        responses.add(
            responses.POST,
            self.url,
            status=200,
            json=self.ok_response,
        )
        enrollments = [
            {'student_key': 'tom', 'status': 'active'},
            {'student_key': 'lucy', 'status': 'active'},
            {'student_key': 'craig', 'status': 'inactive'},
            {'student_key': 'sheryl', 'status': 'inactive'},
        ]

        create_response = self.write_enrollments(enrollments)

        # there are two requests - 1 for the oauth token and then 1 to create enrollments
        mock_request = responses.calls[1].request
        assert 2 == len(responses.calls)
        assert 200 == create_response.status_code
        assert self.ok_response == create_response.json()
        assert self.url == mock_request.url
        assert enrollments == json.loads(mock_request.body.decode())

    @mock_oauth_login
    @responses.activate
    def test_create_enrollments_unprocessable(self):
        responses.add(
            responses.POST,
            self.url,
            status=422,
            json=self.unprocessable_response,
        )
        enrollments = [
            {'student_key': 'ted', 'status': 'duplicate'},
            {'student_key': 'bill', 'status': 'conflict'},
        ]

        create_response = self.write_enrollments(enrollments)

        # there are two requests - 1 for the oauth token and then 1 to create enrollments
        mock_request = responses.calls[1].request
        assert 2 == len(responses.calls)
        assert 422 == create_response.status_code
        assert self.unprocessable_response == create_response.json()
        assert self.url == mock_request.url
        assert enrollments == json.loads(mock_request.body.decode())

    @mock_oauth_login
    @responses.activate
    def test_create_enrollments_404(self):
        responses.add(responses.POST, self.url, status=404)
        enrollments = [{'student_key': 'ted', 'status': 'active'}]
        result = self.write_enrollments(enrollments)
        self.assertEqual(404, result.status_code)


class WriteProgramEnrollmentsTests(WriteEnrollmentsTestMixin, TestCase):
    """
    Tests for the method to write program enrollment data
    to the LMS API.
    """
    @property
    def url(self):
        return urljoin(settings.LMS_BASE_URL, LMS_PROGRAM_ENROLLMENTS_API_TPL.format(self.program_key))

    def write_enrollments(self, enrollments):
        return write_program_enrollments(self.program_key, enrollments)


class WriteProgramCourseEnrollmentsTests(WriteEnrollmentsTestMixin, TestCase):
    """
    Tests for the method to write program/course enrollment data
    to the LMS API.
    """
    @property
    def url(self):
        return urljoin(
            settings.LMS_BASE_URL,
            LMS_PROGRAM_COURSE_ENROLLMENTS_API_TPL.format(
                self.program_key,
                self.course_key
            )
        )

    def write_enrollments(self, enrollments):
        return write_program_course_enrollments(self.program_key, self.course_key, enrollments)


class GetDiscoveryProgramTestCase(TestCase):
    """ Test get_discovery_program function """
    program_uuid = str(uuid.uuid4())
    curriculum_uuid = str(uuid.uuid4())
    discovery_url = urljoin(settings.DISCOVERY_BASE_URL, DISCOVERY_PROGRAM_API_TPL.format(program_uuid))
    course_run_1 = {
        'key': '0001',
        'uuid': '0000-0001',
        'title': 'Test Course 1',
        'external_key': 'testorg-course-101',
        'marketing_url': 'https://stem-institute.edx.org/masters-in-cs/test-course-1',
    }
    program_title = "Master's in CS"
    program_url = 'https://stem-institute.edx.org/masters-in-cs'
    programs_response = {
        'title': program_title,
        'marketing_url': program_url,
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
        title=program_title,
        url=program_url,
        active_curriculum_uuid=curriculum_uuid,
        course_runs=[
            DiscoveryCourseRun(
                course_run_1['key'],
                course_run_1['external_key'],
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
        self.assertEqual(this_program.title, that_program.title)
        self.assertEqual(this_program.url, that_program.url)
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


@ddt.ddt
class DiscoveryProgramTests(TestCase):
    """ Tests for DiscoveryProgram methods """

    def setUp(self):
        super().setUp()
        program_uuid = str(uuid.uuid4())
        curriculum_uuid = str(uuid.uuid4())
        program_title = "Master's in CS"
        program_url = 'https://stem-institute.edx.org/masters-in-cs'
        self.program = DiscoveryProgram(
            version=0,
            loaded=datetime.now(),
            uuid=program_uuid,
            title=program_title,
            url=program_url,
            active_curriculum_uuid=curriculum_uuid,
            course_runs=[
                self.make_course_run(i) for i in range(4)
            ],
        )

    def make_course_run(self, counter):
        """
        Helper for making DiscoveryCourseRuns
        """
        key = 'course-{}'.format(counter)
        external_key = 'external-key-course-{}'.format(counter)
        title = 'Course {} Title'.format(counter)
        url = 'www.courserun.url/{}/'.format(counter)
        return DiscoveryCourseRun(key, external_key, title, url)

    @ddt.data('key', 'external_key')
    def test_get_key(self, attr):
        for course_run in self.program.course_runs:
            test_key = getattr(course_run, attr)
            self.assertEqual(
                self.program.get_course_key(test_key),
                course_run.key
            )

    def test_get_key_not_found(self):
        for i in [10, 101, 111, 123]:
            not_in_program_run = self.make_course_run(i)
            self.assertIsNone(self.program.get_course_key(not_in_program_run.key))
            self.assertIsNone(self.program.get_course_key(not_in_program_run.external_key))

    @ddt.data('key', 'external_key')
    def test_get_external_key(self, attr):
        for course_run in self.program.course_runs:
            test_key = getattr(course_run, attr)
            self.assertEqual(
                self.program.get_external_course_key(test_key),
                course_run.external_key
            )

    def test_get_external_key_not_found(self):
        for i in [10, 101, 111, 123]:
            not_in_program_run = self.make_course_run(i)
            self.assertIsNone(self.program.get_external_course_key(not_in_program_run.key))
