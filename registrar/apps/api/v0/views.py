"""
A mock version of the v1 API, providing dummy data for partner integration
testing.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from registrar.apps.api.serializers import ProgramSerializer
from registrar.apps.api.v0.data import (
    FAKE_ORG_DICT,
    FAKE_ORG_PROGRAMS,
    FAKE_PROGRAM_DICT,
)


class MockProgramListView(ListAPIView):
    """
    A view for listing program objects.

    Path: /api/v1/programs?org={org_key}

    All programs within organization specified by `org_key` are returned.
    For users will global organization access, `org_key` can be omitted in order
    to return all programs.

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access to specified organization.
     * 404: Organization does not exist.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = ProgramSerializer

    def get_queryset(self):
        org_key = self.request.GET.get('org', None)
        if not org_key:
            raise PermissionDenied()
        org = FAKE_ORG_DICT.get(org_key)
        if not org:
            raise Http404()
        if not org.metadata_readable:
            raise PermissionDenied()
        return FAKE_ORG_PROGRAMS[org.key]


class ProgramSpecificViewMixin(object):
    """
    A mixin for views that operate on or within a specific program.
    """

    @property
    def program(self):
        """
        The program specified by the `program_key` URL parameter.
        """
        program_key = self.kwargs['program_key']
        if program_key not in FAKE_PROGRAM_DICT:
            raise Http404()
        return FAKE_PROGRAM_DICT[program_key]


class MockProgramRetrieveView(RetrieveAPIView, ProgramSpecificViewMixin):
    """
    A view for retrieving a single program object.

    Path: /api/v1/programs/{program_key}

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = ProgramSerializer

    def get_object(self):
        if self.program.managing_organization.metadata_readable:
            return self.program
        else:
            raise PermissionDenied()
