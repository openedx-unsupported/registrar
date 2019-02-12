"""
The public-facing REST API.
"""
from rest_framework import viewsets

from registrar.apps.enrollments.models import Program
from registrar.apps.api.serializers import ProgramSerializer


class ProgramReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A view for accessing program objects.

    retrieve:
    Return the program associated with the given ``discovery_uuid``,
    or 404 if no such program exists.

    list:
    Return all programs associated with the organization making the request.

    Usage:
      * /api/v1/programs/{discovery_uuid}/  - Returns data for a single program, given the program's discovery UUID
      * /api/v1/programs/ - Returns a list of all programs the requesting user has access to.
    """
    # This field specifies that individual programs should
    # be filtered by their `discovery_uuid` field.
    lookup_field = 'discovery_uuid'
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
