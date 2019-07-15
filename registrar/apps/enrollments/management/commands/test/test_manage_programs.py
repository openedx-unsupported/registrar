""" Tests for manage_programs management command """
import ddt
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from mock import patch
from requests.exceptions import HTTPError

from registrar.apps.core.tests.factories import OrganizationFactory
from registrar.apps.enrollments.data import DiscoveryProgram
from registrar.apps.enrollments.models import Program
from registrar.apps.enrollments.tests.factories import ProgramFactory


@ddt.ddt
class TestManagePrograms(TestCase):
    """ Test manage_programs command """

    command = 'manage_programs'

    def setUp(self):
        super().setUp()
        discoveryprogram_patcher = patch.object(DiscoveryProgram, 'read_from_discovery')
        self.mock_get_discovery_program = discoveryprogram_patcher.start()
        self.addCleanup(discoveryprogram_patcher.stop)

    @classmethod
    def discovery_dict(cls, org_key, uuid):
        return {
            'authoring_organizations': [{'key': org_key}] if org_key else [],
            'uuid': uuid,
        }

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.org = OrganizationFactory()
        cls.other_org = OrganizationFactory()
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
        cls.english_discovery_program = cls.discovery_dict(cls.org.key, cls.english_uuid)
        cls.german_discovery_program = cls.discovery_dict(cls.other_org.key, cls.german_uuid)
        cls.russian_discovery_program = cls.discovery_dict(cls.other_org.key, cls.russian_uuid)
        cls.arabic_discovery_program = cls.discovery_dict(cls.org.key, cls.arabic_uuid)

    def assert_program(self, expected_uuid, expected_key, expected_org):
        """ Assert that a progam with the given fields exists """
        program = Program.objects.get(discovery_uuid=expected_uuid)
        self.assertEqual(program.key, expected_key)
        self.assertEqual(program.managing_organization, expected_org)

    def assert_program_nonexistant(self, expected_uuid):
        """ Assert that a progam with the given fields exists """
        with self.assertRaises(Program.DoesNotExist):
            Program.objects.get(discovery_uuid=expected_uuid)

    def _uuidkey(self, uuid, key):
        return "{}:{}".format(uuid, key)

    def test_create_program(self):
        self.mock_get_discovery_program.return_value = self.arabic_discovery_program
        self.assert_program_nonexistant(self.arabic_uuid)
        call_command(
            self.command,
            self._uuidkey(self.arabic_uuid, 'masters-in-arabic')
        )
        self.assert_program(self.arabic_uuid, 'masters-in-arabic', self.org)

    def test_create_programs(self):
        self.mock_get_discovery_program.side_effect = [
            self.arabic_discovery_program,
            self.russian_discovery_program,
        ]
        self.assert_program_nonexistant(self.arabic_uuid)
        self.assert_program_nonexistant(self.russian_uuid)
        call_command(
            self.command,
            self._uuidkey(self.arabic_uuid, 'masters-in-arabic'),
            self._uuidkey(self.russian_uuid, 'masters-in-russian'),
        )
        self.assert_program(self.arabic_uuid, 'masters-in-arabic', self.org)
        self.assert_program(self.russian_uuid, 'masters-in-russian', self.other_org)

    def test_modify_program(self):
        self.mock_get_discovery_program.return_value = self.english_discovery_program
        self.assert_program(self.english_uuid, 'masters-in-english', self.org)
        call_command(
            self.command,
            self._uuidkey(self.english_uuid, 'english-program'),
        )
        self.assert_program(self.english_uuid, 'english-program', self.org)

    def test_modify_program_do_nothing(self):
        self.mock_get_discovery_program.return_value = self.english_discovery_program
        self.assert_program(self.english_uuid, 'masters-in-english', self.org)
        call_command(self.command, self._uuidkey(self.english_uuid, 'masters-in-english'))
        self.assert_program(self.english_uuid, 'masters-in-english', self.org)

    def test_incorrect_format(self):
        # pylint: disable=deprecated-method
        with self.assertRaisesRegex(CommandError, 'incorrectly formatted argument'):
            call_command(self.command, 'mastersporgoramme')

    @ddt.data([], [{}])
    def test_no_authoring_orgs(self, authoring_organizations):
        self.mock_get_discovery_program.return_value = {
            'authoring_organizations': authoring_organizations,
            'uuid': self.english_uuid
        }
        # pylint: disable=deprecated-method
        with self.assertRaisesRegex(CommandError, 'No authoring org keys found for program'):
            call_command(self.command, self._uuidkey(self.english_uuid, 'english-program'))

    def test_org_not_found(self):
        self.mock_get_discovery_program.return_value = self.discovery_dict('nonexistant-org', self.english_uuid)
        # pylint: disable=deprecated-method
        with self.assertRaisesRegex(CommandError, 'None of the authoring organizations (.*?) were found'):
            call_command(self.command, self._uuidkey(self.english_uuid, 'english_program'))

    def test_load_from_disco_error(self):
        self.mock_get_discovery_program.side_effect = HTTPError()
        # pylint: disable=deprecated-method
        with self.assertRaisesRegex(CommandError, 'Could not read program'):
            call_command(self.command, self._uuidkey(self.english_uuid, 'english-program'))
