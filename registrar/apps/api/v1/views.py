"""
The public-facing REST API.
"""
import logging

from django.http import HttpResponseForbidden, HttpResponseServerError
from django.shortcuts import get_object_or_404
from requests.exceptions import HTTPError
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from registrar.apps.api.permissions import program_access_required
from registrar.apps.api.serializers import ProgramSerializer, CourseRunSerializer
from registrar.apps.enrollments.models import ACCESS_READ, Program, Organization
from registrar.apps.enrollments.data import get_discovery_program

logger = logging.getLogger(__name__)


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

    /api/v1/programs/{program_key}/courses
        List all courses associated with the given ``program_key``,
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
    lookup_url_kwarg = 'program_key'
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

    @action(detail=True)
    def courses(self, request, program_key):  # pylint: disable=unused-argument
        """
        Retrieve the list of courses contained within this program.

        This returns a flat list of course run objects from the discovery
        service.  This endpoint will only include courses setup as
        part of a curriculum.
        """
        program = self.get_object()
        if not program.check_access(request.user, ACCESS_READ):
            return HttpResponseForbidden()

        try:
            discovery_program = get_discovery_program(program.discovery_uuid)
        except HTTPError:
            logger.exception(
                'Failed to retrieve program data from course-discovery'
            )
            return HttpResponseServerError()

        curricula = discovery_program.get('curricula')

        # this make two temporary assumptions (zwh 03/19)
        #  1. one curriculum per program
        #  2. no programs are nested within a curriculum
        course_runs = []
        if curricula:
            for course in curricula[0].get('courses') or []:
                course_runs = course_runs + course.get('course_runs')

        data = CourseRunSerializer(course_runs, many=True).data

        return Response(data)
