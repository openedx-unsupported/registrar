""" Management command to create or modify programs"""
import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from slugify import slugify

from registrar.apps.core.discovery_cache import ProgramDetails
from registrar.apps.core.models import Organization, Program


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """class for management command to create or modify programs"""
    help = 'Creates or modifies Programs'

    def add_arguments(self, parser):
        parser.add_argument(
            'uuidkeys',
            help=('specify the programs to create or modify, in a single comma '
                  'separated string, in the format <discovery_uuid>[:<program_key>]')
        )

    # pylint: disable=arguments-differ
    @transaction.atomic
    def handle(self, uuidkeys, *args, **options):
        uuidkeys = self.parse_uuidkeys(uuidkeys)
        for uuidkey in uuidkeys:
            discovery_details = ProgramDetails(uuidkey[0]).raw_data
            if not discovery_details:
                raise CommandError('Could not read program from course-discovery; aborting')
            org = self.get_or_create_orgs(discovery_details)
            self.create_or_modify_program(org, discovery_details, *uuidkey)

    def parse_uuidkeys(self, uuidkeys):  # pylint: disable=missing-function-docstring
        result = []
        for uuidkey in uuidkeys.split(','):
            split_args = uuidkey.split(':')
            if len(split_args) == 1:
                result.append((uuidkey, None))
            elif len(split_args) == 2:
                result.append((split_args[0], split_args[1]))
            else:
                message = (
                    f'incorrectly formatted argument {uuidkey}, '
                    'must be in form <program uuid>:<program key> or <program_uuid>'
                )
                raise CommandError(message)
        return result

    def get_or_create_orgs(self, program_details):
        """
        From fetched program details, extract discovery information
        about authoring organizations and return one matching/newly
        created registrar org.

        We return the last authoring org. so that as many
        organizations are created as possible, since this leads to
        more consistent results.
        """
        last_seen_authoring_org = None
        authoring_orgs = program_details.get('authoring_organizations', [])
        for authoring_org in authoring_orgs:
            if 'key' in authoring_org:
                last_seen_authoring_org = self.get_or_create_org_from_discovery_data(authoring_org)
        if not last_seen_authoring_org:
            raise CommandError('No authoring organization could be found or created')
        return last_seen_authoring_org

    def get_or_create_org_from_discovery_data(self, discovery_org_data):
        """
        From fetched org data, get or create a matching organization
        """
        org_key = discovery_org_data['key']
        org, created = Organization.objects.get_or_create(
            key=org_key,
            defaults={'discovery_uuid': discovery_org_data['uuid']},
        )
        if created:
            logger.info('Org %(org_key)s not found in registrar, creating', {'org_key': org_key})
        else:
            logger.info('Using %(org)r as program organization', {'org': org})
        return org

    # pylint: disable=missing-function-docstring
    def create_or_modify_program(self, org, program_details, program_uuid, program_key):
        program, created = Program.objects.get_or_create(
            discovery_uuid=program_uuid,
            defaults={
                'managing_organization': org,
                'key': program_key or slugify(program_details.get('marketing_slug')),
            },
        )
        if (not created) and program_key and (program.key != program_key):
            program.key = program_key
            program.save()
        verb = 'Created' if created else 'Modified existing'
        logger.info(
            '%(verb)s program (key=%(program_key)s uuid=%(uuid)s managing_org=%(org_key)s)',
            {'verb': verb, 'program_key': program_key, 'uuid': program_uuid, 'org_key': org.key}
        )
