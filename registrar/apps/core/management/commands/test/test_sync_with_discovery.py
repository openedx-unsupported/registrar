""" Tests for sync_with_discovery management command """
from unittest.mock import patch

import ddt
from django.core.management import call_command
from django.db.utils import IntegrityError
from django.test import TestCase

from registrar.apps.core.api_client import DiscoveryServiceClient
from registrar.apps.core.models import (
    Organization,
    OrganizationGroup,
    Program,
    ProgramOrganizationGroup,
)
from registrar.apps.core.permissions import (
    OrganizationReadEnrollmentsRole,
    OrganizationReadReportRole,
    ProgramReadReportRole,
)
from registrar.apps.core.tests.factories import (
    OrganizationFactory,
    OrganizationGroupFactory,
    ProgramFactory,
    ProgramOrganizationGroupFactory,
)


class TestSyncWithDiscoveryCommandBase(TestCase):
    """ Test sync_with_discovery command """

    command = 'sync_with_discovery'

    def setUp(self):
        super().setUp()
        get_organizations_patcher = patch.object(DiscoveryServiceClient, 'get_organizations')
        get_programs_by_types_patcher = patch.object(DiscoveryServiceClient, 'get_programs_by_types')
        self.mock_get_organizations_patcher = get_organizations_patcher.start()
        self.mock_get_programs_by_types_patcher = get_programs_by_types_patcher.start()
        self.addCleanup(get_organizations_patcher.stop)
        self.addCleanup(get_programs_by_types_patcher.stop)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.org = OrganizationFactory()
        cls.other_org = OrganizationFactory()
        cls.org_read_reports_group = OrganizationGroupFactory(
            name=f'{cls.org.key}_ReadOrganizationReports',
            organization=cls.org,
            role=OrganizationReadReportRole.name
        )
        cls.org_read_enrollments = OrganizationGroupFactory(
            name=f'{cls.org.key}_ReadEnrollments',
            organization=cls.org,
            role=OrganizationReadEnrollmentsRole.name
        )
        cls.other_org_read_reports_group = OrganizationGroupFactory(
            name=f'{cls.other_org.key}_ReadOrganizationReports',
            organization=cls.other_org,
            role=OrganizationReadReportRole.name
        )
        cls.other_org_read_enrollments = OrganizationGroupFactory(
            name=f'{cls.other_org.key}_ReadEnrollments',
            organization=cls.other_org,
            role=OrganizationReadEnrollmentsRole.name
        )


