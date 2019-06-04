""" Tests for API views. """
import json
import uuid
from posixpath import join as urljoin

import boto3
import ddt
import mock
import moto
import requests
import responses
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from faker import Faker
from guardian.shortcuts import assign_perm
from rest_framework.test import APITestCase
from user_tasks.tasks import UserTask

from registrar.apps.api.constants import ENROLLMENT_WRITE_MAX_SIZE
from registrar.apps.api.tests.mixins import AuthRequestMixin, TrackTestMixin
from registrar.apps.core import permissions as perms
from registrar.apps.core.jobs import (
    post_job_failure,
    post_job_success,
    start_job,
)
from registrar.apps.core.models import Organization, OrganizationGroup
from registrar.apps.core.permissions import JOB_GLOBAL_READ
from registrar.apps.core.tests.factories import (
    OrganizationFactory,
    OrganizationGroupFactory,
    UserFactory,
)
from registrar.apps.core.tests.utils import mock_oauth_login
from registrar.apps.enrollments.constants import PROGRAM_CACHE_KEY_TPL
from registrar.apps.enrollments.data import (
    LMS_PROGRAM_COURSE_ENROLLMENTS_API_TPL,
    DiscoveryProgram,
)
from registrar.apps.enrollments.tests.factories import ProgramFactory


class RegistrarAPITestCase(TrackTestMixin, APITestCase):
    """ Base for tests of the Registrar API """

    api_root = '/api/v1/'
    TEST_PROGRAM_URL_TPL = 'http://registrar-test-data.edx.org/{key}/'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.edx_admin = UserFactory(username='edx-admin')
        assign_perm(perms.ORGANIZATION_READ_METADATA, cls.edx_admin)

        # Some testing-specific terminology for the oranization groups here:
        #  - "admins" have enrollment read/write access & metadata read access
        #  - "ops" have enrollment read access & metadata read access
        #  - "users" have metadata read access

        cls.stem_org = OrganizationFactory(name='STEM Institute')
        cls.cs_program = ProgramFactory(
            key="masters-in-cs",
            managing_organization=cls.stem_org,
        )
        cls.mech_program = ProgramFactory(
            key="masters-in-me",
            managing_organization=cls.stem_org,
        )

        cls.stem_admin = UserFactory(username='stem-institute-admin')
        cls.stem_user = UserFactory(username='stem-institute-user')
        cls.stem_admin_group = OrganizationGroupFactory(
            name='stem-admins',
            organization=cls.stem_org,
            role=perms.OrganizationReadWriteEnrollmentsRole.name
        )
        cls.stem_op_group = OrganizationGroupFactory(
            name='stem-ops',
            organization=cls.stem_org,
            role=perms.OrganizationReadEnrollmentsRole.name
        )
        cls.stem_user_group = OrganizationGroupFactory(
            name='stem-users',
            organization=cls.stem_org,
            role=perms.OrganizationReadMetadataRole.name
        )
        cls.stem_admin.groups.add(cls.stem_admin_group)  # pylint: disable=no-member
        cls.stem_user.groups.add(cls.stem_user_group)  # pylint: disable=no-member

        cls.hum_org = OrganizationFactory(name='Humanities College')
        cls.phil_program = ProgramFactory(
            key="masters-in-philosophy",
            managing_organization=cls.hum_org,
        )
        cls.english_program = ProgramFactory(
            key="masters-in-english",
            managing_organization=cls.hum_org,
        )

        cls.hum_admin = UserFactory(username='humanities-college-admin')
        cls.hum_admin_group = OrganizationGroupFactory(
            name='hum-admins',
            organization=cls.hum_org,
            role=perms.OrganizationReadWriteEnrollmentsRole.name
        )
        cls.hum_op_group = OrganizationGroupFactory(
            name='hum-ops',
            organization=cls.hum_org,
            role=perms.OrganizationReadEnrollmentsRole.name
        )
        cls.hum_user_group = OrganizationGroupFactory(
            name='hum-users',
            organization=cls.hum_org,
            role=perms.OrganizationReadMetadataRole.name
        )
        cls.hum_admin.groups.add(cls.hum_admin_group)  # pylint: disable=no-member

    def mock_api_response(self, url, response_data, method='GET', response_code=200):
        responses.add(
            getattr(responses, method.upper()),
            url,
            body=json.dumps(response_data),
            content_type='application/json',
            status=response_code
        )

    def _discovery_program(self, program_uuid, title, url, curricula):
        return DiscoveryProgram.from_json(
            program_uuid,
            {
                'title': title,
                'marketing_url': url,
                'curricula': curricula
            }
        )

    def _add_programs_to_cache(self):
        programs = [self.cs_program, self.mech_program, self.english_program, self.phil_program]
        for program in programs:
            self._add_program_to_cache(
                program,
                str(program.key).replace('-', ' '),
                self.TEST_PROGRAM_URL_TPL.format(key=program.key),
            )

    def _add_program_to_cache(self, program, title, url):
        cache.set(
            PROGRAM_CACHE_KEY_TPL.format(uuid=program.discovery_uuid),
            self._discovery_program(program.discovery_uuid, title, url, [])
        )


