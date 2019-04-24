""" Tests for the v1_mock API views. """

import uuid

import ddt
import mock
from rest_framework.test import APITestCase

from registrar.apps.api.tests.mixins import AuthRequestMixin
from registrar.apps.api.v1_mock.data import (
    FAKE_PROGRAMS,
    invoke_fake_course_enrollment_listing_job,
    invoke_fake_program_enrollment_listing_job,
)
from registrar.apps.core.permissions import OrganizationReadMetadataRole
from registrar.apps.core.tests.factories import (
    GroupFactory,
    UserFactory,
    OrganizationFactory,
    OrganizationGroupFactory
)


class MockAPITestMixin(AuthRequestMixin):
    """ Base mixin for tests for the v1_mock API. """
    api_root = '/api/v1-mock/'
    event = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_org = OrganizationFactory()
        cls.user_org_group = OrganizationGroupFactory(organization=cls.user_org)
        cls.user = UserFactory(groups=[cls.user_org_group])
        cls.admin_read_metadata_group = GroupFactory(
            name='admin_read_metadata',
            permissions=OrganizationReadMetadataRole.permissions,
        )
        cls.admin_user = UserFactory(groups=[cls.admin_read_metadata_group])
        cls.patcher = mock.patch('registrar.apps.api.segment.track', autospec=True)

    def setUp(self):
        super().setUp()
        self.mock_track = self.patcher.start()

    @property
    def path(self):
        return self.api_root + self.path_suffix

    def assert_segment_tracking(self, user=None, **kwargs):
        """
        Make sure the segment events are created when the request is made
        """
        properties = kwargs.copy()

        if 'user_organizations' not in properties:
            properties['user_organizations'] = [self.user_org.name]

        if not user:
            user = self.user

        self.mock_track.assert_called_once_with(
            user.username,
            self.event,
            properties
        )

    def tearDown(self):
        super().tearDown()
        self.patcher.stop()


class MockJobTestMixin(MockAPITestMixin):
    """ Mixin for testing the results of a job """

    def assert_job_result(self, job_id, job_url, expected_state, expected_path):
        """
        Gets the job at ``job_url``. Asserts:
         * Response is 200
         * Job dict has 'created' key
         * Provided ``expected_state`` matches job's
         * Provided ``expected_path`` is substring of job's result
         * Segment event is created for job retrival
        """
        job_response = self.get(job_url, self.user)
        self.assertEqual(200, job_response.status_code)
        job_data = job_response.data
        self.assertIn('created', job_data)
        self.assertEqual(job_data['state'], expected_state)
        if expected_path:
            self.assertIn(expected_path, job_data['result'])
        else:
            self.assertIsNone(job_data['result'])
        self.event = 'registrar.v1_mock.get_job_status'
        self.assert_segment_tracking(
            job_id=job_id,
            job_state=job_data['state'],
        )


