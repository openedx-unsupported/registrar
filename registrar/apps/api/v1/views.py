"""
The public-facing REST API.
"""
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from guardian.mixins import PermissionRequiredMixin
from rest_framework import viewsets
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response

from registrar.apps.api.serializers import ProgramSerializer
from registrar.apps.enrollments.models import Program, Organization


class BaseProgramViewSet(PermissionRequiredMixin, viewsets.GenericViewSet):
    authentication_classes = (JwtAuthentication,)
    serializer_class = ProgramSerializer
    queryset = Program.objects.all()

    # An authorized user must be able to read metadata about an organization's programs
    permission_required = 'enrollments.organization_read_metadata'
    # A staff user with the global permission for reading organization metadata can
    # access the metadata for any organization.
    accept_global_perms = True
    # Return a 403 instead of trying to redirect the user
    return_403 = True


class RetrieveProgramViewSet(RetrieveModelMixin, BaseProgramViewSet):
    """
    A view for retrieving a single program object.

    /api/v1/programs/{program_key}
        Return the program associated with the given ``program_key``,
        or 404 if no such program exists.

    Responses:
        '200':
            description: OK
        '403':
            description: User does not have read access to program(s)
        '404':
            description: Program key not found.
    """
    lookup_field = 'key'

    @property
    def permission_object(self):
        """
        Returns an organization object against which permissions should be checked.
        If the requesting user does not have permission to access this program's
        organization, or does not have global staff permissions, a 403
        will eventually be returned.
        """
        try:
            program = self.get_object().select_related('organization')
        except:
            return
        return program.managing_organization


class ListProgramViewSet(ListModelMixin, BaseProgramViewSet):
    """
    A view for accessing program objects.

    /api/v1/programs
        List all programs. Staff users only.

    /api/v1/programs?org={org_key}
        Return programs of organization specified by ``org`` query parameter.

    Responses:
        '200':
            description: OK
        '403':
            description: User does not have read access to program(s)
        '404':
            description: Program key not found.
    """
    @property
    def permission_object(self):
        """
        Returns an organization object against which permissions should be checked.
        If the requesting user does not have permission to access the organization
        specified by the ``org`` query parameter, or does not have global staff permissions,
        a 403 will eventually be returned.
        """
        org_key = self.request.GET.get('org')
        if not org_key:
            # permission checking will pass only if the requesting
            # user has global permissions to access any organization's data
            return
        try:
            return Organization.objects.get(key=org_key)
        except Organization.DoesNotExist:
            # TODO: probably better to propagate a 404 here
            return

    def list(self, request):
        org_key = request.GET.get('org', None)
        if org_key is None:
            programs = self.get_queryset()
        else:
            programs = self.get_queryset().filter(managing_organization__key=org_key)
        data = self.get_serializer(programs, many=True).data
        return Response(data)
