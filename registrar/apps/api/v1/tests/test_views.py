""" Tests for API views. """

import json
from posixpath import join as urljoin

import ddt
import mock
import responses
from django.conf import settings
from rest_framework.test import APITestCase

from registrar.apps.api.tests.mixins import JwtMixin
from registrar.apps.core.tests.factories import (
    UserFactory,
    USER_PASSWORD,
    StaffUserFactory,
)
from registrar.apps.core.models import Organization
from registrar.apps.core.tests.factories import OrganizationFactory
from registrar.apps.enrollments.tests.factories import (  # pylint: disable=no-name-in-module
    ProgramFactory,
)


# pylint: disable=unused-argument

def mock_oauth_login(fn):
    """
    Mock request to authenticate registrar as a backend client
    """
    # pylint: disable=missing-docstring
    def inner(self, *args, **kwargs):
        responses.add(
            responses.POST,
            settings.LMS_BASE_URL + '/oauth2/access_token',
            body=json.dumps({'access_token': 'abcd', 'expires_in': 60}),
            status=200
        )
        fn(self, *args, **kwargs)
    return inner


def _mock_organization_check_access(org, user, access_level):
    """
    Mock of organization access checking.

    Return True iff username is {organization_name}-admin.
    """
    return user.is_staff or user.username == '{0}-admin'.format(org.key)


class RegistrarAPITestCase(APITestCase, JwtMixin):
    """ Base for tests of the Registrar API """

    API_ROOT = '/api/v1/'

    def setUp(self):
        super(RegistrarAPITestCase, self).setUp()
        self.org1 = OrganizationFactory(name='STEM Institute')
        self.program1a = ProgramFactory(
            managing_organization=self.org1,
            title="Master's in CS"
        )
        self.program1b = ProgramFactory(
            managing_organization=self.org1,
            title="Master's in ME"
        )
        self.org2 = OrganizationFactory(name='Humanities College')
        self.program2a = ProgramFactory(
            managing_organization=self.org2,
            title="Master's in Philosophy"
        )
        self.program2b = ProgramFactory(
            managing_organization=self.org2,
            title="Master's in English"
        )
        self.staff = StaffUserFactory(username='edx-admin')
        self.user1 = UserFactory(username='stem-institute-admin')
        self.user2 = UserFactory(username='humanities-college-admin')

    def login(self, user):
        return self.client.login(username=user.username, password=USER_PASSWORD)

    def get(self, path, user):
        return self.client.get(
            self.API_ROOT + path,
            follow=True,
            HTTP_AUTHORIZATION=self.generate_jwt_header(user, admin=user.is_staff)
        )

    def mock_api_response(self, url, response_data):
        responses.add(
            responses.GET,
            url,
            body=json.dumps(response_data),
            content_type='application/json',
            status=200
        )