@ddt.ddt
class MockProgramListViewTests(MockAPITestMixin, APITestCase):
    """ Tests for mock program listing """

    method = 'GET'
    path = 'programs'
    event = 'registrar.v1_mock.list_programs'

    def test_list_all_unauthorized(self):
        response = self.get(self.path, self.user)
        self.assertEqual(response.status_code, 403)
        self.assert_segment_tracking(permission_failure='no_org_key')

    def test_list_all_admin_user(self):
        response = self.get(self.path, self.admin_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), len(FAKE_PROGRAMS))
        self.assert_segment_tracking(
            user=self.admin_user,
            user_organizations=[],
        )

    def test_list_org_unauthorized(self):
        org_key = 'u-perezburgh'
        response = self.get(self.path + '?org=' + org_key, self.user)
        self.assertEqual(response.status_code, 403)
        self.assert_segment_tracking(
            organization_filter=org_key,
            permission_failure='no_org_permission',
        )

    def test_list_org_no_perm_but_admin(self):
        """
        Every organization's metadata should be visible to the admin user,
        even u-perezburgh.
        """
        response = self.get(self.path + '?org=u-perezburgh', self.admin_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_org_not_found(self):
        response = self.get(self.path + '?org=antarctica-tech', self.user)
        self.assertEqual(response.status_code, 404)
        self.assert_segment_tracking(
            org_key='antarctica-tech',
            failure='org_not_found',
        )

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
        self.assert_segment_tracking(organization_filter=org_key)


@ddt.ddt
class MockProgramRetrieveViewTests(MockAPITestMixin, APITestCase):
    """ Tests for mock program retrieve """

    method = 'GET'
    path = 'programs/'
    event = 'registrar.v1_mock.get_program_detail'

    def test_program_unauthorized(self):
        response = self.get(self.path + 'upz-masters-ancient-history', self.user)
        self.assertEqual(response.status_code, 403)
        self.assert_segment_tracking(
            program_key='upz-masters-ancient-history',
            permission_failure='no_program_read_permission',
        )

    def test_program_not_found(self):
        response = self.get(self.path + 'uan-masters-underwater-basket-weaving', self.user)
        self.assertEqual(response.status_code, 404)
        self.assert_segment_tracking(
            program_key='uan-masters-underwater-basket-weaving',
            failure='program_not_found',
        )

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
        self.assert_segment_tracking(program_key=program_key)


@ddt.ddt
class MockCourseListViewTests(MockAPITestMixin, APITestCase):
    """ Tests for mock course listing """

    # For AuthN test
    method = 'GET'
    path = 'programs/bcc-masters-english-lit/courses'
    event = 'registrar.v1_mock.get_program_courses'

    def test_program_unauthorized(self):
        response = self.get('programs/upz-masters-ancient-history/courses', self.user)
        self.assertEqual(response.status_code, 403)
        self.assert_segment_tracking(
            program_key='upz-masters-ancient-history',
            permission_failure='no_program_read_permission',
        )

    def test_program_not_found(self):
        response = self.get('programs/uan-masters-underwater-basket-weaving/courses', self.user)
        self.assertEqual(response.status_code, 404)
        self.assert_segment_tracking(
            program_key='uan-masters-underwater-basket-weaving',
            failure='program_not_found',
        )

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
        self.assert_segment_tracking(program_key=program_key)


class MockProgramEnrollmentPostTests(MockAPITestMixin, APITestCase):
    """ Test for mock program enrollment """

    # For AuthN test
    method = 'POST'
    path = 'programs/hhp-masters-ce/enrollments/'
    event = 'registrar.v1_mock.post_program_enrollment'

    def student_enrollment(self, status, student_key=None):
        return {
            'status': status,
            'student_key': student_key or uuid.uuid4().hex[0:10]
        }

    def test_unauthenticated(self):
        post_data = [
            self.student_enrollment('enrolled')
        ]
        response = self.post(
            'programs/upz-masters-ancient-history/enrollments/',
            post_data,
            None
        )
        self.assertEqual(response.status_code, 401)

    def test_program_unauthorized(self):
        post_data = [
            self.student_enrollment('enrolled')
        ]
        response = self.post(
            'programs/dvi-masters-polysci/enrollments/',
            post_data,
            self.user
        )
        self.assertEqual(response.status_code, 403)
        self.assert_segment_tracking(
            program_key='dvi-masters-polysci',
            permission_failure='no_enrollments_write_permission',
        )

    def test_program_not_found(self):
        post_data = [
            self.student_enrollment('enrolled')
        ]
        response = self.post(
            'programs/uan-shark-tap-dancing/enrollments/',
            post_data,
            self.user
        )
        self.assertEqual(response.status_code, 404)
        self.assert_segment_tracking(
            program_key='uan-shark-tap-dancing',
            failure='program_not_found',
        )

    def test_successful_program_enrollment(self):
        post_data = [
            self.student_enrollment('enrolled', '001'),
            self.student_enrollment('enrolled', '002'),
            self.student_enrollment('pending', '003'),
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
        self.assert_segment_tracking(program_key='hhp-masters-theo-physics')

    def test_partially_valid_enrollment(self):
        post_data = [
            self.student_enrollment('new', '001'),
            self.student_enrollment('pending', '003'),
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

        self.assert_segment_tracking(program_key='hhp-masters-theo-physics')

    def test_unprocessable_enrollment(self):
        response = self.post(
            'programs/hhp-masters-theo-physics/enrollments/',
            [{'status': 'enrolled'}],
            self.user
        )

        self.assertEqual(response.status_code, 422)
        self.assert_segment_tracking(
            program_key='hhp-masters-theo-physics',
            failure='unprocessable_entity',
        )

    def test_duplicate_enrollment(self):
        post_data = [
            self.student_enrollment('enrolled', '001'),
            self.student_enrollment('enrolled', '002'),
            self.student_enrollment('pending', '001'),
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
        self.assert_segment_tracking(program_key='hhp-masters-theo-physics')

    def test_enrollment_payload_limit(self):
        post_data = []
        for _ in range(26):
            post_data += self.student_enrollment('enrolled')

        response = self.post(
            'programs/hhp-masters-theo-physics/enrollments/',
            post_data,
            self.user
        )

        self.assertEqual(response.status_code, 413)
        self.assert_segment_tracking(
            program_key='hhp-masters-theo-physics',
            failure='request_entity_too_large',
        )


@ddt.ddt
class MockProgramEnrollmentPatchTests(MockAPITestMixin, APITestCase):
    """ Tests for mock modify program enrollment """

    method = 'PATCH'
    path = 'programs/hhp-masters-ce/enrollments/'
    event = 'registrar.v1_mock.patch_program_enrollment'

    def learner_modification(self, student_key, status):
        return {"student_key": student_key, "status": status}

    def test_200_ok(self):
        patch_data = [
            self.learner_modification("A", "enrolled"),
            self.learner_modification("B", "pending"),
            self.learner_modification("C", "suspended"),
            self.learner_modification("D", "canceled"),
        ]
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "A": "enrolled",
                "B": "pending",
                "C": "suspended",
                "D": "canceled"
            },
            response.data
        )
        self.assert_segment_tracking(program_key='hhp-masters-ce')

    def test_207_multi_status(self):
        """ Also tests duplicates """
        patch_data = [
            self.learner_modification("A", "enrolled"),
            self.learner_modification("A", "enrolled"),
            self.learner_modification("B", "not-a-status"),
            self.learner_modification("C", "enrolled"),
        ]
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(207, response.status_code)
        self.assertDictEqual(
            {
                'A': 'duplicated',
                'B': 'invalid-status',
                'C': 'enrolled',
            },
            response.data
        )
        self.assert_segment_tracking(program_key='hhp-masters-ce')

    def test_403_forbidden(self):
        path_403 = 'programs/dvi-masters-polysci/enrollments/'
        patch_data = [self.learner_modification("A", "enrolled")]
        response = self.patch(path_403, patch_data, self.user)
        self.assertEqual(403, response.status_code)
        self.assert_segment_tracking(
            program_key='dvi-masters-polysci',
            permission_failure='no_enrollments_write_permission',
        )

    def test_413_payload_too_large(self):
        patch_data = [self.learner_modification(str(i), "enrolled") for i in range(30)]
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(413, response.status_code)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            failure='request_entity_too_large',
        )

    def test_404_not_found(self):
        path_404 = 'programs/nonexistant-program-will-404/enrollments/'
        patch_data = [self.learner_modification("A", "enrolled")]
        response = self.patch(path_404, patch_data, self.user)
        self.assertEqual(404, response.status_code)
        self.assert_segment_tracking(
            program_key='nonexistant-program-will-404',
            failure='program_not_found',
        )

    def test_422_unprocessable_entity(self):
        patch_data = [{'student_key': 'A', 'status': 'this-is-not-a-status'}]
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(422, response.status_code)
        self.assertDictEqual({'A': 'invalid-status'}, response.data)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            failure='unprocessable_entity',
        )

    @ddt.data(
        [{'status': 'enrolled'}],
        [{'student_key': '000'}],
        ["this isn't even a dict!"],
        [{'student_key': '000', 'status': 'enrolled'}, "bad_data"],
    )
    def test_422_unprocessable_entity_bad_data(self, patch_data):
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(response.status_code, 422)
        self.assertIn('invalid enrollment record', response.data)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            failure='unprocessable_entity',
        )


