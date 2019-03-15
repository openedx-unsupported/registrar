""" Tests for the v0 API views. """

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
