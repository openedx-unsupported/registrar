"""
The public-facing REST API.
"""
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework import viewsets
from rest_framework.response import Response

from registrar.apps.api.permissions import program_access_required
from registrar.apps.api.serializers import ProgramSerializer
from registrar.apps.enrollments.models import ACCESS_READ, Program, Organization


class ProgramReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A view for accessing program objects.

    /api/v1/programs
        List all programs. Staff users only.

    /api/v1/programs?org={org_key}
        Return programs of organization specified by ``org`` query parameter.

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
    authentication_classes = (JwtAuthentication,)
    lookup_field = 'program_key'
    serializer_class = ProgramSerializer
    queryset = Program

    def list(self, request):
        org_key = request.GET.get('org', None)
        if org_key is None:
            if not request.user.is_staff:
                return HttpResponseForbidden()
            programs = Program.objects.all()
        else:
            org = get_object_or_404(Organization, key=org_key.lower())
            if not org.check_access(request.user, ACCESS_READ):
                return HttpResponseForbidden()
            programs = org.programs.all()
        data = ProgramSerializer(programs, many=True).data
        return Response(data)

    @program_access_required(ACCESS_READ)
    def retrieve(self, request, program):  # pylint: disable=arguments-differ
        data = ProgramSerializer(program).data
        return Response(data)
