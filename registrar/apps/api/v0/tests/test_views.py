""" Tests for the v0 API views. """

import json
import uuid
import ddt
from rest_framework.test import APITestCase

from registrar.apps.api.tests.mixins import JwtMixin
from registrar.apps.core.tests.factories import UserFactory


class MockAPITestBase(APITestCase, JwtMixin):
    """ Base class for tests for the v0 API. """
    API_ROOT = '/api/v0/'
    path_suffix = None  # Define me in subclasses

    @property
    def path(self):
        return self.API_ROOT + self.path_suffix

    def setUp(self):
        super().setUp()
        self.user = UserFactory()

    def get(self, path, user):
        if user:
            return self.client.get(
                self.API_ROOT + path,
                follow=True,
                HTTP_AUTHORIZATION=self.generate_jwt_header(
                    user, admin=user.is_staff,
                )
            )
        else:
            return self.client.get(self.API_ROOT + path, follow=True)

    def post(self, path, data, user):
        if user:
            return self.client.post(
                self.API_ROOT + path,
                data=json.dumps(data),
                follow=True,
                content_type='application/json',
                HTTP_AUTHORIZATION=self.generate_jwt_header(
                    user, admin=user.is_staff,
                )
            )
        else:
            return self.client.post(
                self.API_ROOT + path, data=json.dumps(data), follow=True, content_type='application/json',
            )


# pylint: disable=no-member
class MockAPICommonTests(object):
    """ Common tests for all v0 API test cases """

    def test_unauthenticated(self):
        response = self.get(self.path, None)
        self.assertEqual(response.status_code, 401)


@ddt.ddt
class MockProgramListViewTests(MockAPITestBase, MockAPICommonTests):
    """ Tests for mock program listing """

    path_suffix = 'programs'

    def test_list_all_unauthorized(self):
        response = self.get(self.path, self.user)
        self.assertEqual(response.status_code, 403)

    def test_list_org_unauthorized(self):
        response = self.get(self.path + '?org=u-perezburgh', self.user)
        self.assertEqual(response.status_code, 403)

    def test_org_not_found(self):
        response = self.get(self.path + '?org=antarctica-tech', self.user)
        self.assertEqual(response.status_code, 404)

    @ddt.data(
        ('brianchester-college', 1),
        ('donnaview-inst', 2),
        ('holmeshaven-polytech', 3),
    )
    @ddt.unpack
    def test_success(self, org_key, num_programs):
        response = self.get(self.path + '?org={}'.format(org_key), self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), num_programs)


@ddt.ddt
class MockProgramRetrieveViewTests(MockAPITestBase, MockAPICommonTests):
    """ Tests for mock program retrieve """

    path_suffix = 'programs/'

    def test_program_unauthorized(self):
        response = self.get(self.path + 'upz-masters-ancient-history', self.user)
        self.assertEqual(response.status_code, 403)

    def test_program_not_found(self):
        response = self.get(self.path + 'uan-masters-underwater-basket-weaving', self.user)
        self.assertEqual(response.status_code, 404)

    @ddt.data(
        'bcc-masters-english-lit',
        'dvi-masters-polysci',
        'dvi-mba',
        'hhp-masters-ce',
        'hhp-masters-theo-physics',
        'hhp-masters-enviro',
    )
    def test_program_retrieve(self, program_key):
        response = self.get(self.path + program_key, self.user)
        self.assertEqual(response.status_code, 200)


@ddt.ddt
class MockCourseListViewTests(MockAPITestBase, MockAPICommonTests):
    """ Tests for mock course listing """

    path_suffix = 'programs/bcc-masters-english-lit/courses'  # for 401 test only

    def test_program_unauthorized(self):
        response = self.get('programs/upz-masters-ancient-history/courses', self.user)
        self.assertEqual(response.status_code, 403)

    def test_program_not_found(self):
        response = self.get('programs/uan-masters-underwater-basket-weaving/courses', self.user)
        self.assertEqual(response.status_code, 404)

    @ddt.data(
        ('bcc-masters-english-lit', 4),
        ('dvi-masters-polysci', 4),
        ('dvi-mba', 2),
        ('hhp-masters-ce', 4),
        ('hhp-masters-theo-physics', 3),
        ('hhp-masters-enviro', 0),
    )
    @ddt.unpack
    def test_program_retrieve(self, program_key, num_courses):
        response = self.get('programs/{}/courses'.format(program_key), self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), num_courses)


