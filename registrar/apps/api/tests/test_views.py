"""
Tests for non-versioned views.
"""
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


class OldAPIDocViewTest(APITestCase):
    """
    Tests for accessing API docs hand-written in api.yaml file and
    served up by Swagger.
    """
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
        cls.org_admin.groups.add(cls.org_admin_group)

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


class NewAPIDocViewTest(APITestCase):
    """
    Tests for accessing API docs generated using edx-api-doc-tools.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()

    def assert_can_load_docs_page(self):
        """
        Assert that we can load /api-docs/new as expected.

        Because most of the docs page is loaded via AJAX, we can't make many assertions
        about the api-docs page. The best we can do is:
        * Assert that the response was 200 OK.
        * Assert that a statically-rendered string, such as the API title,
          is in the page. We choose the API title because the specific title we are
          checking for is *not* in the old API docs, so we are sure that we aren't
          just loading the old API docs when tests pass.
        """
        docs_response = self.client.get('/api-docs/new', follow=True)
        assert docs_response.status_code == 200
        docs_response_text = docs_response.content.decode('utf-8')
        assert "Registrar API - Online Documentation" in docs_response_text

    def test_docs_access_logged_out(self):
        self.assert_can_load_docs_page()

    def test_docs_access_logged_in(self):
        self.client.login(username=self.user.username, password=USER_PASSWORD)
        self.assert_can_load_docs_page()