def _mock_invoke_program_job(duration):
    """
    Return a wrapper around ``invoke_fake_program_enrollment_listing_job`` that
    ignores supplied ``min_duration`` and ``max_duration`` and replaces them
    both with the ``duration`` argument to this function.
    """
    def inner(program_key, min_duration=5, max_duration=5):  # pylint: disable=unused-argument
        return invoke_fake_program_enrollment_listing_job(
            program_key, duration, duration,
        )
    return inner


@ddt.ddt
class MockProgramEnrollmentGetTests(MockJobTestMixin, APITestCase):
    """
    Tests for the mock retrieval of program enrollments data via fake async jobs.
    """
    method = 'GET'
    path = 'programs/hhp-masters-ce/enrollments/'
    event = 'registrar.v1_mock.get_program_enrollment'

    def _get_enrollments(self, program_key):
        return self.get('programs/{}/enrollments/'.format(program_key), self.user)

    @ddt.data(
        'upz-masters-ancient-history',
        'bcc-masters-english-lit',
    )
    def test_program_unauthorized(self, program_key):
        response = self._get_enrollments(program_key)
        self.assertEqual(403, response.status_code)
        self.assert_segment_tracking(
            program_key=program_key,
            permission_failure='no_enrollments_read_permission',
        )

    def test_program_not_found(self):
        response = self._get_enrollments('not-a-program')
        self.assertEqual(404, response.status_code)
        self.assert_segment_tracking(
            program_key='not-a-program',
            failure='program_not_found',
        )

    @ddt.data(
        ('dvi-masters-polysci', 10, 'In Progress', None),
        ('dvi-masters-polysci', 0, 'Succeeded', 'polysci.json'),
        ('dvi-mba', 0, 'Succeeded', 'mba.json'),
        ('hhp-masters-ce', 0, 'Succeeded', 'ce.json'),
        ('hhp-masters-theo-physics', 0, 'Succeeded', 'physics.json'),
        ('hhp-masters-enviro', 10, 'In Progress', None),
        ('hhp-masters-enviro', 0, 'Failed', None),
    )
    @ddt.unpack
    def test_program_get_202(self, program_key, job_duration, expected_state, expected_fname):
        with mock.patch(
                'registrar.apps.api.v1_mock.views.invoke_fake_program_enrollment_listing_job',
                new=_mock_invoke_program_job(job_duration),
        ):
            response = self._get_enrollments(program_key)

        self.assertEqual(202, response.status_code)
        self.assert_segment_tracking(program_key=program_key)
        self.mock_track.reset_mock()
        RESULTS_ROOT = '/static/api/v1_mock/program-enrollments/'
        expected_path = RESULTS_ROOT + expected_fname if expected_fname else None
        self.assert_job_result(
            response.data['job_id'], response.data['job_url'], expected_state, expected_path,
        )


