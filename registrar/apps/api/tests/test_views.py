"""
Tests for non-versioned views.
"""
from rest_framework.test import APITestCase

from registrar.apps.core.tests.factories import USER_PASSWORD, UserFactory


class APIDocViewTest(APITestCase):
    """
    Tests for accessing API docs generated using edx-api-doc-tools.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()

    def assert_can_load_docs_page(self):
        """
        Assert that we can load /api-docs as expected.

        Because most of the docs page is loaded via AJAX, we can't make many assertions
        about the api-docs page. The best we can do is:
        * Assert that the response was 200 OK.
        * Assert that a statically-rendered string, such as the API title,
          is in the page.
        """
        docs_response = self.client.get('/api-docs', follow=True)
        assert docs_response.status_code == 200
        docs_response_text = docs_response.content.decode('utf-8')
        assert "Registrar API - Online Documentation" in docs_response_text

    def test_docs_access_logged_out(self):
        self.assert_can_load_docs_page()

    def test_docs_access_logged_in(self):
        self.client.login(username=self.user.username, password=USER_PASSWORD)
        self.assert_can_load_docs_page()
