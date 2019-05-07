""" Internal utility API views """
from django.core.cache import cache
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.status import HTTP_204_NO_CONTENT

from registrar.apps.api.v1.mixins import ProgramSpecificViewMixin
from registrar.apps.enrollments.constants import PROGRAM_CACHE_KEY_TPL
from registrar.apps.enrollments.models import Program


class FlushProgramCacheView(ProgramSpecificViewMixin, APIView):
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
    authentication_classes = (JwtAuthentication, SessionAuthentication)
    staff_only = True

    # pylint: disable=unused-argument
    def delete(self, request, program_key=None):
        """
        Clears a specific program from the cache, if specified.
        Otherwise, clears the entire cache.
        """
        if program_key:
            program_uuid = self.program.discovery_uuid
            cache.delete(PROGRAM_CACHE_KEY_TPL.format(uuid=program_uuid))
        else:
            cache.delete_many([
                PROGRAM_CACHE_KEY_TPL.format(uuid=program.discovery_uuid)
                for program in Program.objects.all()
            ])
        return Response(status=HTTP_204_NO_CONTENT)