class MockProgramEnrollmentViewTests(MockAPITestBase, MockAPICommonTests):
    """ Test for mock program enrollment """

    def student_enrollment(self, email, status, student_key=None):
        return {
            'email': email,
            'status': status,
            'student_key': student_key or uuid.uuid4().hex[0:10]
        }

    def test_unauthenticated(self):
        post_data = [
            self.student_enrollment('jjohn@mit.edu', 'enrolled')
        ]
        response = self.post(
            'programs/upz-masters-ancient-history/enrollments/',
            post_data,
            None
        )
        self.assertEqual(response.status_code, 401)

    def test_program_unauthorized(self):
        post_data = [
            self.student_enrollment('jjohn@mit.edu', 'enrolled')
        ]
        response = self.post(
            'programs/dvi-masters-polysci/enrollments/',
            post_data,
            self.user
        )
        self.assertEqual(response.status_code, 403)

    def test_program_not_found(self):
        post_data = [
            self.student_enrollment('jjohn@mit.edu', 'enrolled')
        ]
        response = self.post(
            'programs/uan-shark-tap-dancing/enrollments/',
            post_data,
            self.user
        )
        self.assertEqual(response.status_code, 404)

    def test_successful_program_enrollment(self):
        post_data = [
            self.student_enrollment('hefferWolfe@mit.edu', 'enrolled', '001'),
            self.student_enrollment('invader_zim@mit.edu', 'enrolled', '002'),
            self.student_enrollment('snarf@mit.edu', 'pending', '003'),
        ]
        response = self.post(
            'programs/hhp-masters-theo-physics/enrollments/',
            post_data,
            self.user
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            '001': 'enrolled',
            '002': 'enrolled',
            '003': 'pending',
        })

    def test_partially_valid_enrollment(self):
        post_data = [
            self.student_enrollment('hefferWolfe@mit.edu', 'new', '001'),
            self.student_enrollment('snarf@mit.edu', 'pending', '003'),
        ]
        response = self.post(
            'programs/hhp-masters-theo-physics/enrollments/',
            post_data,
            self.user
        )

        self.assertEqual(response.status_code, 207)
        self.assertEqual(response.data, {
            '001': 'invalid-status',
            '003': 'pending',
        })

    def test_unprocessable_enrollment(self):
        response = self.post(
            'programs/hhp-masters-theo-physics/enrollments/',
            [{'status': 'enrolled'}],
            self.user
        )

        self.assertEqual(response.status_code, 422)

    def test_duplicate_enrollment(self):
        post_data = [
            self.student_enrollment('hefferWolfe@mit.edu', 'enrolled', '001'),
            self.student_enrollment('invader_zim@mit.edu', 'enrolled', '002'),
            self.student_enrollment('hefferWolfe@mit.edu', 'enrolled', '001'),
        ]
        response = self.post(
            'programs/hhp-masters-theo-physics/enrollments/',
            post_data,
            self.user
        )

        self.assertEqual(response.status_code, 207)
        self.assertEqual(response.data, {
            '001': 'duplicated',
            '002': 'enrolled',
        })

    def test_enrollment_payload_limit(self):
        post_data = []
        for i in range(26):
            post_data += self.student_enrollment(
                'user{}@mit.edu'.format(i), 'enrolled'
            )

        response = self.post(
            'programs/hhp-masters-theo-physics/enrollments/',
            post_data,
            self.user
        )

        self.assertEqual(response.status_code, 413)