@ddt.ddt
class MockCourseEnrollmentPostTests(MockAPITestMixin, APITestCase):
    """ Tests for mock course enrollment """

    method = 'POST'
    path = 'programs/hhp-masters-ce/courses/course-v1:HHPx+MA-102+Fall2050/enrollments/'
    event = 'registrar.v1_mock.post_course_enrollment'

    def learner_enrollment(self, student_key, status):
        return {"student_key": student_key, "status": status}

    def test_200_ok(self):
        post_data = [
            self.learner_enrollment("A", "active"),
            self.learner_enrollment("B", "inactive"),
        ]
        response = self.post(self.path, post_data, self.user)
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "A": "active",
                "B": "inactive",
            },
            response.data
        )
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
        )

    def test_207_multi_status(self):
        """ Also tests duplicates """
        post_data = [
            self.learner_enrollment("A", "active"),
            self.learner_enrollment("A", "inactive"),
            self.learner_enrollment("B", "not-a-status"),
            self.learner_enrollment("C", "active"),
        ]
        response = self.post(self.path, post_data, self.user)
        self.assertEqual(207, response.status_code)
        self.assertDictEqual(
            {
                'A': 'duplicated',
                'B': 'invalid-status',
                'C': 'active',
            },
            response.data
        )
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
        )

    def test_403_forbidden(self):
        path_403 = 'programs/dvi-masters-polysci/courses/course-v1:DVIx+GOV-200+Spring2050/enrollments/'
        post_data = [self.learner_enrollment("A", "active")]
        response = self.post(path_403, post_data, self.user)
        self.assertEqual(403, response.status_code)
        self.assert_segment_tracking(
            program_key='dvi-masters-polysci',
            course_key='course-v1:DVIx+GOV-200+Spring2050',
            permission_failure='no_enrollments_write_permission',
        )

    def test_413_payload_too_large(self):
        post_data = [self.learner_enrollment(str(i), "active") for i in range(30)]
        response = self.post(self.path, post_data, self.user)
        self.assertEqual(413, response.status_code)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
            failure='request_entity_too_large',
        )

    def test_404_not_found_program(self):
        path_404 = 'programs/nonexistant-program/courses/course-v1:HHPx+MA-102+Fall2050/enrollments/'
        post_data = [self.learner_enrollment("A", "active")]
        response = self.post(path_404, post_data, self.user)
        self.assertEqual(404, response.status_code)
        self.assert_segment_tracking(
            program_key='nonexistant-program',
            failure='program_not_found',
        )

    @ddt.data(
        "course-v1:HHPx+FAKE-3333+Spring1776",  # nonexistant
        "course-v1:HHPx+PHYS-260+Spring2050"  # not in this program
    )
    def test_404_not_found_course(self, course):
        path_404 = 'programs/hhp-masters-ce/courses/{}/enrollments/'.format(course)
        post_data = [self.learner_enrollment("A", "active")]
        response = self.post(path_404, post_data, self.user)
        self.assertEqual(404, response.status_code)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key=course,
            failure='course_not_found',
        )

    def test_422_unprocessable_entity(self):
        post_data = [self.learner_enrollment('A', 'this-is-not-a-status')]
        response = self.post(self.path, post_data, self.user)
        self.assertEqual(422, response.status_code)
        self.assertDictEqual({'A': 'invalid-status'}, response.data)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
            failure='unprocessable_entity',
        )

    @ddt.data(
        [{'status': 'active'}],
        [{'student_key': '000'}],
        ["this isn't even a dict!"],
        [{'student_key': '000', 'status': 'active'}, "bad_data"],
    )
    def test_422_unprocessable_entity_bad_data(self, post_data):
        response = self.post(self.path, post_data, self.user)
        self.assertEqual(response.status_code, 422)
        self.assertIn('invalid enrollment record', response.data)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
            failure='unprocessable_entity',
        )