class S3MockMixin(object):
    """
    Mixin for classes that need to access S3 resources.

    Enables S3 mock and creates default bucket before tests.
    Disables S3 mock afterwards.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._s3_mock = moto.mock_s3()
        cls._s3_mock.start()
        conn = boto3.resource('s3')
        conn.create_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)

    @classmethod
    def tearDownClass(cls):
        cls._s3_mock.stop()
        super().tearDownClass()


@ddt.ddt
class ProgramListViewTests(RegistrarAPITestCase, AuthRequestMixin):
    """ Tests for the /api/v1/programs?org={org_key} endpoint """

    method = 'GET'
    path = 'programs'
    event = 'registrar.v1.list_programs'

    def setUp(self):
        super().setUp()
        self._add_programs_to_cache()

    def test_all_programs_200(self):
        with self.assert_tracking(user=self.edx_admin):
            response = self.get('programs', self.edx_admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        response_programs = sorted(response.data, key=lambda p: p['program_key'])
        self.assertListEqual(
            response_programs,
            [
                {
                    'program_key': 'masters-in-cs',
                    'program_title': 'masters in cs',
                    'program_url': 'http://registrar-test-data.edx.org/masters-in-cs/',
                },
                {
                    'program_key': 'masters-in-english',
                    'program_title': 'masters in english',
                    'program_url': 'http://registrar-test-data.edx.org/masters-in-english/',
                },
                {
                    'program_key': 'masters-in-me',
                    'program_title': 'masters in me',
                    'program_url': 'http://registrar-test-data.edx.org/masters-in-me/',
                },
                {
                    'program_key': 'masters-in-philosophy',
                    'program_title': 'masters in philosophy',
                    'program_url': 'http://registrar-test-data.edx.org/masters-in-philosophy/',
                },
            ]
        )

    @ddt.data(

        # If you aren't staff and you don't supply a filter, you get a 403.
        {
            'groups': set(),
            'expected_status': 403,
        },
        {
            'groups': {'stem-admins'},
            'expected_status': 403,
        },
        {
            'groups': {'stem-ops', 'hum-admins'},
            'expected_status': 403,
        },

        # If you use only an org filter, and you don't have access to that org,
        # you get a 403
        {
            'groups': set(),
            'org_filter': 'stem-institute',
            'expected_status': 403,
        },
        {
            'groups': {'hum-admins'},
            'org_filter': 'stem-institute',
            'expected_status': 403,
        },

        # If you use only an org filter, and you DO have access to that org,
        # you get only that org's programs.
        {
            'groups': {'stem-users'},
            'org_filter': 'stem-institute',
            'expect_stem_programs': True,
        },
        {
            'groups': {'stem-admins', 'stem-users'},
            'org_filter': 'stem-institute',
            'expect_stem_programs': True,
        },
        {
            'groups': {'stem-ops', 'hum-admins'},
            'org_filter': 'stem-institute',
            'expect_stem_programs': True,
        },

        # If you use a permissions filter, you always get a 200, with all
        # the programs you have access to (which may be an empty list).
        {
            'groups': set(),
            'perm_filter': 'metadata',
        },
        {
            'groups': set(),
            'perm_filter': 'read',
        },
        {
            'groups': set(),
            'perm_filter': 'write',
        },
        {
            'groups': {'stem-users', 'hum-ops'},
            'perm_filter': 'write',
        },
        {
            'groups': {'stem-admins', 'hum-ops'},
            'perm_filter': 'write',
            'expect_stem_programs': True,
        },
        {
            'groups': {'stem-admins', 'hum-ops'},
            'perm_filter': 'read',
            'expect_stem_programs': True,
            'expect_hum_programs': True,
        },
        {
            'groups': {'hum-admins', 'hum-users'},
            'perm_filter': 'write',
            'expect_hum_programs': True,
        },
        {
            'groups': {'hum-admins', 'hum-users'},
            'perm_filter': 'metadata',
            'expect_hum_programs': True,
        },

        # Finally, the filters may be combined
        {
            'groups': {'stem-admins', 'hum-ops'},
            'perm_filter': 'read',
            'org_filter': 'humanities-college',
            'expect_hum_programs': True,
        },
        {
            'groups': {'stem-admins', 'hum-ops'},
            'perm_filter': 'write',
            'org_filter': 'stem-institute',
            'expect_stem_programs': True,
        },
        {
            'groups': {'stem-admins', 'hum-ops'},
            'perm_filter': 'write',
            'org_filter': 'humanities-college',
        },
    )
    @ddt.unpack
    def test_program_filters(
            self,
            groups=frozenset(),
            perm_filter=None,
            org_filter=None,
            expected_status=200,
            expect_stem_programs=False,
            expect_hum_programs=False,
    ):
        org_groups = [OrganizationGroup.objects.get(name=name) for name in groups]
        user = UserFactory(groups=org_groups)

        query = []
        tracking_kwargs = {}
        if org_filter:
            query.append('org=' + org_filter)
            tracking_kwargs['organization_filter'] = org_filter
        if perm_filter:
            query.append('user_has_perm=' + perm_filter)
            tracking_kwargs['permission_filter'] = perm_filter
        if expected_status == 403:
            tracking_kwargs['missing_permissions'] = [
                perms.ORGANIZATION_READ_METADATA
            ]
        querystring = '&'.join(query)

        expected_programs_keys = set()
        if expect_stem_programs:
            expected_programs_keys.update({
                'masters-in-cs', 'masters-in-me'
            })
        if expect_hum_programs:
            expected_programs_keys.update({
                'masters-in-english', 'masters-in-philosophy'
            })

        with self.assert_tracking(
                user=user,
                status_code=expected_status,
                **tracking_kwargs
        ):
            response = self.get('programs?' + querystring, user)
        self.assertEqual(response.status_code, expected_status)

        if expected_status == 200:
            actual_program_keys = {
                program['program_key'] for program in response.data
            }
            self.assertEqual(expected_programs_keys, actual_program_keys)

    @ddt.data(
        # Bad org filter, no perm filter
        ('intergalactic-univ', None, 'org_not_found'),
        # Bad org filter, good perm filter
        ('intergalactic-univ', 'write', 'org_not_found'),
        # No org filter, bad perm filter
        (None, 'right', 'no_such_perm'),
        # Good org filter, bad perm filter
        ('stem-institute', 'right', 'no_such_perm'),
        # Bad org filter, bad perm filter
        # Note: whether this raises `no_such_perm` or `org_not_found`
        #       is essentially an implementation detail; either would
        #       be acceptable. Either way, the user sees a 404.
        ('intergalactic-univ', 'right', 'no_such_perm'),
    )
    @ddt.unpack
    def test_404(self, org_filter, perm_filter, expected_failure):
        query = []
        tracking_kwargs = {}
        if org_filter:
            query.append('org=' + org_filter)
            tracking_kwargs['organization_filter'] = org_filter
        if perm_filter:
            query.append('user_has_perm=' + perm_filter)
            tracking_kwargs['permission_filter'] = perm_filter
        querystring = '&'.join(query)

        with self.assert_tracking(
                user=self.stem_admin,
                failure=expected_failure,
                status_code=404,
                **tracking_kwargs
        ):
            response = self.get('programs?' + querystring, self.stem_admin)
        self.assertEqual(response.status_code, 404)

    @mock.patch.object(Organization.objects, 'get', wraps=Organization.objects.get)
    def test_org_property_caching(self, get_org_wrapper):
        # If the 'managing_organization' property is not cached, a single
        # call to this endpoint would cause multiple Organization queries
        response = self.get("programs?org=stem-institute", self.stem_admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        get_org_wrapper.assert_called_once()


@ddt.ddt
class ProgramRetrieveViewTests(RegistrarAPITestCase, AuthRequestMixin):
    """ Tests for the /api/v1/programs/{program_key} endpoint """

    method = 'GET'
    path = 'programs/masters-in-english'
    event = 'registrar.v1.get_program_detail'

    def setUp(self):
        super().setUp()
        self._add_programs_to_cache()

    @ddt.data(True, False)
    def test_get_program(self, is_staff):
        user = self.edx_admin if is_staff else self.hum_admin
        with self.assert_tracking(user=user, program_key='masters-in-english'):
            response = self.get('programs/masters-in-english', user)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data,
            {
                'program_key': 'masters-in-english',
                'program_title': 'masters in english',
                'program_url': 'http://registrar-test-data.edx.org/masters-in-english/',
            },
        )

    def test_get_program_unauthorized(self):
        with self.assert_tracking(
                user=self.stem_admin,
                program_key='masters-in-english',
                missing_permissions=[perms.ORGANIZATION_READ_METADATA],
        ):
            response = self.get('programs/masters-in-english', self.stem_admin)
        self.assertEqual(response.status_code, 403)

    def test_program_not_found(self):
        with self.assert_tracking(
                user=self.stem_admin,
                program_key='masters-in-polysci',
                failure='program_not_found',
        ):
            response = self.get('programs/masters-in-polysci', self.stem_admin)
        self.assertEqual(response.status_code, 404)


@ddt.ddt
class ProgramCourseListViewTests(RegistrarAPITestCase, AuthRequestMixin):
    """ Tests for the /api/v1/programs/{program_key}/courses endpoint """

    method = 'GET'
    path = 'programs/masters-in-english/courses'
    event = 'registrar.v1.get_program_courses'

    program_uuid = str(uuid.uuid4())
    program_title = Faker().sentence(nb_words=6)  # pylint: disable=no-member
    program_url = Faker().uri()  # pylint: disable=no-member

    @ddt.data(True, False)
    @mock_oauth_login
    @responses.activate
    def test_get_program_courses(self, is_staff):
        user = self.edx_admin if is_staff else self.hum_admin

        disco_program = self._discovery_program(
            self.program_uuid,
            self.program_title,
            self.program_url,
            [
                {
                    'is_active': False,
                    'courses': []
                },
                {
                    'is_active': True,
                    'courses': [{
                        'course_runs': [
                            {
                                'key': '0001',
                                'uuid': '123456',
                                'title': 'Test Course 1',
                                'marketing_url': 'https://humanities-college.edx.org/masters-in-english/test-course-1',
                            }
                        ],
                    }]
                },
            ]
        )

        with self.assert_tracking(user=user, program_key='masters-in-english'):
            with mock.patch.object(DiscoveryProgram, 'get', return_value=disco_program):
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
        with self.assert_tracking(
                user=self.hum_admin,
                program_key='masters-in-cs',
                missing_permissions=[perms.ORGANIZATION_READ_METADATA],
        ):
            response = self.get('programs/masters-in-cs/courses', self.hum_admin)
        self.assertEqual(response.status_code, 403)

    @mock_oauth_login
    @responses.activate
    def test_get_program_with_no_course_runs(self):
        user = self.hum_admin

        disco_program = self._discovery_program(
            self.program_uuid,
            self.program_title,
            self.program_url,
            [{
                'is_active': True,
                'courses': [{
                    'course_runs': []
                }]
            }]
        )

        with self.assert_tracking(user=user, program_key='masters-in-english'):
            with mock.patch.object(DiscoveryProgram, 'get', return_value=disco_program):
                response = self.get('programs/masters-in-english/courses', user)

        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data, [])

    @mock_oauth_login
    @responses.activate
    def test_get_program_with_no_active_curriculum(self):
        user = self.hum_admin

        disco_program = self._discovery_program(
            self.program_uuid,
            self.program_title,
            self.program_url,
            [{
                'is_active': False,
                'courses': [{
                    'course_runs': []
                }]
            }]
        )

        with self.assert_tracking(user=user, program_key='masters-in-english'):
            with mock.patch.object(DiscoveryProgram, 'get', return_value=disco_program):
                response = self.get('programs/masters-in-english/courses', user)

        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data, [])

    @mock_oauth_login
    @responses.activate
    def test_get_program_with_multiple_courses(self):
        user = self.stem_admin

        disco_program = self._discovery_program(
            self.program_uuid,
            self.program_title,
            self.program_url,
            [{
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
        )

        with self.assert_tracking(user=user, program_key='masters-in-cs'):
            with mock.patch.object(DiscoveryProgram, 'get', return_value=disco_program):
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
        with self.assert_tracking(
                user=self.stem_admin,
                program_key='masters-in-polysci',
                failure='program_not_found'
        ):
            response = self.get('programs/masters-in-polysci/courses', self.stem_admin)
        self.assertEqual(response.status_code, 404)


class ProgramEnrollmentWriteMixin(object):
    """ Test write requests to the /api/v1/programs/{program_key}/enrollments endpoint """
    path = 'programs/masters-in-english/enrollments'

    @classmethod
    def setUpTestData(cls):  # pylint: disable=missing-docstring
        super().setUpTestData()
        program_uuid = cls.cs_program.discovery_uuid
        cls.disco_program = DiscoveryProgram.from_json(program_uuid, {
            'curricula': [
                {'uuid': 'inactive-curriculum-0000', 'is_active': False},
                {'uuid': 'active-curriculum-0000', 'is_active': True}
            ]
        })
        cls.program_no_curricula = DiscoveryProgram.from_json(program_uuid, {
            'curricula': []
        })
        cls.lms_request_url = urljoin(
            settings.LMS_BASE_URL, 'api/program_enrollments/v1/programs/{}/enrollments/'
        ).format(program_uuid)

    def mock_enrollments_response(self, method, expected_response, response_code=200):
        self.mock_api_response(self.lms_request_url, expected_response, method=method, response_code=response_code)

    def student_enrollment(self, status, student_key=None):
        return {
            'status': status,
            'student_key': student_key or uuid.uuid4().hex[0:10]
        }

    def test_program_unauthorized_at_organization(self):
        req_data = [
            self.student_enrollment('enrolled'),
        ]

        with self.assert_tracking(
                user=self.hum_admin,
                program_key='masters-in-cs',
                missing_permissions=[perms.ORGANIZATION_WRITE_ENROLLMENTS],
        ):
            response = self.request(
                self.method,
                'programs/masters-in-cs/enrollments/',
                self.hum_admin,
                req_data,
            )
        self.assertEqual(response.status_code, 403)

    def test_program_insufficient_permissions(self):
        req_data = [
            self.student_enrollment('enrolled'),
        ]
        with self.assert_tracking(
                user=self.stem_user,
                program_key='masters-in-cs',
                missing_permissions=[perms.ORGANIZATION_WRITE_ENROLLMENTS],
        ):
            response = self.request(
                self.method,
                'programs/masters-in-cs/enrollments/',
                self.stem_user,
                req_data,
            )
        self.assertEqual(response.status_code, 403)

    def test_program_not_found(self):
        req_data = [
            self.student_enrollment('enrolled'),
        ]
        with self.assert_tracking(
                user=self.stem_admin,
                program_key='uan-salsa-dancing-with-sharks',
                failure='program_not_found',
        ):
            response = self.request(
                self.method,
                'programs/uan-salsa-dancing-with-sharks/enrollments/',
                self.stem_admin,
                req_data,
            )
        self.assertEqual(response.status_code, 404)

    @mock_oauth_login
    @responses.activate
    def test_successful_program_enrollment_write(self):
        expected_lms_response = {
            '001': 'enrolled',
            '002': 'enrolled',
            '003': 'pending'
        }
        self.mock_enrollments_response(self.method, expected_lms_response)

        req_data = [
            self.student_enrollment('enrolled', '001'),
            self.student_enrollment('enrolled', '002'),
            self.student_enrollment('pending', '003'),
        ]

        with self.assert_tracking(user=self.stem_admin, program_key='masters-in-cs'):
            with mock.patch.object(DiscoveryProgram, 'get', return_value=self.disco_program):
                response = self.request(
                    self.method,
                    'programs/masters-in-cs/enrollments/',
                    self.stem_admin,
                    req_data,
                )

        lms_request_body = json.loads(responses.calls[-1].request.body.decode('utf-8'))
        self.assertListEqual(lms_request_body, [
            {
                'status': 'enrolled',
                'student_key': '001',
                'curriculum_uuid': 'active-curriculum-0000'
            },
            {
                'status': 'enrolled',
                'student_key': '002',
                'curriculum_uuid': 'active-curriculum-0000'
            },
            {
                'status': 'pending',
                'student_key': '003',
                'curriculum_uuid': 'active-curriculum-0000'
            }
        ])
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_lms_response)

    @mock_oauth_login
    @responses.activate
    def test_backend_unprocessable_response(self):
        self.mock_enrollments_response(self.method, "invalid enrollment record", response_code=422)

        req_data = [
            self.student_enrollment('enrolled', '001'),
            self.student_enrollment('enrolled', '002'),
            self.student_enrollment('pending', '003'),
        ]

        with self.assert_tracking(
                user=self.stem_admin,
                program_key='masters-in-cs',
                failure='unprocessable_entity',
        ):
            with mock.patch.object(DiscoveryProgram, 'get', return_value=self.disco_program):
                response = self.request(
                    self.method,
                    'programs/masters-in-cs/enrollments/',
                    self.stem_admin,
                    req_data,
                )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data, 'invalid enrollment record')

    @mock_oauth_login
    @responses.activate
    def test_backend_multi_status_response(self):
        expected_lms_response = {
            '001': 'enrolled',
            '002': 'enrolled',
            '003': 'invalid-status'
        }
        self.mock_enrollments_response(self.method, expected_lms_response, response_code=207)

        req_data = [
            self.student_enrollment('enrolled', '001'),
            self.student_enrollment('enrolled', '002'),
            self.student_enrollment('not_a_valid_value', '003'),
        ]
        with self.assert_tracking(
                user=self.stem_admin,
                program_key='masters-in-cs',
                status_code=207,
        ):
            with mock.patch.object(DiscoveryProgram, 'get', return_value=self.disco_program):
                response = self.request(
                    self.method,
                    'programs/masters-in-cs/enrollments/',
                    self.stem_admin,
                    req_data,
                )
        self.assertEqual(response.status_code, 207)
        self.assertDictEqual(response.data, expected_lms_response)

    @mock_oauth_login
    @responses.activate
    def test_backend_server_error(self):
        self.mock_enrollments_response(self.method, 'Internal Server Error', response_code=500)

        req_data = [
            self.student_enrollment('active', '001'),
            self.student_enrollment('active', '002'),
            self.student_enrollment('inactive', '003'),
        ]
        with self.assertRaisesRegex(requests.exceptions.HTTPError, 'Internal Server Error'):
            with mock.patch.object(DiscoveryProgram, 'get', return_value=self.disco_program):
                self.request(self.method, 'programs/masters-in-cs/enrollments/', self.stem_admin, req_data)

    @mock_oauth_login
    @responses.activate
    def test_backend_404(self):
        self.mock_enrollments_response(self.method, 'Not Found', response_code=404)

        req_data = [
            self.student_enrollment('active', '001'),
            self.student_enrollment('active', '002'),
            self.student_enrollment('inactive', '003'),
        ]
        with mock.patch.object(DiscoveryProgram, 'get', return_value=self.disco_program):
            response = self.request(self.method, 'programs/masters-in-cs/enrollments/', self.stem_admin, req_data)

        self.assertEqual(404, response.status_code)

    def test_write_enrollment_payload_limit(self):
        req_data = [self.student_enrollment('enrolled')] * (ENROLLMENT_WRITE_MAX_SIZE + 1)

        with self.assert_tracking(
                user=self.stem_admin,
                program_key='masters-in-cs',
                failure='request_entity_too_large',
        ):
            response = self.request(self.method, 'programs/masters-in-cs/enrollments/', self.stem_admin, req_data)
        self.assertEqual(response.status_code, 413)


class ProgramEnrollmentPostTests(ProgramEnrollmentWriteMixin, RegistrarAPITestCase, AuthRequestMixin):
    method = 'POST'
    event = 'registrar.v1.post_program_enrollment'


class ProgramEnrollmentPatchTests(ProgramEnrollmentWriteMixin, RegistrarAPITestCase, AuthRequestMixin):
    method = 'PATCH'
    event = 'registrar.v1.patch_program_enrollment'


@ddt.ddt
class ProgramEnrollmentGetTests(S3MockMixin, RegistrarAPITestCase, AuthRequestMixin):
    """ Tests for GET /api/v1/programs/{program_key}/enrollments endpoint """
    method = 'GET'
    path = 'programs/masters-in-english/enrollments'
    event = 'registrar.v1.get_program_enrollment'

    enrollments = [
        {
            'student_key': 'abcd',
            'status': 'enrolled',
            'account_exists': True,
        },
        {
            'student_key': 'efgh',
            'status': 'pending',
            'account_exists': False,
        },
    ]
    enrollments_json = json.dumps(enrollments, indent=4)
    enrollments_csv = (
        "abcd,enrolled,True\r\n"
        "efgh,pending,False\r\n"
    )

    @mock.patch(
        'registrar.apps.enrollments.tasks.get_program_enrollments',
        return_value=enrollments,
    )
    @ddt.data(
        (None, 'json', enrollments_json),
        ('json', 'json', enrollments_json),
        ('csv', 'csv', enrollments_csv),
    )
    @ddt.unpack
    def test_ok(self, format_param, expected_format, expected_contents, _mock):
        format_suffix = "?fmt=" + format_param if format_param else ""
        kwargs = {'result_format': format_param} if format_param else {}
        with self.assert_tracking(
                user=self.hum_admin,
                program_key='masters-in-english',
                status_code=202,
                **kwargs
        ):
            response = self.get(self.path + format_suffix, self.hum_admin)
        self.assertEqual(response.status_code, 202)
        with self.assert_tracking(
                event='registrar.v1.get_job_status',
                user=self.hum_admin,
                job_id=response.data['job_id'],
                job_state='Succeeded',
        ):
            job_response = self.get(response.data['job_url'], self.hum_admin)
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_response.data['state'], 'Succeeded')

        result_url = job_response.data['result']
        self.assertIn(".{}?".format(expected_format), result_url)
        file_response = requests.get(result_url)
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(file_response.text, expected_contents)

    def test_permission_denied(self):
        with self.assert_tracking(
                user=self.stem_admin,
                program_key='masters-in-english',
                missing_permissions=[perms.ORGANIZATION_READ_ENROLLMENTS],
        ):
            response = self.get(self.path, self.stem_admin)
        self.assertEqual(response.status_code, 403)

    def test_program_not_found(self):
        with self.assert_tracking(
                user=self.hum_admin,
                program_key='masters-in-polysci',
                failure='program_not_found',
        ):
            response = self.get('programs/masters-in-polysci/enrollments', self.hum_admin)
        self.assertEqual(response.status_code, 404)

    def test_invalid_format_404(self):
        with self.assert_tracking(
                user=self.hum_admin,
                program_key='masters-in-english',
                failure='result_format_not_supported',
                result_format='invalidformat',
                status_code=404,
        ):
            response = self.get(self.path + '?fmt=invalidformat', self.hum_admin)
        self.assertEqual(response.status_code, 404)


@ddt.ddt
class ProgramCourseEnrollmentGetTests(S3MockMixin, RegistrarAPITestCase, AuthRequestMixin):
    """ Tests for GET /api/v1/programs/{program_key}/enrollments endpoint """
    method = 'GET'
    path = 'programs/masters-in-english/courses/HUMx+English-550+Spring/enrollments'
    event = 'registrar.v1.get_course_enrollment'

    program_uuid = str(uuid.uuid4())
    disco_program = DiscoveryProgram.from_json(program_uuid, {
        'curricula': [{
            'is_active': True,
            'courses': [{
                'course_runs': [{
                    'key': 'HUMx+English-550+Spring',
                    'title': "English 550",
                    'marketing_url': 'https://example.com/english-550',
                }]
            }]
        }],
    })

    enrollments = [
        {
            'student_key': 'abcd',
            'status': 'enrolled',
            'account_exists': True,
        },
        {
            'student_key': 'efgh',
            'status': 'pending',
            'account_exists': False,
        },
    ]
    enrollments_json = json.dumps(enrollments, indent=4)
    enrollments_csv = (
        "abcd,enrolled,True\r\n"
        "efgh,pending,False\r\n"
    )

    @mock.patch.object(DiscoveryProgram, 'get', return_value=disco_program)
    @mock.patch(
        'registrar.apps.enrollments.tasks.get_course_run_enrollments',
        return_value=enrollments,
    )
    @ddt.data(
        (None, 'json', enrollments_json),
        ('json', 'json', enrollments_json),
        ('csv', 'csv', enrollments_csv),
    )
    @ddt.unpack
    def test_ok(self, format_param, expected_format, expected_contents, _mock1, _mock2):
        format_suffix = "?fmt=" + format_param if format_param else ""
        kwargs = {'result_format': format_param} if format_param else {}
        with self.assert_tracking(
                user=self.hum_admin,
                program_key='masters-in-english',
                course_key='HUMx+English-550+Spring',
                status_code=202,
                **kwargs
        ):
            response = self.get(self.path + format_suffix, self.hum_admin)
        self.assertEqual(response.status_code, 202)
        with self.assert_tracking(
                event='registrar.v1.get_job_status',
                user=self.hum_admin,
                job_id=response.data['job_id'],
                job_state='Succeeded',
        ):
            job_response = self.get(response.data['job_url'], self.hum_admin)
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_response.data['state'], 'Succeeded')

        result_url = job_response.data['result']
        self.assertIn(".{}?".format(expected_format), result_url)
        file_response = requests.get(result_url)
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(file_response.text, expected_contents)

    @mock.patch.object(DiscoveryProgram, 'get', return_value=disco_program)
    def test_permission_denied(self, _mock):
        with self.assert_tracking(
                user=self.stem_admin,
                program_key='masters-in-english',
                course_key='HUMx+English-550+Spring',
                missing_permissions=[perms.ORGANIZATION_READ_ENROLLMENTS],
        ):
            response = self.get(self.path, self.stem_admin)
        self.assertEqual(response.status_code, 403)

    @mock.patch.object(DiscoveryProgram, 'get', return_value=disco_program)
    @ddt.data(
        # Bad program
        ('masters-in-polysci', 'course-v1:HUMx+English-550+Spring', 'program_not_found'),
        # Good program, course key formatted correctly, but course does not exist
        ('masters-in-english', 'course-v1:STEMx+Biology-440+Fall', 'course_not_found'),
        # Good program, course key matches URL but is formatted incorrectly
        ('masters-in-english', 'not-a-course-key:a+b+c', 'course_not_found'),
    )
    @ddt.unpack
    def test_not_found(self, program_key, course_key, expected_failure, _mock):
        path_fmt = 'programs/{}/courses/{}/enrollments'
        with self.assert_tracking(
                user=self.hum_admin,
                program_key=program_key,
                course_key=course_key,
                failure=expected_failure,
        ):
            response = self.get(
                path_fmt.format(program_key, course_key), self.hum_admin
            )
        self.assertEqual(response.status_code, 404)


class JobStatusRetrieveViewTests(S3MockMixin, RegistrarAPITestCase, AuthRequestMixin):
    """ Tests for GET /api/v1/jobs/{job_id} endpoint """
    method = 'GET'
    path = 'jobs/a6393974-cf86-4e3b-a21a-d27e17932447'
    event = 'registrar.v1.get_job_status'

    def test_successful_job(self):
        job_id = start_job(self.stem_admin, _succeeding_job)
        with self.assert_tracking(
                user=self.stem_admin,
                job_id=job_id,
                job_state='Succeeded',
        ):
            job_respose = self.get('jobs/' + job_id, self.stem_admin)
        self.assertEqual(job_respose.status_code, 200)

        job_status = job_respose.data
        self.assertIn('created', job_status)
        self.assertEqual(job_status['state'], 'Succeeded')
        result_url = job_status['result']
        self.assertIn("/job-results/{}.json?".format(job_id), result_url)

        file_response = requests.get(result_url)
        self.assertEqual(file_response.status_code, 200)
        json.loads(file_response.text)  # Make sure this doesn't raise an error

    @mock.patch('registrar.apps.core.jobs.logger', autospec=True)
    def test_failed_job(self, mock_jobs_logger):
        FAIL_MESSAGE = "everything is broken"
        job_id = start_job(self.stem_admin, _failing_job, FAIL_MESSAGE)
        with self.assert_tracking(
                user=self.stem_admin,
                job_id=job_id,
                job_state='Failed',
        ):
            job_respose = self.get('jobs/' + job_id, self.stem_admin)
        self.assertEqual(job_respose.status_code, 200)

        job_status = job_respose.data
        self.assertIn('created', job_status)
        self.assertEqual(job_status['state'], 'Failed')
        self.assertIsNone(job_status['result'])
        self.assertEqual(mock_jobs_logger.error.call_count, 1)

        error_logged = mock_jobs_logger.error.call_args_list[0][0][0]
        self.assertIn(job_id, error_logged)
        self.assertIn(FAIL_MESSAGE, error_logged)

    def test_job_permission_denied(self):
        job_id = start_job(self.stem_admin, _succeeding_job)
        with self.assert_tracking(
                user=self.hum_admin,
                job_id=job_id,
                missing_permissions=[perms.JOB_GLOBAL_READ],
        ):
            job_respose = self.get('jobs/' + job_id, self.hum_admin)
        self.assertEqual(job_respose.status_code, 403)

    def test_job_global_read_permission(self):
        job_id = start_job(self.stem_admin, _succeeding_job)
        assign_perm(JOB_GLOBAL_READ, self.hum_admin)
        with self.assert_tracking(
                user=self.hum_admin,
                job_id=job_id,
                job_state='Succeeded',
        ):
            job_respose = self.get('jobs/' + job_id, self.hum_admin)
        self.assertEqual(job_respose.status_code, 200)

    def test_job_does_not_exist(self):
        nonexistant_job_id = str(uuid.uuid4())
        with self.assert_tracking(
                user=self.stem_admin,
                job_id=nonexistant_job_id,
                failure='job_not_found',
        ):
            job_respose = self.get('jobs/' + nonexistant_job_id, self.stem_admin)
        self.assertEqual(job_respose.status_code, 404)


@shared_task(base=UserTask, bind=True)
def _succeeding_job(self, job_id, user_id):  # pylint: disable=unused-argument
    """ A job that just succeeds, posting an empty JSON list as its result. """
    fake_data = Faker().pystruct(20, str, int, bool)  # pylint: disable=no-member
    post_job_success(job_id, json.dumps(fake_data), 'json')


@shared_task(base=UserTask, bind=True)
def _failing_job(self, job_id, user_id, fail_message):  # pylint: disable=unused-argument
    """ A job that just fails, providing `fail_message` as its reason """
    post_job_failure(job_id, fail_message)


@ddt.ddt
class ProgramCourseEnrollmentWriteMixin(object):
    """ Test write requests to the /api/v1/programs/{program_key}/courses/{course_id}/enrollments/ endpoint """
    # we need to define this for testing unauthenticated requests
    path = 'programs/masters-in-english/courses/course-v1:edX+DemoX+Demo_Course/enrollments'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.program_uuid = cls.cs_program.discovery_uuid
        cls.course_id = 'course-v1:edX+DemoX+Demo_Course'
        cls.lms_request_url = urljoin(
            settings.LMS_BASE_URL, LMS_PROGRAM_COURSE_ENROLLMENTS_API_TPL
        ).format(cls.program_uuid, cls.course_id)

    def get_url(self, program_key=None, course_id=None):
        """ Helper to determine the request URL for this test class. """
        kwargs = {
            'program_key': program_key or self.cs_program.key,
            'course_id': course_id or self.course_id,
        }
        return reverse('api:v1:program-course-enrollment', kwargs=kwargs)

    def mock_course_enrollments_response(self, method, expected_response, response_code=200):
        self.mock_api_response(self.lms_request_url, expected_response, method=method, response_code=response_code)

    def student_course_enrollment(self, status, student_key=None):
        return {
            'status': status,
            'student_key': student_key or uuid.uuid4().hex[0:10]
        }

    def test_program_unauthorized_at_organization(self):
        req_data = [
            self.student_course_enrollment('active'),
        ]

        # The humanities admin can't access data from the CS program
        with self.assert_tracking(
                user=self.hum_admin,
                program_key=self.cs_program.key,
                course_key=self.course_id,
                missing_permissions=[perms.ORGANIZATION_WRITE_ENROLLMENTS],
        ):
            response = self.request(
                self.method, self.get_url(), self.hum_admin, req_data
            )
        self.assertEqual(response.status_code, 403)

    def test_program_insufficient_permissions(self):
        req_data = [
            self.student_course_enrollment('active'),
        ]
        # The STEM learner doesn't have sufficient permissions to enroll learners
        with self.assert_tracking(
                user=self.stem_user,
                program_key=self.cs_program.key,
                course_key=self.course_id,
                missing_permissions=[perms.ORGANIZATION_WRITE_ENROLLMENTS],
        ):
            response = self.request(
                self.method, self.get_url(), self.stem_user, req_data
            )
        self.assertEqual(response.status_code, 403)

    def test_program_not_found(self):
        req_data = [
            self.student_course_enrollment('active'),
        ]
        # this program just doesn't exist
        with self.assert_tracking(
                user=self.stem_admin,
                program_key='uan-salsa-dancing-with-sharks',
                course_key=self.course_id,
                failure='program_not_found',
        ):
            response = self.request(
                self.method,
                self.get_url(program_key='uan-salsa-dancing-with-sharks'),
                self.stem_admin,
                req_data,
            )
        self.assertEqual(response.status_code, 404)

    @mock_oauth_login
    @responses.activate
    def test_successful_program_course_enrollment_write(self):
        expected_lms_response = {
            '001': 'active',
            '002': 'active',
            '003': 'inactive'
        }
        self.mock_course_enrollments_response(self.method, expected_lms_response)

        req_data = [
            self.student_course_enrollment('active', '001'),
            self.student_course_enrollment('active', '002'),
            self.student_course_enrollment('inactive', '003'),
        ]

        with self.assert_tracking(
                user=self.stem_admin,
                program_key=self.cs_program.key,
                course_key=self.course_id,
        ):
            response = self.request(
                self.method, self.get_url(), self.stem_admin, req_data
            )

        lms_request_body = json.loads(responses.calls[-1].request.body.decode('utf-8'))
        self.assertListEqual(lms_request_body, [
            {
                'status': 'active',
                'student_key': '001',
            },
            {
                'status': 'active',
                'student_key': '002',
            },
            {
                'status': 'inactive',
                'student_key': '003',
            }
        ])
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_lms_response)

    @mock_oauth_login
    @responses.activate
    def test_backend_unprocessable_response(self):
        self.mock_course_enrollments_response(self.method, "invalid enrollment record", response_code=422)

        req_data = [
            self.student_course_enrollment('active', '001'),
            self.student_course_enrollment('active', '002'),
            self.student_course_enrollment('inactive', '003'),
        ]

        with self.assert_tracking(
                user=self.stem_admin,
                program_key=self.cs_program.key,
                course_key=self.course_id,
                failure='unprocessable_entity',
        ):
            response = self.request(
                self.method, self.get_url(), self.stem_admin, req_data
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data, 'invalid enrollment record')

    @mock_oauth_login
    @responses.activate
    def test_backend_multi_status_response(self):
        expected_lms_response = {
            '001': 'active',
            '002': 'active',
            '003': 'invalid-status'
        }
        self.mock_course_enrollments_response(self.method, expected_lms_response, response_code=207)

        req_data = [
            self.student_course_enrollment('active', '001'),
            self.student_course_enrollment('active', '002'),
            self.student_course_enrollment('not_a_valid_value', '003'),
        ]

        with self.assert_tracking(
                user=self.stem_admin,
                program_key=self.cs_program.key,
                course_key=self.course_id,
                status_code=207,
        ):
            response = self.request(
                self.method, self.get_url(), self.stem_admin, req_data
            )

        self.assertEqual(response.status_code, 207)
        self.assertDictEqual(response.data, expected_lms_response)

    @mock_oauth_login
    @responses.activate
    def test_backend_server_error(self):
        self.mock_course_enrollments_response(self.method, 'Internal Server Error', response_code=500)

        req_data = [
            self.student_course_enrollment('active', '001'),
            self.student_course_enrollment('active', '002'),
            self.student_course_enrollment('inactive', '003'),
        ]
        with self.assertRaisesRegex(requests.exceptions.HTTPError, 'Internal Server Error'):
            self.request(self.method, self.get_url(), self.stem_admin, req_data)

    def test_write_enrollment_payload_limit(self):
        req_data = [self.student_course_enrollment('active')] * (ENROLLMENT_WRITE_MAX_SIZE + 1)

        with self.assert_tracking(
                user=self.stem_admin,
                program_key=self.cs_program.key,
                course_key=self.course_id,
                failure='request_entity_too_large',
        ):
            response = self.request(
                self.method, self.get_url(), self.stem_admin, req_data
            )

        self.assertEqual(response.status_code, 413)

    @ddt.data("this is a string", {'this is a': 'dict'})
    def test_request_not_a_list(self, payload):
        response = self.request(self.method, self.get_url(), self.stem_admin, payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('expected request body type: List', response.data)


class ProgramCourseEnrollmentPostTests(ProgramCourseEnrollmentWriteMixin, RegistrarAPITestCase, AuthRequestMixin):
    method = 'POST'
    event = 'registrar.v1.post_course_enrollment'


class ProgramCourseEnrollmentPatchTests(ProgramCourseEnrollmentWriteMixin, RegistrarAPITestCase, AuthRequestMixin):
    method = 'PATCH'
    event = 'registrar.v1.patch_course_enrollment'