class TestSyncOrganizationsWithDiscoveryCommand(TestSyncWithDiscoveryCommandBase):
    """
    All the test cases for making sure Organizations objects are
    properly created or updated based on data from Discovery service
    """
    @classmethod
    def discovery_organization_dict(cls, uuid, key, name):
        return {
            'key': key,
            'uuid': str(uuid),
            'name': name,
        }

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.new_discovery_org_uuid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        cls.new_discovery_organization = cls.discovery_organization_dict(
            cls.new_discovery_org_uuid,
            'letterX',
            'Letter University',
        )
        cls.updating_discovery_organization = cls.discovery_organization_dict(
            cls.org.discovery_uuid,
            'updateX',
            'Updating University',
        )
        cls.discovery_org = cls.discovery_organization_dict(
            cls.org.discovery_uuid,
            cls.org.key,
            cls.org.name,
        )
        cls.discovery_other_org = cls.discovery_organization_dict(
            cls.other_org.discovery_uuid,
            cls.other_org.key,
            cls.other_org.name,
        )

    def assert_org_nonexistant(self, expected_uuid):
        """
        Make sure the passed in org uuids do not exist in the database
        """
        with self.assertRaises(Organization.DoesNotExist):
            Organization.objects.get(discovery_uuid=expected_uuid)

    def assert_organizations(self, orgs_expected, query_count_expected):
        """
        Make sure the database state is what is expected.
        Also ensure the query count of the management command is expected
        """
        self.mock_get_organizations_patcher.return_value = orgs_expected
        self.mock_get_programs_by_types_patcher.return_value = []
        with self.assertNumQueries(query_count_expected):
            call_command(self.command)

        for org in orgs_expected:
            self.assertTrue(Organization.objects.get(discovery_uuid=org['uuid'], key=org['key'], name=org['name']))

            # check that read report role exists
            existing_org_report_group = OrganizationGroup.objects.get(
                organization__discovery_uuid=org['uuid'],
                role=OrganizationReadReportRole.name
            )
            self.assertTrue(existing_org_report_group)
            expected_org_group_name = f'{org["key"]}_ReadOrganizationReports'
            self.assertEqual(existing_org_report_group.name, expected_org_group_name)

    def test_sync_organization_create_and_update(self):
        orgs_to_sync = [
            self.new_discovery_organization,
            self.updating_discovery_organization,
            self.discovery_other_org,
        ]
        self.assert_org_nonexistant(self.new_discovery_org_uuid)

        self.assert_organizations(orgs_to_sync, 49)

    def test_sync_organization_create_only(self):
        other_new_org_uuid = '99999999-2222-2222-3333-555555555555'
        other_new_org = self.discovery_organization_dict(
            other_new_org_uuid,
            'languageX',
            'Language University',
        )
        orgs_to_sync = [
            self.new_discovery_organization,
            other_new_org,
            self.discovery_other_org,
            self.discovery_org,
        ]
        self.assert_org_nonexistant(self.new_discovery_org_uuid)
        self.assert_org_nonexistant(other_new_org_uuid)

        self.assert_organizations(orgs_to_sync, 42)

    def test_sync_organization_update_only(self):
        orgs_to_sync = [
            self.updating_discovery_organization,
            self.discovery_other_org
        ]

        self.assert_organizations(orgs_to_sync, 32)

    def test_sync_no_change(self):
        orgs_to_sync = [
            self.discovery_org,
            self.discovery_other_org,
        ]
        self.assert_organizations(orgs_to_sync, 9)

    def test_success_output(self):
        orgs_to_sync = [
            self.new_discovery_organization,
            self.updating_discovery_organization,
            self.discovery_other_org,
        ]
        self.mock_get_organizations_patcher.return_value = orgs_to_sync
        self.mock_get_programs_by_types_patcher.return_value = []
        with patch('registrar.apps.core.management.commands.sync_with_discovery.logger') as mock_logger:
            call_command(self.command)
            mock_logger.info.assert_called_with('Sync with Discovery Service complete!')