@ddt.ddt
class MockCourseEnrollmentPatchTests(MockAPITestMixin, APITestCase):
    """ Tests for mock modify course enrollment """

    # For AuthN test
    method = 'PATCH'
    path = 'programs/hhp-masters-ce/courses/course-v1:HHPx+MA-102+Fall2050/enrollments/'
    event = 'registrar.v1_mock.patch_course_enrollment'

    def learner_modification(self, student_key, status):
        return {"student_key": student_key, "status": status}

    def test_200_ok(self):
        patch_data = [
            self.learner_modification("A", "active"),
            self.learner_modification("B", "inactive"),
        ]
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "A": "active",
                "B": "inactive",
            },
            response.data
        )
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
        )

    def test_207_multi_status(self):
        """ Also tests duplicates """
        patch_data = [
            self.learner_modification("A", "active"),
            self.learner_modification("A", "inactive"),
            self.learner_modification("B", "not-a-status"),
            self.learner_modification("C", "active"),
        ]
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(207, response.status_code)
        self.assertDictEqual(
            {
                'A': 'duplicated',
                'B': 'invalid-status',
                'C': 'active',
            },
            response.data
        )
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
        )

    def test_403_forbidden(self):
        path_403 = 'programs/dvi-masters-polysci/courses/course-v1:DVIx+GOV-200+Spring2050/enrollments/'
        patch_data = [self.learner_modification("A", "active")]
        response = self.patch(path_403, patch_data, self.user)
        self.assertEqual(403, response.status_code)
        self.assert_segment_tracking(
            program_key='dvi-masters-polysci',
            course_key='course-v1:DVIx+GOV-200+Spring2050',
            permission_failure='no_enrollments_write_permission',
        )

    def test_413_payload_too_large(self):
        patch_data = [self.learner_modification(str(i), "active") for i in range(30)]
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(413, response.status_code)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
            failure='request_entity_too_large',
        )

    def test_404_not_found_program(self):
        path_404 = 'programs/nonexistant-program/courses/course-v1:HHPx+MA-102+Fall2050/enrollments/'
        patch_data = [self.learner_modification("A", "active")]
        response = self.patch(path_404, patch_data, self.user)
        self.assertEqual(404, response.status_code)
        self.assert_segment_tracking(
            program_key='nonexistant-program',
            failure='program_not_found',
        )

    @ddt.data(
        "course-v1:HHPx+FAKE-3333+Spring1776",  # nonexistant
        "course-v1:HHPx+PHYS-260+Spring2050"  # not in this program
    )
    def test_404_not_found_course(self, course):
        path_404 = 'programs/hhp-masters-ce/courses/{}/enrollments/'.format(course)
        patch_data = [self.learner_modification("A", "active")]
        response = self.patch(path_404, patch_data, self.user)
        self.assertEqual(404, response.status_code)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key=course,
            failure='course_not_found',
        )

    def test_422_unprocessable_entity(self):
        patch_data = [self.learner_modification('A', 'this-is-not-a-status')]
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(422, response.status_code)
        self.assertDictEqual({'A': 'invalid-status'}, response.data)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
            failure='unprocessable_entity',
        )

    @ddt.data(
        [{'status': 'active'}],
        [{'student_key': '000'}],
        ["this isn't even a dict!"],
        [{'student_key': '000', 'status': 'active'}, "bad_data"],
    )
    def test_422_unprocessable_entity_bad_data(self, patch_data):
        response = self.patch(self.path, patch_data, self.user)
        self.assertEqual(response.status_code, 422)
        self.assertIn('invalid enrollment record', response.data)
        self.assert_segment_tracking(
            program_key='hhp-masters-ce',
            course_key='course-v1:HHPx+MA-102+Fall2050',
            failure='unprocessable_entity',
        )


