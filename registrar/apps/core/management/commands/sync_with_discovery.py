""" Management command to synchronize the organization and programs with Discovery service """
import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from slugify import slugify

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
        self.sync_organizations()
        self.sync_programs(PROGRAM_TYPES_TO_SYNC)

        self.sync_org_groups()
        self.sync_program_org_groups()

        # load bearing log message. edx.org monitors for this log message
        # to know when the sync has run successfully
        logger.info('Sync with Discovery Service complete!')

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
                org = Organization(
                    discovery_uuid=discovery_org.get('uuid'),
                    name=discovery_org.get('name'),
                    key=discovery_org.get('key'),
                )
                orgs_to_create.append(org)
                logger.info('Creating %s with uuid %s', discovery_org.get('key'), discovery_org.get('uuid'))
            else:
                if existing_org.name != discovery_org.get('name') or existing_org.key != discovery_org.get('key'):
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
            logger.info('Sync organizations complete. No changes made to Registrar service')

        if orgs_to_create:
            # Bulk create those new organizations
            Organization.objects.bulk_create(orgs_to_create)

        if orgs_to_update:
            # Bulk update those organizations needs updating
            Organization.objects.bulk_update(orgs_to_update, ['name', 'key'])

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
                    # key from disco is not guaranteed to be a valid slugfield.
                    # The current key pattern in disco looks something like /masters/program/name-of-the-program,
                    # so we should only use the piece of the marketing slug that contains the name of the program.
                    program_key = slugify(
                        discovery_program.get('marketing_slug').split('/')[-1],
                        max_length=100,
                    )
                    programs_to_create.append(Program(
                        discovery_uuid=discovery_program.get('uuid'),
                        managing_organization=auth_org,
                        key=program_key,
                    ))
                    logger.info(
                        'Creating %s with uuid %s',
                        program_key,
                        discovery_authoring_org.get('uuid')
                    )

        # Bulk create those new programs
        Program.objects.bulk_create(programs_to_create)

        if not programs_to_create:
            logger.info('Sync programs complete. No changes made to Registrar service')

        logger.info('Sync Programs Success!')

    def sync_org_groups(self):
        """
        All organizations should have the ReadOrganizationReports group with a consistent naming convention.
        Create or update the groups for all organizations missing this default group.
        Then we save each new org group one by one. This is inefficient but necessary
        each new org group save() function includes a lot of logic we cannot bulk create
        """
        read_reports_groups = {}
        for group in OrganizationGroup.objects.select_related('organization').filter(
            role=OrganizationReadReportRole.name
        ):
            read_reports_groups[group.organization.key] = group

        for org in Organization.objects.all():
            name = f'{org.key}_ReadOrganizationReports'

            created, updated = (False, False)
            org_group = read_reports_groups.get(org.key)

            if not org_group:
                org_group = OrganizationGroup(
                    name=name,
                    organization=org,
                    role=OrganizationReadReportRole.name,
                )
                created = True
            elif org_group.name != name:
                org_group.name = name
                updated = True

            if created or updated:
                org_group.save()
                logger.info(
                    '%s org group for org %s and permission %s. org_group_id: %s',
                    'Created' if created else 'Updated',
                    org.key,
                    OrganizationReadReportRole.name,
                    org_group.id,
                )

    def sync_program_org_groups(self):
        """
        All programs should have the ReadProgramReports group with a consistent naming convention.
        Create or update the groups for all programs missing this default group.
        Then we save each new program org group one by one. This is inefficient but necessary
        each new program org group save() function includes a lot of logic we cannot bulk create
        """
        read_reports_groups = {}
        groups_query = ProgramOrganizationGroup.objects.select_related(
            'program'
        ).select_related('granting_organization').filter(role=ProgramReadReportRole.name)

        for group in groups_query:
            read_reports_groups[(group.granting_organization.key, group.program.key)] = group

        for program in Program.objects.select_related('managing_organization'):
            name = f'{program.managing_organization.key}_{program.key}_ReadProgramReports'

            created, updated = (False, False)
            program_org_group = read_reports_groups.get((program.managing_organization.key, program.key))

            if not program_org_group:
                program_org_group = ProgramOrganizationGroup(
                    name=name,
                    granting_organization=program.managing_organization,
                    program=program,
                    role=ProgramReadReportRole.name
                )
                created = True
            elif program_org_group.name != name:
                program_org_group.name = name
                updated = True

            if created or updated:
                program_org_group.save()
                logger.info(
                    '%s program_org group for org %s, program %s and permission %s. program_org_group_id: %s',
                    'Created' if created else 'Updated',
                    program.managing_organization.key,
                    program.key,
                    ProgramReadReportRole.name,
                    program_org_group.id,
                )
