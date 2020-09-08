""" Management command to synchronize the organization and programs with Discovery service """
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from registrar.apps.core.api_client import DiscoveryServiceClient
from registrar.apps.core.models import (
    Organization,
    OrganizationGroup,
    Program,
    ProgramOrganizationGroup,
)
from registrar.apps.core.permissions import (
    OrganizationReadReportRole,
    ProgramReadReportRole,
)


logger = logging.getLogger(__name__)

PROGRAM_TYPES_TO_SYNC = ['micromasters', 'masters', 'professional-certificate', 'microbachelors', 'xseries']


class Command(BaseCommand):
    """class for command updates data from discovery service"""
    help = 'Adds Organizations and Programs based on data in Discovery Service. Will also update Organizations'

    @transaction.atomic
    def handle(self, *args, **options):
        """
        The main logic and entry point of the management command
        """
        # First make api call to discovery service to get list of organizations available
        self.sync_organizations()
        self.sync_programs(PROGRAM_TYPES_TO_SYNC)

    def sync_organizations(self):
        """
        Make API call to discovery service and get latest organizations list
        Then update the registrar organizations by adding new ones and
        updating the existing data
        """
        discovery_organizations = DiscoveryServiceClient.get_organizations()
        existing_org_dictionary = {}
        orgs_to_create = []
        orgs_to_update = []

        for org in Organization.objects.all():
            existing_org_dictionary[str(org.discovery_uuid)] = org

        logger.info('Start sync Discovery organizations...')
        for discovery_org in discovery_organizations:
            existing_org = existing_org_dictionary.get(discovery_org.get('uuid'))
            if not existing_org:
                orgs_to_create.append(Organization(
                    discovery_uuid=discovery_org.get('uuid'),
                    name=discovery_org.get('name'),
                    key=discovery_org.get('key'),
                ))
                logger.info('Creating %s', discovery_org.get('key'))
            elif existing_org.name != discovery_org.get('name') or existing_org.key != discovery_org.get('key'):
                existing_org.name = discovery_org.get('name')
                existing_org.key = discovery_org.get('key')
                orgs_to_update.append(existing_org)
                logger.info(
                    'Updating %s to have %s and %s',
                    existing_org.discovery_uuid,
                    existing_org.key,
                    existing_org.name,
                )

        if not orgs_to_create and not orgs_to_update:
            logger.info('Sync complete. No changes made to Registrar service')

        if orgs_to_create:
            # Bulk create those new organizations
            Organization.objects.bulk_create(orgs_to_create)
            self.create_org_groups(orgs_to_create)

        if orgs_to_update:
            # Bulk update those organizations needs updating
            Organization.objects.bulk_update(orgs_to_update, ['name', 'key'])
            self.update_org_groups(orgs_to_update)

        logger.info('Sync Organizations Success!')

    def sync_programs(self, program_types):
        """
        Make API call to discovery service and get latest programs list
        with pre-defined program-types
        Then update the registrar programs by adding new ones and
        updating the existing data
        """
        existing_org_dictionary = {}

        for org in Organization.objects.all():
            existing_org_dictionary[str(org.discovery_uuid)] = org

        discovery_programs = DiscoveryServiceClient.get_programs_by_types(program_types)
        existing_program_dictionary = {}
        programs_to_create = []

        for program in Program.objects.all():
            existing_program_dictionary[str(program.discovery_uuid)] = program

        logger.info('Start sync Discovery programs...')
        for discovery_program in discovery_programs:
            program_orgs_count = len(discovery_program.get('authoring_organizations'))
            if program_orgs_count > 1:
                logger.info(
                    'Encounterd program %s with multiple authoring orgs. Not updating registrar',
                    discovery_program.get('marketing_slug'),
                )
                continue

            cur_program = existing_program_dictionary.get(discovery_program.get('uuid'))
            if not cur_program:
                discovery_authoring_org = next(iter(discovery_program.get('authoring_organizations')), None)
                auth_org = None
                if discovery_authoring_org:
                    auth_org = existing_org_dictionary.get(discovery_authoring_org.get('uuid'))
                if auth_org:
                    programs_to_create.append(Program(
                        discovery_uuid=discovery_program.get('uuid'),
                        managing_organization=auth_org,
                        key=discovery_program.get('marketing_slug'),
                    ))
                    logger.info('Creating %s', discovery_program.get('marketing_slug'))

        if not programs_to_create:
            logger.info('Sync complete. No changes made to Registrar service')
            return

        # Bulk create those new programs
        Program.objects.bulk_create(programs_to_create)
        self.create_program_org_groups(programs_to_create)

        logger.info('Sync Programs Success!')

    def update_org_groups(self, updated_orgs):
        """
        Update the existing OrganizationGroups to match the up to date name of the organization
        """
        existing_org_groups = OrganizationGroup.objects.select_related('organization').filter(
            organization__discovery_uuid__in=[org.discovery_uuid for org in updated_orgs]
        )
        org_group_to_update = []
        for org_group in existing_org_groups:
            org_group.name = '{}_ReadOrganizationReports'.format(org_group.organization.key)
            org_group_to_update.append(org_group)

        OrganizationGroup.objects.bulk_update(org_group_to_update, ['name'])

    def create_org_groups(self, new_orgs):
        """
        Create new org groups based on the new orgs passed in.
        Then we save each new org group one by one. This is inefficient but necessary
        each new org group save() function includes a lot of logic we cannot bulk create
        """
        newly_created_orgs = Organization.objects.filter(
            discovery_uuid__in=[org.discovery_uuid for org in new_orgs]
        )
        for new_org in newly_created_orgs:
            new_org_group = OrganizationGroup(
                name='{}_ReadOrganizationReports'.format(new_org.key),
                organization=new_org,
                role=OrganizationReadReportRole.name,
            )
            new_org_group.save()
            logger.info(
                'Created new org group for org %s and permission %s. org_group_id: %s',
                new_org.key,
                OrganizationReadReportRole.name,
                new_org_group.id
            )

    def create_program_org_groups(self, new_programs):
        """
        Create new program org groups based on the new programs passed in.
        Then we save each new program org group one by one. This is inefficient but necessary
        each new program org group save() function includes a lot of logic we cannot bulk create
        """

        newly_created_programs = Program.objects.select_related('managing_organization').filter(
            discovery_uuid__in=[program.discovery_uuid for program in new_programs]
        )
        for new_program in newly_created_programs:
            new_program_org_group = ProgramOrganizationGroup(
                name='{}_{}_ReadProgramReports'.format(
                    new_program.managing_organization.key,
                    new_program.key,
                ),
                granting_organization=new_program.managing_organization,
                program=new_program,
                role=ProgramReadReportRole.name
            )
            new_program_org_group.save()
            logger.info(
                'Created new program_org group for org %s, program %s and permission %s. program_org_group_id: %s',
                new_program.managing_organization.key,
                new_program.key,
                ProgramReadReportRole.name,
                new_program_org_group.id
            )
