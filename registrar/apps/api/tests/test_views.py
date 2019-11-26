""" Tests for non-api views """
import json

from guardian.shortcuts import assign_perm
from rest_framework.test import APITestCase

from registrar.apps.core import permissions as perms
from registrar.apps.core.tests.factories import (
    USER_PASSWORD,
    OrganizationFactory,
    OrganizationGroupFactory,
    ProgramFactory,
    UserFactory,
)


class APIDocViewTest(APITestCase):
    """ Tests for accessing api-docs """
    path = '/api-docs/'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = UserFactory()
        assign_perm(perms.ORGANIZATION_WRITE_ENROLLMENTS, cls.admin_user)

        cls.org = OrganizationFactory(name='Test Organization')
        cls.program = ProgramFactory(
            managing_organization=cls.org,
        )
        cls.org_admin_group = OrganizationGroupFactory(
            organization=cls.org,
            role=perms.OrganizationReadWriteEnrollmentsRole.name
        )
        cls.org_admin = UserFactory()
        cls.org_admin.groups.add(cls.org_admin_group)  # pylint: disable=no-member

        cls.no_perms_user = UserFactory()

    def test_access_apidocs_edxadmin(self):
        self.access_apidocs(self.admin_user, True)

    def test_access_apidocs_orgadmin(self):
        self.access_apidocs(self.org_admin, True)

    def test_access_apidocs_noperms(self):
        self.access_apidocs(self.no_perms_user, True)

    def test_unauthenticated(self):
        self.access_apidocs(None, False)

    def access_apidocs(self, user, expected_paths):
        """ Helper method for accessing apidocs and making assertions """
        if user:
            self.client.login(username=user.username, password=USER_PASSWORD)
        else:
            self.client.logout()
        response = self.client.get(self.path)
        self.assertEqual(200, response.status_code)
        self.assert_paths(response, expected_paths)

    def assert_paths(self, response, expected_paths):
        """ Assert the presence of 'paths' in the response context """
        spec = None
        for context in response.context:  # pragma: no branch
            if 'spec' in context:  # pragma: no branch
                spec = context['spec']
                break
        self.assertIsNotNone(spec)
        spec = json.loads(spec)
        paths = spec.get('paths')
        self.assertIsNotNone(paths)
        self.assertEqual(expected_paths, bool(paths))
