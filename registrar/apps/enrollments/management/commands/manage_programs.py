""" Management command to create or modify programs"""
import logging
import re
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from requests.exceptions import HTTPError

from registrar.apps.core.constants import ORGANIZATION_KEY_PATTERN
from registrar.apps.core.models import Organization, OrganizationGroup
from registrar.apps.core.permissions import ORGANIZATION_ROLES
from registrar.apps.enrollments.data import DiscoveryProgram
from registrar.apps.enrollments.models import Program


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    # pylint: disable=missing-docstring

    help = 'Creates or modifies Programs'

    def add_arguments(self, parser):
        parser.add_argument('org_key')
        parser.add_argument(
            'uuidkeys',
            nargs='*',
            help='specify the programs to create or modify, in the format <discovery_uuid>:<program_key>',
        )

    # pylint: disable=arguments-differ
    @transaction.atomic
    def handle(self, org_key, uuidkeys, *args, **options):
        uuidkeys = self.parse_uuidkeys(uuidkeys)
        for uuidkey in uuidkeys:
            program_dict
            self.create_or_modify_program(org, *uuidkey)

    def parse_uuidkeys(self, uuidkeys):
        result = []
        for uuidkey in uuidkeys:
            split_args = uuidkey.split(':')
            if len(split_args) != 2:
                message = ('incorrectly formatted argument {}, '
                           'must be in form <program uuid>:<program key>').format(uuidkey)
                raise CommandError(message)
            result.append((split_args[0], split_args[1]))
        return result

    def lookup_org(self, org_key):
        try:
            return Organization.objects.get(key=org_key)
        except Organization.DoesNotExist:
            raise CommandError('No organization found for key {}'.format(org_key))

    def create_or_modify_program(self, org, program_uuid, program_key):
        import pdb;pdb.set_trace()
        discovery_program = self.get_program_from_discovery(program_uuid)
        program, created = Program.objects.get_or_create(
            discovery_uuid=discovery_program.uuid,
            defaults={
                'managing_organization': org,
                'key': program_key,
            },
        )
        if not created:
            if program.managing_organization != org:
                raise CommandError('Existing program uuid={} key={} is not managed by {}'.format(
                    discovery_program.uuid, program.key, org
                ))
            if program.key != program_key:
                program.key = program_key
                program.save()
        verb = 'Created' if created else 'Modified existing'
        logger.info('{} program (key={} uuid={} managing_org={})'.format(verb, program_key, program_uuid, org.key))

    def get_program_from_discovery(self, program_uuid):
        try:
            discovery_program = DiscoveryProgram.load_from_discovery(program_uuid)
        except HTTPError as e:
            raise CommandError('Unable to load program {} from course-discovery: {}'.format(program_uuid, e))
        logger.info('Loaded program {} from discovery'.format(program_uuid))
        return discovery_program
    
    def get_org_keys(self, program_dict):
        result = []
        authoring_orgs = program_dict.get('authoring_organizations', [])
        for authoring_org in authoring_orgs:
            if 'key' in authoring_org:
                result.append(authoring_org['key'])
        if not result:
            raise CommandError('No authoring orgs keys found for program {}'.format(program_dict.get('uuid')))
        return result