@ddt.ddt
@mock.patch.object(Organization, 'check_access', _mock_organization_check_access)
class ProgramReadOnlyViewSetTests(RegistrarAPITestCase):
    """ Tests for the /api/v1/programs endpoint """

    def test_staff_can_get_all_programs(self):
        response = self.get('programs', self.staff)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def test_non_staff_cannot_get_all_programs(self):
        response = self.get('programs', self.user1)
        self.assertEqual(response.status_code, 403)

    @ddt.data(True, False)
    def test_admin_can_list_programs(self, is_staff):
        user = self.staff if is_staff else self.user1
        response = self.get('programs?org=stem-institute', user)
        self.assertEqual(response.status_code, 200)
        response_programs = sorted(response.data, key=lambda p: p['program_key'])
        self.assertListEqual(
            response_programs,
            [
                {
                    'program_title': "Master's in CS",
                    'program_key': 'masters-in-cs',
                    'program_url':
                        'https://stem-institute.edx.org/masters-in-cs',
                },
                {
                    'program_title': "Master's in ME",
                    'program_key': 'masters-in-me',
                    'program_url':
                        'https://stem-institute.edx.org/masters-in-me',
                },
            ]
        )

    def test_non_admin_cannot_list_programs(self):
        response = self.get('programs?org=stem-institute', self.user2)
        self.assertEqual(response.status_code, 403)

    def test_org_not_found(self):
        response = self.get('programs?org=business-univ', self.user1)
        self.assertEqual(response.status_code, 404)

    @ddt.data(True, False)
    def test_admin_can_get_program(self, is_staff):
        user = self.staff if is_staff else self.user2
        response = self.get('programs/masters-in-english', user)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data,
            {
                'program_title': "Master's in English",
                'program_key': 'masters-in-english',
                'program_url':
                    'https://humanities-college.edx.org/masters-in-english',
            },
        )

    def test_non_admin_cannot_get_program(self):
        response = self.get('programs/masters-in-english', self.user1)
        self.assertEqual(response.status_code, 403)

    def test_program_not_found(self):
        response = self.get('programs/masters-in-polysci', self.user1)
        self.assertEqual(response.status_code, 404)

    @mock_oauth_login
    @responses.activate
    def test_admin_can_get_program_courses(self):
        user = self.staff

        program_data = {
            'curricula': [{
                'courses': [{
                    'course_runs': [
                        {
                            'key': '0001',
                            'uuid': '123456',
                            'title': 'Test Course 1',
                            'marketing_url': 'https://humanities-college.edx.org/masters-in-english/test-course-1',
                        }
                    ],
                }],
            }],
        }

        program_uuid = self.program2b.discovery_uuid
        discovery_url = urljoin(settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/').format(program_uuid)
        self.mock_api_response(discovery_url, program_data)

        response = self.get('programs/masters-in-english/courses', user)

        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data,
            [{
                'course_id': '0001',
                'course_title': 'Test Course 1',
                'course_url': 'https://humanities-college.edx.org/masters-in-english/test-course-1',
            }],
        )

    def test_get_program_courses_unauthorized(self):
        response = self.get('programs/masters-in-cs/courses', self.user2)
        self.assertEqual(response.status_code, 403)

    @mock_oauth_login
    @responses.activate
    def test_get_program_with_no_course_runs(self):
        user = self.user2

        program_data = {
            'curricula': [{
                'courses': [{
                    'course_runs': []
                }]
            }]
        }

        program_uuid = self.program2b.discovery_uuid
        discovery_url = urljoin(settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/').format(program_uuid)
        self.mock_api_response(discovery_url, program_data)

        response = self.get('programs/masters-in-english/courses', user)

        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data, [])

    @mock_oauth_login
    @responses.activate
    def test_get_program_with_multiple_courses(self):
        user = self.user1

        program_data = {
            'curricula': [{
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
                    },
                    {
                        'course_runs': [
                            {
                                'key': '0002a',
                                'uuid': '0000-0002a',
                                'title': 'Test Course 2',
                                'marketing_url': 'https://stem-institute.edx.org/masters-in-cs/test-course-2a',
                            },
                            {
                                'key': '0002b',
                                'uuid': '0000-0002b',
                                'title': 'Test Course 2',
                                'marketing_url': 'https://stem-institute.edx.org/masters-in-cs/test-course-2b',
                            },
                        ],
                    }
                ],
            }],
        }

        program_uuid = self.program1a.discovery_uuid
        discovery_url = urljoin(settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/').format(program_uuid)
        self.mock_api_response(discovery_url, program_data)

        response = self.get('programs/masters-in-cs/courses', user)

        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data,
            [
                {
                    'course_id': '0001',
                    'course_title': 'Test Course 1',
                    'course_url': 'https://stem-institute.edx.org/masters-in-cs/test-course-1',
                },
                {
                    'course_id': '0002a',
                    'course_title': 'Test Course 2',
                    'course_url': 'https://stem-institute.edx.org/masters-in-cs/test-course-2a',
                },
                {
                    'course_id': '0002b',
                    'course_title': 'Test Course 2',
                    'course_url': 'https://stem-institute.edx.org/masters-in-cs/test-course-2b',
                }
            ],
        )