def _mock_invoke_course_job(duration):
    """
    Return a wrapper around ``invoke_fake_course_enrollment_listing_job`` that
    ignores supplied ``min_duration`` and ``max_duration`` and replaces them
    both with the ``duration`` argument to this function.
    """
    def inner(program_key, course_key, min_duration=5, max_duration=5):  # pylint: disable=unused-argument
        return invoke_fake_course_enrollment_listing_job(
            program_key, course_key, duration, duration,
        )
    return inner


@ddt.ddt
class MockCourseEnrollmentGetTests(MockJobTestMixin, APITestCase):
    """
    Tests for the mock retrieval of program enrollments data via fake async jobs.
    """

    # For AuthN test
    method = 'GET'
    path = 'programs/dvi-mba/courses/DVIx+BIZ-200+Spring2050/enrollments'
    event = 'registrar.v1_mock.get_course_enrollment'

    def _get_enrollments(self, program_key, course_key):
        return self.get(
            'programs/{}/courses/{}/enrollments'.format(program_key, course_key),
            self.user,
        )

    @ddt.data(
        ('upz-masters-ancient-history', 'UPZx+HIST-101+Spring2050'),
        ('bcc-masters-english-lit', 'BCCx+EN-111+Spring2050'),
    )
    @ddt.unpack
    def test_program_unauthorized(self, program_key, course_key):
        response = self._get_enrollments(program_key, course_key)
        self.assertEqual(403, response.status_code)
        self.assert_segment_tracking(
            program_key=program_key,
            course_key=course_key,
            permission_failure='no_enrollments_read_permission'
        )

    @ddt.data(
        ('not-a-program', 'NOTORGx+not-a-course+Bad2010', 'program_not_found'),
        ('not-a-program', 'HHPx+MA-101+Spring2050', 'program_not_found'),
        ('hhp-masters-ce', 'NOTORGx+not-a-course+Bad2010', 'course_not_found'),
        ('hhp-masters-ce', 'BCCx+EN-111+Spring2050', 'course_not_found'),  # real course, wrong program
    )
    @ddt.unpack
    def test_course_not_found(self, program_key, course_key, event_failure):
        response = self._get_enrollments(program_key, course_key)
        self.assertEqual(404, response.status_code)
        if event_failure == 'program_not_found':
            self.assert_segment_tracking(
                program_key=program_key,
                failure=event_failure,
            )
        else:
            self.assert_segment_tracking(
                program_key=program_key,
                course_key=course_key,
                failure=event_failure,
            )

    @ddt.data(
        (
            'dvi-masters-polysci',
            'course-v1:DVIx+COMM-101+Spring2050',
            10,
            'In Progress',
            None,
        ),
        (
            'dvi-masters-polysci',
            'course-v1:DVIx+COMM-101+Spring2050',
            0,
            'Succeeded',
            'polysci-comm-101.json',
        ),
        (
            'dvi-masters-polysci',
            'course-v1:DVIx+GOV-200+Spring2050',
            0,
            'Succeeded',
            'polysci-gov-200.json',
        ),
        (
            'dvi-masters-polysci',
            'course-v1:DVIx+GOV-201+Spring2050',
            0,
            'Succeeded',
            'polysci-gov-201.json',
        ),
        (
            'dvi-masters-polysci',
            'course-v1:DVIx+GOV-202+Spring2050',
            0,
            'Succeeded',
            'polysci-gov-202.json',
        ),
        (
            'dvi-mba',
            'course-v1:DVIx+COMM-101+Spring2050',
            0,
            'Succeeded',
            'mba-comm-101.json',
        ),
        (
            'dvi-mba',
            'course-v1:DVIx+BIZ-200+Spring2050',
            0,
            'Succeeded',
            'mba-biz-200.json',
        ),
        (
            'hhp-masters-ce',
            'course-v1:HHPx+MA-101+Spring2050',
            0,
            'Succeeded',
            'ce-ma-101.json',
        ),
        (
            'hhp-masters-ce',
            'course-v1:HHPx+MA-102+Fall2050',
            0,
            'Succeeded',
            'ce-ma-102.json',
        ),
        (
            'hhp-masters-ce',
            'course-v1:HHPx+CE-300+Spring2050',
            0,
            'Succeeded',
            'ce-ce-300-spring.json',
        ),
        (
            'hhp-masters-ce',
            'course-v1:HHPx+CE-300+Summer2050',
            0,
            'Succeeded',
            'ce-ce-300-summer.json',
        ),
        (
            'hhp-masters-theo-physics',
            'course-v1:HHPx+MA-101+Spring2050',
            0,
            'Succeeded',
            'physics-ma-101.json',
        ),
        (
            'hhp-masters-theo-physics',
            'course-v1:HHPx+MA-102+Fall2050',
            0,
            'Succeeded',
            'physics-ma-102.json',
        ),
        (
            'hhp-masters-theo-physics',
            'course-v1:HHPx+PHYS-260+Spring2050',
            10,
            'In Progress',
            None,
        ),
        (
            'hhp-masters-theo-physics',
            'course-v1:HHPx+PHYS-260+Spring2050',
            0,
            'Failed',
            None,
        ),
    )
    @ddt.unpack
    def test_course_get_202(self, program_key, course_key, job_duration, expected_state, expected_fname):
        with mock.patch(
                'registrar.apps.api.v1_mock.views.invoke_fake_course_enrollment_listing_job',
                new=_mock_invoke_course_job(job_duration),
        ):
            response = self._get_enrollments(program_key, course_key)

        self.assertEqual(202, response.status_code)
        self.assert_segment_tracking(program_key=program_key, course_key=course_key)
        self.mock_track.reset_mock()
        RESULTS_ROOT = '/static/api/v1_mock/course-enrollments/'
        expected_path = RESULTS_ROOT + expected_fname if expected_fname else None
        self.assert_job_result(
            response.data['job_id'], response.data['job_url'], expected_state, expected_path,
        )


class MockJobRetrievalTests(MockAPITestMixin, APITestCase):
    """Test case to make sure only AuthN'ed users can get job statuses"""

    # We need not define any tests functions here, because:
    #  (1) MockAPITestMixin superclass will check that this 401s
    #      if a user is not authenticated, and
    #  (2) Happy-path (authenticated) job gets are handled by
    #      MockProgramEnrollmentGetTests and MockCourseEnrollmentGetTests

    method = 'GET'
    path = 'jobs/a6393974-cf86-4e3b-a21a-d27e17932447'
