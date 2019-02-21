"""
The public-facing REST API.
"""
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response

from registrar.apps.enrollments.models import Program, Organization
from registrar.apps.api.serializers import ProgramSerializer
from registrar.apps.api.permissions import get_user_organization_keys


class ProgramReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A view for accessing program objects.
    ---
    retrieve:
    Return the program associated with the given ``key``,
    or 404 if no such program exists.

    list:
    Return all programs associated with the organization making the request.

    Usage:
      * /api/v1/programs/{program_key}/ - Returns data for a single program, given the program's key.
      * /api/v1/programs - Returns a list of all programs the user has access to.
      * /api/v1/programs?org={org_key} - Returns a list of an organization's programs.
    """
    lookup_field = 'key'
    serializer_class = ProgramSerializer
    queryset = Program

    def list(self, request):
        org_key = request.GET.get('org', None)
        if org_key is None:
            if not request.user.is_staff:
                return HttpResponseForbidden()
            programs = Program.objects.all()
        else:
            if not request.user.is_staff:
                user_keys = get_user_organization_keys(request.user)
                if org_key.lower() not in user_keys:
                    return HttpResponseForbidden()
            programs = get_object_or_404(Organization, key=org_key).programs.all()
        data = ProgramSerializer(programs, many=True).data
        return Response(data)

    def retrieve(self, request, key=None):
        program = get_object_or_404(Program.objects.all(), key=key)
        org_keys = set(org.key for org in program.organizations.all())
        user_org_keys = get_user_organization_keys(request.user)
        if len(org_keys.intersection(user_org_keys)) == 0:
            return HttpResponseForbidden()
        data = ProgramSerializer(program).data
        return Response(data)
