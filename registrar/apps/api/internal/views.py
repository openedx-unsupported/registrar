""" Internal utility API views """
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
)
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from registrar.apps.core.constants import PROGRAM_CACHE_KEY_TPL
from registrar.apps.core.models import Program

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

    # pylint: disable=unused-argument
    def delete(self, request, program_key=None):
        """
        Clears a specific program from the cache, if specified.
        Otherwise, clears the entire cache.
        """
        if program_key:
            program = get_object_or_404(Program, key=program_key)
            program_uuid = program.discovery_uuid
            cache.delete(PROGRAM_CACHE_KEY_TPL.format(uuid=program_uuid))
        else:
            cache.delete_many([
                PROGRAM_CACHE_KEY_TPL.format(uuid=program.discovery_uuid)
                for program in Program.objects.all()
            ])
        return Response(status=HTTP_204_NO_CONTENT)
