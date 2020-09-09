""" Tests for API views. """
import ddt

from registrar.apps.api.tests.mixins import AuthRequestMixin
from registrar.apps.api.v1.tests.test_views import RegistrarAPITestCase


@ddt.ddt
class ViewMethodNotSupportedTests(RegistrarAPITestCase, AuthRequestMixin):
    """ Tests for the case if user requested a not supported HTTP method """

    api_root = '/api/v3/'
    TEST_PROGRAM_URL_TPL = 'http://registrar-test-data.edx.org/{key}/'
    method = 'DELETE'
    path = 'programs'

    @ddt.data(
        ('programs', 'ProgramListPaginationView'),
    )
    @ddt.unpack
    def test_not_supported_http_method(self, path, view_name):
        self.mock_logging.reset_mock()
        self.path = path
        response = self.request(self.method, path, self.edx_admin)
        self.mock_logging.error.assert_called_once_with(
            'Segment tracking event name not found for request method %s on view %s',
            self.method,
            view_name,
        )
        self.assertEqual(response.status_code, 405)


@ddt.ddt
class ProgramListPaginationViewTests(RegistrarAPITestCase, AuthRequestMixin):
    """ Tests for the /api/v3/programs?org={org_key} endpoint with pagination """

    api_root = '/api/v3/'
    TEST_PROGRAM_URL_TPL = 'http://registrar-test-data.edx.org/{key}/'
    method = 'GET'
    path = 'programs'
    event = 'registrar.v3.list_programs'

    def test_valid_pagination(self):
        with self.assert_tracking(user=self.edx_admin):
            response = self.get('programs?page_size=1&page=2', self.edx_admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data['next'], 'http://testserver/api/v3/programs?page=3&page_size=1')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['count'], 4)

    def test_pagination_with_large_page_size(self):
        with self.assert_tracking(user=self.edx_admin):
            response = self.get('programs?page_size=100&page=1', self.edx_admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data['next'], None)
        self.assertEqual(len(response.data['results']), 4)
        self.assertEqual(response.data['count'], 4)

    def test_pagination_with_other_user(self):
        with self.assert_tracking(user=self.stem_user):
            response = self.get('programs?page_size=1&page=2', self.stem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data['next'], None)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['count'], 2)

    def test_default_pagination(self):
        with self.assert_tracking(user=self.edx_admin):
            response = self.get('programs?', self.edx_admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(len(response.data['results']), 4)
        self.assertEqual(response.data['count'], 4)

    def test_404_with_string_pagination_arguments(self):
        with self.assert_tracking(user=self.edx_admin, status_code=404):
            response = self.get('programs?page=foo&page_size=2', self.edx_admin)
        self.assertEqual(response.status_code, 404)

    def test_404_with_invalid_pagination_arguments(self):
        with self.assert_tracking(user=self.edx_admin, status_code=404):
            response = self.get('programs?page_size=100&page=2', self.edx_admin)
        self.assertEqual(response.status_code, 404)