@ddt.ddt
class TestSyncProgramsWithDiscoveryCommand(TestSyncWithDiscoveryCommandBase):
    """
    All the test cases for making sure Program objects are
    properly created based on data from Discovery service
    """
    @classmethod
    def discovery_program_dict(cls, org_uuid, uuid, slug):
        return {
            'authoring_organizations': [{'uuid': str(org_uuid)}] if org_uuid else [],
            'uuid': uuid,
            'marketing_slug': slug,
        }

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.english_uuid = '11111111-2222-3333-4444-555555555555'
        cls.german_uuid = '22222222-2222-3333-4444-555555555555'
        cls.russian_uuid = '33333333-2222-3333-4444-555555555555'
        cls.arabic_uuid = '44444444-2222-3333-4444-555555555555'

        cls.english_program = ProgramFactory(
            key='masters-in-english',
            discovery_uuid=cls.english_uuid,
            managing_organization=cls.org
        )
        cls.german_program = ProgramFactory(
            key='masters-in-german',
            discovery_uuid=cls.german_uuid,
            managing_organization=cls.other_org
        )
        cls.english_program_read_report_group = ProgramOrganizationGroupFactory(
            name=f'{cls.org.key}_{cls.english_program.key}_ReadProgramReports',
            program=cls.english_program,
            granting_organization=cls.org,
            role=ProgramReadReportRole.name,
        )
        cls.german_program_read_report_group = ProgramOrganizationGroupFactory(
            name=f'{cls.other_org.key}_{cls.german_program.key}_ReadProgramReports',
            program=cls.german_program,
            granting_organization=cls.other_org,
            role=ProgramReadReportRole.name,
        )
        cls.english_discovery_program = cls.discovery_program_dict(
            cls.org.discovery_uuid,
            cls.english_uuid,
            'masters-in-english'
        )
        cls.german_discovery_program = cls.discovery_program_dict(
            cls.other_org.discovery_uuid,
            cls.german_uuid,
            'masters-in-german'
        )
        cls.russian_discovery_program = cls.discovery_program_dict(
            cls.other_org.discovery_uuid,
            cls.russian_uuid,
            'russian-slug'
        )
        cls.arabic_discovery_program = cls.discovery_program_dict(
            cls.org.discovery_uuid,
            cls.arabic_uuid,
            'arabic-slug'
        )

    def assert_program_nonexistant(self, expected_uuid):
        """ Assert that a progam with the given fields do not exists """
        with self.assertRaises(Program.DoesNotExist):
            Program.objects.get(discovery_uuid=expected_uuid)

    def assert_programs(self, programs_to_sync, query_count_expected, programs_expected=None):
        """
        Make sure the database state is what is expected.
        Also ensure the query count of the management command is expected
        """
        if not programs_expected:
            programs_expected = programs_to_sync
        self.mock_get_organizations_patcher.return_value = []
        self.mock_get_programs_by_types_patcher.return_value = programs_to_sync
        with self.assertNumQueries(query_count_expected):
            call_command(self.command)

        for program in programs_expected:
            created_program = Program.objects.get(discovery_uuid=program['uuid'])
            self.assertTrue(created_program)
            self.assertTrue(
                ProgramOrganizationGroup.objects.get(
                    program=created_program,
                    granting_organization=created_program.managing_organization,
                    role=ProgramReadReportRole.name,
                )
            )

    def test_sync_programs_create_with_different_slugs(self):
        updated_discovery_program = self.discovery_program_dict(
            self.german_program.managing_organization.discovery_uuid,
            self.german_program.discovery_uuid,
            'updated-marketing-slug',
        )
        programs_to_sync = [
            self.russian_discovery_program,
            self.arabic_discovery_program,
            self.english_discovery_program,
            updated_discovery_program
        ]
        self.assert_program_nonexistant(self.russian_discovery_program.get('uuid'))
        self.assert_program_nonexistant(self.arabic_discovery_program.get('uuid'))

        self.assert_programs(programs_to_sync, 42)

    def test_sync_programs_create_with_non_slug_marketing_slug(self):
        """ Discovery keys that are not valid slugs should be slugified """
        long_slug = (
            'masters/online-masters/masters-in-business/'
            'university-of-open-edx-online-masters-in-'
            'business-analytics-statistics-and-computer-science-and-data-science-and-data-anlytics'
        )
        discovery_program = self.discovery_program_dict(
            self.org.discovery_uuid,
            '77777777-2222-3333-4444-555555555555',
            long_slug,
        )
        programs_to_sync = [
            discovery_program,
        ]
        self.assert_programs(programs_to_sync, 26)
        created_program = Program.objects.get(discovery_uuid=discovery_program['uuid'])
        self.assertEqual(
            created_program.key,
            'university-of-open-edx-online-masters-in-business-analytics-statistics-and-computer-science-and-data'
        )

    def test_sync_programs_multiple_non_slug_marketing_slug(self):
        """
        Discovery keys that are not valid slugs should be slugified, and job should fail if keys are not unique
        """
        discovery_program = self.discovery_program_dict(
            self.org.discovery_uuid,
            '77777777-2222-3333-4444-555555555555',
            'marketing/online-masters/this-is-the-program-name',
        )
        another_discovery_program = self.discovery_program_dict(
            self.org.discovery_uuid,
            '77777777-2222-3333-4444-666666666666',
            'marketing/masters/this-is-the-program-name',
        )
        programs_to_sync = [
            discovery_program,
            another_discovery_program,
        ]

        with self.assertRaises(IntegrityError):
            self.assert_programs(programs_to_sync, 26)

    def test_sync_programs_with_different_slugs(self):
        updated_discovery_program = self.discovery_program_dict(
            self.german_program.managing_organization.discovery_uuid,
            self.german_program.discovery_uuid,
            'updated-marketing-slug'
        )
        programs_to_sync = [
            self.english_discovery_program,
            updated_discovery_program
        ]
        self.assert_programs(programs_to_sync, 9)

    def test_sync_programs_create_only(self):
        programs_to_sync = [
            self.russian_discovery_program,
            self.arabic_discovery_program,
            self.english_discovery_program,
        ]
        self.assert_program_nonexistant(self.russian_discovery_program.get('uuid'))
        self.assert_program_nonexistant(self.arabic_discovery_program.get('uuid'))

        self.assert_programs(programs_to_sync, 42)

    def test_sync_programs_missing_role(self):
        """ program already exists but no reporting role has been created """
        spanish_program = ProgramFactory(
            key='masters-in-spanish',
            discovery_uuid='77777777-2222-3333-4444-555555555555',
            managing_organization=self.org
        )
        spanish_discovery_program = self.discovery_program_dict(
            self.org.discovery_uuid,
            spanish_program.discovery_uuid,
            spanish_program.key,
        )

        programs_to_sync = [
            spanish_discovery_program
        ]
        self.assert_programs(programs_to_sync, 25)

    def test_sync_programs_update_role(self):
        """ program already exists but the reporting role has a nonstandard name """
        spanish_program = ProgramFactory(
            key='masters-in-spanish',
            discovery_uuid='77777777-2222-3333-4444-555555555555',
            managing_organization=self.org
        )
        spanish_discovery_program = self.discovery_program_dict(
            self.org.discovery_uuid,
            spanish_program.discovery_uuid,
            spanish_program.key,
        )
        ProgramOrganizationGroupFactory(
            name='BadNameReadReports',
            program=spanish_program,
            granting_organization=self.org,
            role=ProgramReadReportRole.name,
        )

        programs_to_sync = [
            spanish_discovery_program
        ]
        self.assert_programs(programs_to_sync, 31)

    def test_sync_programs_no_change(self):
        programs_to_sync = [
            self.english_discovery_program,
            self.german_discovery_program,
        ]
        self.assert_programs(programs_to_sync, 9)

    @ddt.data(
        '44444444-2222-3333-4444-000000000000',
        None
    )
    def test_sync_programs_bad_org(self, org_uuid):
        no_org_program = self.discovery_program_dict(
            org_uuid,
            self.russian_uuid,
            'no-org-program',
        )
        programs_to_sync = [
            self.english_discovery_program,
            no_org_program,
        ]
        self.assert_program_nonexistant(no_org_program.get('uuid'))
        self.assert_programs(programs_to_sync, 9, [self.english_discovery_program])
        self.assert_program_nonexistant(no_org_program.get('uuid'))

    def test_sync_programs_multiple_authoring_orgs(self):
        new_program_uuid_string = '77777777-2222-3333-4444-555555555555'
        new_program_to_create = {
            'authoring_organizations': [
                {'uuid': str(self.org.discovery_uuid)},
                {'uuid': str(self.other_org.discovery_uuid)},
            ],
            'uuid': new_program_uuid_string,
            'marketing_slug': 'multi_orgs_program',
        }
        programs_to_sync = [
            self.german_discovery_program,
            self.english_discovery_program,
        ]
        self.assert_programs(programs_to_sync + [new_program_to_create], 9, programs_to_sync)
        self.assert_program_nonexistant(new_program_uuid_string)
