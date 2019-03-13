""" Tests for API views. """

import ddt
import mock
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
