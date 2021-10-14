"""
Test module for api_client.py
"""
from posixpath import join as urljoin
from uuid import UUID

import ddt
import responses
from django.conf import settings
from django.test import TestCase

from ..api_client import DISCOVERY_API_TPL, DiscoveryServiceClient
from .utils import mock_oauth_login


@ddt.ddt
class DiscoveryServiceClientTestCase(TestCase):
    """
    Tests against the DiscoveryServiceClient object
    """
    organization_from_discovery = {
        'key': 'test_org',
        'name': 'org for testing',
        'uuid': '00000000-1111-3333-6666-777777777777',
    }
    another_organization_from_discovery = {
        'key': 'test_another_org',
        'name': 'another org for testing',
        'uuid': '00000000-1111-3333-6666-777777777788'
    }
    master_uuid = UUID("99999999-4444-2222-1111-000000000000")
    master_from_discovery = {
        'title': "Master's in CS",
        'marketing_url': "https://stem.edx.org/masters-in-cs",
        'type': "Masters",
        'uuid': str(master_uuid),
    }
    mm_program_from_discovery = {
        'title': "Micromaster tester program",
        'marketing_url': "https://stem.edx.org/mm-in-test",
        'type': "Micromasters",
        'uuid': "99999999-4444-2222-1111-000000000011",
    }
    program_types = ['Micromasters', 'Masters']

    def get_multi_response(self, results):
        """ Return the response that's paginated """
        return {
            'count': len(results),
            'next': None,
            'prev': None,
            'results': results
        }

    @mock_oauth_login
    @responses.activate
    @ddt.data(
        (200, master_from_discovery),
        (403, {'message': 'Permission Denied'})
    )
    @ddt.unpack
    def test_get_program(self, status, data_json):
        discovery_program_url = urljoin(
            settings.DISCOVERY_BASE_URL,
            DISCOVERY_API_TPL.format('programs', self.master_uuid)
        )
        responses.add(
            responses.GET,
            discovery_program_url,
            status=status,
            json=data_json,
        )
        program = DiscoveryServiceClient.get_program(self.master_uuid)
        if status == 200:
            self.assertEqual(program, data_json)
        else:
            self.assertIsNone(program)

    @mock_oauth_login
    @responses.activate
    @ddt.data(
        (200, [master_from_discovery, mm_program_from_discovery]),
        (403, [])
    )
    @ddt.unpack
    def test_get_programs_by_types(self, status, results):
        discovery_url = urljoin(
            settings.DISCOVERY_BASE_URL,
            DISCOVERY_API_TPL.format('programs', '')
        )
        discovery_url += f'?types={",".join(self.program_types)}&status=active'
        responses.add(
            responses.GET,
            discovery_url,
            status=status,
            json=self.get_multi_response(results),
        )
        programs = DiscoveryServiceClient.get_programs_by_types(self.program_types)
        if status == 200:
            self.assertEqual(results, programs)
        else:
            self.assertEqual([], programs)

    @mock_oauth_login
    @responses.activate
    @ddt.data(
        (200, [organization_from_discovery, another_organization_from_discovery]),
        (403, [])
    )
    @ddt.unpack
    def test_get_organizations(self, status, results):
        discovery_url = urljoin(
            settings.DISCOVERY_BASE_URL,
            DISCOVERY_API_TPL.format('organizations', '')
        )
        responses.add(
            responses.GET,
            discovery_url,
            status=status,
            json=self.get_multi_response(results),
        )
        orgs = DiscoveryServiceClient.get_organizations()
        if status == 200:
            self.assertEqual(results, orgs)
        else:
            self.assertEqual([], orgs)
