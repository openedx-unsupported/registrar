""" Test API Serializers """
import mock
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import TestCase
from django.test.client import RequestFactory

from registrar.apps.api.serializers import DetailedProgramSerializer
from registrar.apps.core.constants import PROGRAM_CACHE_KEY_TPL
from registrar.apps.core.permissions import (
    API_READ_METADATA,
    API_WRITE_ENROLLMENTS,
)
from registrar.apps.core.tests.factories import (
    OrganizationFactory,
    ProgramFactory,
)


class DetailedProgramSerializerTests(TestCase):
    """ Tests the DetailedProgramSerializer """
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.org = OrganizationFactory()
        cls.program = ProgramFactory(managing_organization=cls.org)

        cls.request = RequestFactory().get('/api/v1/programs')
        cls.request.user = AnonymousUser()

    def setUp(self):
        super().setUp()

        cache.set(
            PROGRAM_CACHE_KEY_TPL.format(uuid=self.program.discovery_uuid),
            {
                'title': 'test-program',
                'type': 'Masters',
                'curricula': [],
            }
        )

    @mock.patch('registrar.apps.api.serializers.get_effective_user_program_api_permissions')
    def test_serializer(self, fake_get_perms):
        """
        Test that the serializer should return output of get_effective_user_program_api_permissions
        for permissions.
        """
        fake_get_perms.return_value = {
            API_WRITE_ENROLLMENTS,
            API_READ_METADATA,
        }
        program = DetailedProgramSerializer(
            self.program,
            context={
                'request': self.request
            }
        ).data
        self.assertListEqual(
            program.get('permissions'),
            [API_READ_METADATA.name, API_WRITE_ENROLLMENTS.name]
        )

    def test_permissions_no_request_context(self):
        """
        Serializer should return an empty list for permissions if invoked
        without a request context
        """
        program = DetailedProgramSerializer(self.program).data
        self.assertListEqual(program.get('permissions'), [])
