""" Internal utility API views """
from django.shortcuts import get_object_or_404
from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
)
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from registrar.apps.core.models import Program
from registrar.apps.core.proxies import DiscoveryProgram

from ..v1.mixins import AuthMixin


class FlushProgramCacheView(AuthMixin, APIView):
    """
    A view for clearing the programs cache.
    Is only accessable to staff users.

    Path: /api/internal/cache/{program_key}/

    Accepts: [DELETE]

    Returns:
     * 200: Program cache successfully cleared
     * 401: User not authenticated
     * 403: User not staff
     * 404: Program not found (only returned if user is staff)
    """
    event_method_map = {'DELETE': 'registrar.internal.flush_program_cache'}
    event_parameter_map = {'program_key': 'program_key'}
    authentication_classes = (JwtAuthentication, SessionAuthentication)
    raise_404_if_unauthorized = True
    staff_only = True

    def delete(self, request, program_key=None):
        """
        Clears a specific program from the cache, if specified.
        Otherwise, clears the entire cache.
        """
        if program_key:
            program = get_object_or_404(Program, key=program_key)
            program_uuids = [program.discovery_uuid]
        else:
            program_uuids = list(
                Program.objects.values_list('discovery_uuid', flat=True)
            )
        DiscoveryProgram.clear_cached_program_details(program_uuids)
        return Response(status=HTTP_204_NO_CONTENT)
