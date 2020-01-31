""" Test API Serializers """
import mock
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import TestCase
from django.test.client import RequestFactory

from registrar.apps.api.serializers import ProgramSerializer
from registrar.apps.core.constants import PROGRAM_CACHE_KEY_TPL
from registrar.apps.core.data import DiscoveryProgram
from registrar.apps.core.permissions import (
    APIReadMetadataPermission,
    APIWriteEnrollmentsPermission,
)
from registrar.apps.core.tests.factories import (
    OrganizationFactory,
    ProgramFactory,
)


class ProgramSerializerTests(TestCase):
    """ Tests the ProgramSerializer """
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
            DiscoveryProgram.from_json(
                self.program.discovery_uuid,
                {
                    'title': 'test-program',
                    'type': 'masters',
                    'curricula': [],
                }
            )
        )

    @mock.patch('registrar.apps.api.serializers.get_user_api_permissions')
    def test_get_user_permissions(self, fake_get_perms):
        """
        Program permissions should be populated with the union of all
        permissions assigned at that program and its managing organization
        """
        fake_get_perms.side_effect = [
            set([APIWriteEnrollmentsPermission]),  # mocked permissions on program
            set([APIReadMetadataPermission]),  # mocked permissions on org
        ]
        program = ProgramSerializer(
            self.program,
            context={
                'request': self.request
            }
        ).data
        self.assertListEqual(
            program.get('permissions'),
            [APIReadMetadataPermission.name, APIWriteEnrollmentsPermission.name]
        )

    def test_permissions_no_request_context(self):
        """
        Serializer should return an empty list for permissions if invoked
        without a request context
        """
        program = ProgramSerializer(self.program).data
        self.assertListEqual(program.get('permissions'), [])
