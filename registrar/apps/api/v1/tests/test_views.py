""" Tests for API views. """

import json
from posixpath import join as urljoin

import ddt
from guardian.shortcuts import assign_perm
import responses
from django.conf import settings
from rest_framework.test import APITestCase

from registrar.apps.api.tests.mixins import RequestMixin
from registrar.apps.core import permissions as perms
from registrar.apps.core.tests.factories import (
    OrganizationFactory,
    OrganizationGroupFactory,
    UserFactory,
)
from registrar.apps.enrollments.tests.factories import ProgramFactory


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


class RegistrarAPITestCase(APITestCase, RequestMixin):
    """ Base for tests of the Registrar API """

    api_root = '/api/v1/'

    def setUp(self):
        super(RegistrarAPITestCase, self).setUp()

        self.edx_admin = UserFactory(username='edx-admin')
        assign_perm(perms.ORGANIZATION_READ_METADATA, self.edx_admin)

        self.stem_org = OrganizationFactory(name='STEM Institute')
        self.cs_program = ProgramFactory(
            managing_organization=self.stem_org,
            title="Master's in CS"
        )
        self.mech_program = ProgramFactory(
            managing_organization=self.stem_org,
            title="Master's in ME"
        )

        self.stem_admin = UserFactory(username='stem-institute-admin')
        self.stem_admin_group = OrganizationGroupFactory(
            organization=self.stem_org,
            role=perms.OrganizationReadMetadataRole.name
        )
        self.stem_admin.groups.add(self.stem_admin_group)  # pylint: disable=no-member

        self.hum_org = OrganizationFactory(name='Humanities College')
        self.phil_program = ProgramFactory(
            managing_organization=self.hum_org,
            title="Master's in Philosophy"
        )
        self.english_program = ProgramFactory(
            managing_organization=self.hum_org,
            title="Master's in English"
        )

        self.hum_admin = UserFactory(username='humanities-college-admin')
        self.hum_admin_group = OrganizationGroupFactory(
            organization=self.hum_org,
            role=perms.OrganizationReadMetadataRole.name
        )
        self.hum_admin.groups.add(self.hum_admin_group)  # pylint: disable=no-member

    def mock_api_response(self, url, response_data):
        responses.add(
            responses.GET,
            url,
            body=json.dumps(response_data),
            content_type='application/json',
            status=200
        )


@ddt.ddt
class ProgramListViewTests(RegistrarAPITestCase):
    """ Tests for the /api/v1/programs?org={org_key} endpoint """

    def test_all_programs(self):
        response = self.get('programs', self.edx_admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def test_all_programs_unauthorized(self):
        response = self.get('programs', self.stem_admin)
        self.assertEqual(response.status_code, 403)

    @ddt.data(True, False)
    def test_list_programs(self, is_staff):
        user = self.edx_admin if is_staff else self.stem_admin
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

    def test_list_programs_unauthorized(self):
        response = self.get('programs?org=stem-institute', self.hum_admin)
        self.assertEqual(response.status_code, 403)

    def test_org_not_found(self):
        response = self.get('programs?org=business-univ', self.stem_admin)
        self.assertEqual(response.status_code, 404)


@ddt.ddt
class ProgramRetrieveViewTests(RegistrarAPITestCase):
    """ Tests for the /api/v1/programs/{program_key} endpoint """

    @ddt.data(True, False)
    def test_get_program(self, is_staff):
        user = self.edx_admin if is_staff else self.hum_admin
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

    def test_get_program_unauthorized(self):
        response = self.get('programs/masters-in-english', self.stem_admin)
        self.assertEqual(response.status_code, 403)

    def test_program_not_found(self):
        response = self.get('programs/masters-in-polysci', self.stem_admin)
        self.assertEqual(response.status_code, 404)


@ddt.ddt
class ProgramCourseListViewTests(RegistrarAPITestCase):
    """ Tests for the /api/v1/programs/{program_key}/courses endpoint """

    @ddt.data(True, False)
    @mock_oauth_login
    @responses.activate
    def test_get_program_courses(self, is_staff):
        user = self.edx_admin if is_staff else self.hum_admin

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

        program_uuid = self.english_program.discovery_uuid
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
        response = self.get('programs/masters-in-cs/courses', self.hum_admin)
        self.assertEqual(response.status_code, 403)

    @mock_oauth_login
    @responses.activate
    def test_get_program_with_no_course_runs(self):
        user = self.hum_admin

        program_data = {
            'curricula': [{
                'courses': [{
                    'course_runs': []
                }]
            }]
        }

        program_uuid = self.english_program.discovery_uuid
        discovery_url = urljoin(settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/').format(program_uuid)
        self.mock_api_response(discovery_url, program_data)

        response = self.get('programs/masters-in-english/courses', user)

        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data, [])

    @mock_oauth_login
    @responses.activate
    def test_get_program_with_multiple_courses(self):
        user = self.stem_admin

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

        program_uuid = self.cs_program.discovery_uuid
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

    def test_program_not_found(self):
        response = self.get('programs/masters-in-polysci/courses', self.stem_admin)
        self.assertEqual(response.status_code, 404)
