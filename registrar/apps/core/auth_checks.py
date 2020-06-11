"""
Functions for checking user access and membership to organizations and programs.
"""
from guardian.shortcuts import get_objects_for_user, get_perms

from registrar.apps.core.permissions import API_ENROLLMENT_PERMISSIONS

from .discovery_cache import ProgramDetails
from .models import Organization, OrganizationGroup, Program
from .permissions import DB_TO_API_PERMISSION_MAPPING


def get_user_organizations(user):
    """
    Get the set of Organizations that the user belongs to via OrganizationGroups.

    Arguments:
        user (User)

    Returns: frozenset[Organization]
    """
    groups = user.groups.all()
    organization_groups = OrganizationGroup.objects.filter(id__in=groups)
    organization_ids = organization_groups.values_list('organization', flat=True)
    organizations = Organization.objects.filter(id__in=organization_ids)
    return frozenset(organizations)


def get_programs_by_api_permission(user, required_api_permission, organization_filter=None):
    """
    Return a queryset of programs that a user is granted the required_api_permisssion to.

    Note that "an API permission granted to a user" may be done via the
    Program itself, the Program's managing Organization, or both;
    furthermore, that granting may be done on an object-level, on the global-level,
    or both. For details on this, see ADRs 3, 4, and 6.

    Arguments:
        user (User)
        required_api_permission (APIPermission)
        organization_filter (Organization|None):
            Optional organization to filter the queryset on.

    Returns: QuerySet[Program]
        A queryset of Programs, optionally filtered down by managing_organization,
        upon which the user possesses the required_api_permission.
    """
    # Start with a queryset of Programs for which the user has the Program permission.
    programs_with_perm_qs = get_objects_for_user(
        user=user,
        perms=required_api_permission.program_permission,
        klass=Program,
        use_groups=True,  # Use both user-assigned and group assigned permissions.
        with_superuser=True,  # Superusers implicitly have permission on all objects.
        accept_global_perms=True,  # Global permissions apply to all objects.
    )
    if organization_filter:
        # If we're filtering by an Organization, then check if the user has the
        # corresponding Organization permission.
        has_perm_on_filter_org = (
            # Check object-level permissions on Organization.
            user.has_perm(
                required_api_permission.organization_permission,
                organization_filter,
            ) or
            # Check global Organization permission.
            user.has_perm(
                required_api_permission.organization_permission
            )
        )
        # If they have permission on the filter Organization, then just grab all
        # programs managed by that organization.
        # Otherwise, apply the Organizaiton filter the Programs with Program-level
        # permission.
        programs_qs = (
            Program.objects if has_perm_on_filter_org else programs_with_perm_qs
        ).filter(
            managing_organization=organization_filter
        )
    else:
        # If we're not filter by organization, we need to take the union of:
        # * Programs upon which the user has Program permission, and
        # * Programs that are managed by an Organization upon which the
        #   user has Organization permission.
        organizations_with_perm_qs = get_objects_for_user(
            user=user,
            perms=required_api_permission.organization_permission,
            klass=Organization,
            use_groups=True,
            with_superuser=True,
            accept_global_perms=True,
        )
        programs_qs = (
            programs_with_perm_qs |
            Program.objects.filter(
                managing_organization__in=organizations_with_perm_qs
            )
        )
    if required_api_permission.enables_enrollment_management:
        # If the required permission involves enrollment management,
        # then specifically remove enrollment permissions for programs where
        # enrollment management is disabled (at the time of writing,
        # this includes all MicroMasters and MicroBachelors programs).
        # For efficiency, grab all the UUIDs we need from the queryset, use them
        # to query the discovery cache, and then build a new queryset from the
        # filtered list of UUIDs.
        program_uuids = programs_qs.values_list('discovery_uuid', flat=True)
        details_by_uuid = ProgramDetails.load_many(program_uuids)
        program_uuids = [
            uuid
            for uuid in program_uuids
            if details_by_uuid[uuid].is_enrollment_enabled
        ]
        return Program.objects.filter(discovery_uuid__in=program_uuids)
    else:
        # Otherwise, just return the queryset.
        return programs_qs


def get_api_permissions_by_program(user, program):
    """
    Returns a set of all APIPermissions granted to the user on a
    program  either in the context of a program or an organization.
    This includes permissions granted though a global permission or role.

    This will filter out APIPermissions for the program that are not valid
    for the program. Currently, this only removes a user's read and/or write
    enrollments permissions for a program that does not have enrollments enabled.

    Arguments:
        user (User)
        program (Program)

    Returns: set[APIPermission]
    """
    program_permissions = _get_api_permissions_for_single_object(
        user, program
    )
    organization_permissions = _get_api_permissions_for_single_object(
        user, program.managing_organization
    )
    user_permissions = program_permissions | organization_permissions
    # Specifically remove enrollment permissions for programs where
    # enrollment management is disabled (at the time of writing,
    # this includes all MicroMasters and MicroBachelors programs).
    if user_permissions and not program.details.is_enrollment_enabled:
        user_permissions -= set(API_ENROLLMENT_PERMISSIONS)
    return user_permissions


def _get_api_permissions_for_single_object(user, obj):
    """
    Returns a set of all APIPermissions granted to the user on a
    provided object instance. This includes permissions granted though a
    global permission or role. If no object is passed only global permissions
    will be returned.

    You should not use this function directly if you want a set of a user's effective
    APIPermissions, as this function does not account for programs for which enrollments
    are disabled. Use the `get_api_permissions_by_program` function for this
    purpose instead.
    """
    user_object_permissions = get_perms(user, obj)
    user_global_permissions = list(user.get_all_permissions())
    user_api_permissions = set()
    for db_perm in user_object_permissions + user_global_permissions:
        if db_perm in DB_TO_API_PERMISSION_MAPPING:  # pragma: no branch
            user_api_permissions.add(DB_TO_API_PERMISSION_MAPPING[db_perm])
    return user_api_permissions
