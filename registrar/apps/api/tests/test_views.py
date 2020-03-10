"""
Tests for non-versioned views.
"""
from rest_framework.test import APITestCase

from registrar.apps.core.tests.factories import USER_PASSWORD, UserFactory


class APIDocViewTest(APITestCase):
    """ Tests for accessing api-docs """
    path = '/api-docs/'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()

    def test_docs_access_logged_out(self):
        return self.client.get('/api-docs').status_code == 200

    def test_docs_access_logged_in(self):
        self.client.login(username=self.user.username, password=USER_PASSWORD)
        return self.client.get('/api-docs').status_code == 200
