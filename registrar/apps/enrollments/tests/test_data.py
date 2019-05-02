"""
Tests for enrollments/data.py

Much of data.py is not tested in this file because it is already implicitly
tested by our view tests.
"""
import uuid
from posixpath import join as urljoin
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from requests.exceptions import HTTPError
import responses
from rest_framework.exceptions import ValidationError

from registrar.apps.core.tests.utils import mock_oauth_login
from registrar.apps.enrollments.data import get_program_enrollments, get_discovery_program


class GetProgramEnrollmentsTestCase(TestCase):
    """ Tests for data.get_program_enrollments """

    uuid = '7fbefaa4-c0e8-431b-af69-8d3ddde543a2'
    url = '{}/api/program_enrollments/v1/programs/{}/enrollments'.format(
        settings.LMS_BASE_URL, uuid
    )

    good_data_1 = [
        {
            'student_key': 'abcd',
            'account_exists': True,
            'status': 'enrolled',
        },
        {
            'student_key': 'efgh',
            'account_exists': False,
            'status': 'canceled',
        },
    ]
    good_data_2 = [
        {
            'student_key': 'ijkl',
            'account_exists': False,
            'status': 'pending',
        },
        {
            'student_key': 'mnop',
            'account_exists': True,
            'status': 'suspended',
        },
    ]
    bad_data = [
        {
            'student_key': 'qrst',
            'account_exists': True,
            'status': 'this-is-not-a-status',
        },
    ]

    @mock_oauth_login
    @responses.activate
    def test_get_program_enrollments(self):
        responses.add(
            responses.GET,
            self.url,
            status=200,
            json={'next': self.url + "?cursor=xxx", 'results': self.good_data_1},
        )
        responses.add(
            responses.GET,
            self.url,
            status=200,
            json={'next': None, 'results': self.good_data_2},
        )
        enrolls = get_program_enrollments(self.uuid)
        self.assertCountEqual(enrolls, self.good_data_1 + self.good_data_2)

    @mock_oauth_login
    @responses.activate
    def test_get_program_enrollments_bad_data(self):
        responses.add(
            responses.GET,
            self.url,
            status=200,
            json={'next': None, 'results': self.good_data_1 + self.bad_data},
        )
        with self.assertRaises(ValidationError):
            get_program_enrollments(self.uuid)

    @mock_oauth_login
    @responses.activate
    def test_get_program_enrollments_500(self):
        responses.add(responses.GET, self.url, status=500)
        with self.assertRaises(HTTPError):
            get_program_enrollments(self.uuid)


class GetDiscoveryProgramTestCase(TestCase):
    """ Test get_discovery_program function """

    program_uuid = uuid.uuid4()
    discovery_url = urljoin(settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/').format(program_uuid)
    programs_response = {
        'curricula': [{
            'uuid': uuid.uuid4().hex[0:10],
            'is_active': True,
            'courses': [
                {
                    'course_runs': [
                        {
                            'key': '0001',
                            'uuid': '0000-0001',
                            'title': 'Test Course 1',
                            'marketing_url': 'https://stem-institute.edx.org/masters-in-cs/test-course-1',
                        },
                    ],
                }
            ],
        }],
    }

    def setUp(self):
        super(GetDiscoveryProgramTestCase, self).setUp()
        cache.clear()

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
        response = get_discovery_program(self.program_uuid)
        self.assertEqual(response, self.programs_response)
        self.assertEqual(len(responses.calls), 2)

        # this should return the same object from cache
        response = get_discovery_program(self.program_uuid)
        self.assertEqual(response, self.programs_response)
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
            get_discovery_program(self.program_uuid)

        responses.replace(
            responses.GET,
            self.discovery_url,
            json=self.programs_response,
            status=200
        )
        response = get_discovery_program(self.program_uuid)
        self.assertEqual(response, self.programs_response)
