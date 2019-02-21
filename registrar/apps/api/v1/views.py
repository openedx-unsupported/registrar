"""
The public-facing REST API.
"""
from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from registrar.apps.enrollments.models import Program, Organization
from registrar.apps.api.serializers import ProgramSerializer
from registrar.apps.api.permissions import ProgramReadOnlyViewSetPermission


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
      * /api/v1/programs?org={org_key} - Returns a list of an organization's programs.
      * /api/v1/programs - Returns a list of all programs. Staff users only.
    """
    lookup_field = 'key'
    serializer_class = ProgramSerializer
    permission_classes = [ProgramReadOnlyViewSetPermission]

    def get_queryset(self):
        org_key = self.request.GET.get('org', None)
        if org_key is None:
            return Program.objects.all()
        else:
            return get_object_or_404(Organization, key=org_key).programs
