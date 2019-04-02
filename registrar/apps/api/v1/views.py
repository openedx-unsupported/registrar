"""
The public-facing REST API.
"""
from collections.abc import Iterable
import logging

from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import resolve, reverse
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from guardian.shortcuts import get_objects_for_user
from requests.exceptions import HTTPError
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_202_ACCEPTED,
)

import registrar.apps.api.segment as segment
from registrar.apps.api.serializers import (
    CourseRunSerializer,
    JobAcceptanceSerializer,
    ProgramSerializer,
)
from registrar.apps.enrollments.models import Program
from registrar.apps.core import permissions as perms
from registrar.apps.core.models import Organization
from registrar.apps.enrollments.data import (
    get_discovery_program,
    invoke_program_enrollment_listing,
)

logger = logging.getLogger(__name__)


class AuthMixin(object):
    """
    Mixin providing AuthN/AuthZ functionality for all our views to use.

    This mixin overrides `APIView.check_permissions` to use Django Guardian.
    It replicates, to the extent that we require, the functionality of
    Django Guardian's `PermissionRequiredMixin`, which unfortunately doesn't
    play nicely with Django REST Framework.
    """
    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_required = []
    raise_404_if_unauthorized = False

    def get_permission_object(self):
        """
        Get an object against which required permissions will be checked.

        If None, permissions will be checked globally.
        """
        return None

    def check_permissions(self, request):
        """
        Check that the authenticated user can access this view.

        Ensure that the user has all of the permissions specified in
        `permission_required` granted on the object returned by
        `get_permission_object`. If not, an HTTP 403 (or, HTTP 404 if
        `raise_404_if_unauthorized` is True) is raised.

        Overrides APIView.check_permissions.
        """
        if resolve(request.path_info).url_name == 'api-docs':
            self.check_doc_permissions(request)
            return

        if isinstance(self.permission_required, str):
            required = [self.permission_required]
        elif isinstance(self.permission_required, Iterable):
            required = [perm for perm in self.permission_required]
        else:
            raise ImproperlyConfigured(
                'permission_required must be set to string or iterable; ' +
                'is set to {}'.format(self.permission_required)
            )

        if all(request.user.has_perm(perm) for perm in required):
            return
        obj = self.get_permission_object()
        if obj and all(request.user.has_perm(perm, obj) for perm in required):
            return
        if self.raise_404_if_unauthorized:
            raise Http404()
        else:
            raise PermissionDenied()

    def check_doc_permissions(self, request):
        """
        Check whether the endpoint being requested should show up in the
        Swagger UI.

        When loading /api-docs/, Swagger does `check_permissions` on all
        API endpoints in order to decide which ones to show to the user.
        However, we assign permissions on a per-Oranization-instance
        basis using Guardian, whereas /api-docs/ is Organization-agnostic.

        To compensate for this, we handle permission checks coming from
        /api-docs/ differently: we simply check if the user has the appropriate
        permission on *any* Organization instance.
        """
        if not get_objects_for_user(request.user, self.permission_required):
            raise PermissionDenied()


class ProgramListView(AuthMixin, ListAPIView):
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

    serializer_class = ProgramSerializer
    permission_required = perms.ORGANIZATION_READ_METADATA

    def get_queryset(self):
        org_key = self.request.GET.get('org', None)
        programs = Program.objects.all()
        if org_key:
            programs = programs.filter(managing_organization__key=org_key)
        segment.track(
            self.request.user.username,
            'List Programs',
            {'organization_key': org_key}
        )
        return programs

    def get_permission_object(self):
        """
        Returns an organization object against which permissions should be checked.

        If the requesting user does not have `organization_read_metadata`
        permission for the organization specified by `org` (or globally
        on the Organization class), Guardian will raise a 403.
        """
        org_key = self.request.GET.get('org')
        if org_key:
            return get_object_or_404(Organization, key=org_key)
        else:
            # By returning None, Guardian will check for global Organization
            # access instead of access against a specific Organization
            return None


class ProgramSpecificViewMixin(AuthMixin):
    """
    A mixin for views that operate on or within a specific program.

    Provides a `program` property. On first access, the property is loaded
    based on the `program_key` URL parameter, and cached for subsequent
    calls. This avoids redundant database queries between `get_object/queryset`
    and `get_permission_object`.
    """

    def __init__(self, *args, **kwargs):
        super(ProgramSpecificViewMixin, self).__init__(*args, **kwargs)
        self._program = None

    @property
    def program(self):
        """
        The program specified by the `program_key` URL parameter.
        """
        if not self._program:
            program_key = self.kwargs['program_key']
            self._program = get_object_or_404(Program, key=program_key)
        return self._program

    def get_permission_object(self):
        """
        Returns an organization object against which permissions should be checked.
        """
        return self.program.managing_organization


class ProgramRetrieveView(ProgramSpecificViewMixin, RetrieveAPIView):
    """
    A view for retrieving a single program object.

    Path: /api/v1/programs/{program_key}

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """

    serializer_class = ProgramSerializer
    permission_required = perms.ORGANIZATION_READ_METADATA

    def get_object(self):
        return self.program


class ProgramCourseListView(ProgramSpecificViewMixin, ListAPIView):
    """
    A view for listing courses in a program.

    Path: /api/v1/programs/{program_key}/courses

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """

    serializer_class = CourseRunSerializer
    permission_required = perms.ORGANIZATION_READ_METADATA

    def get_queryset(self):
        uuid = self.program.discovery_uuid
        try:
            discovery_program = get_discovery_program(uuid)
        except HTTPError as error:
            error_string = (
                'Failed to retrieve program data from course-discovery ' +
                '(key = {}, uuid = {}, http status = {})'.format(
                    self.program.key, uuid, error.response.status_code,
                )
            )
            logger.exception(error_string)
            raise Exception(error_string)

        curricula = discovery_program.get('curricula')

        # this make two temporary assumptions (zwh 03/19)
        #  1. one curriculum per program
        #  2. no programs are nested within a curriculum
        course_runs = []
        if curricula:
            for course in curricula[0].get('courses') or []:
                course_runs = course_runs + course.get('course_runs')
        return course_runs


class ProgramEnrollmentView(ProgramSpecificViewMixin, APIView):
    """
    A view for asynchronously retrieving program enrollments.

    Path: /api/v1/programs/{program_key}/enrollments

    Accepts: [GET]

    ----------------------------------------------------------------------------
    GET
    ----------------------------------------------------------------------------

    Invokes a Django User Task that retrieves student enrollment
    data for a given program.

    Returns:
     * 202: Accepted, an asynchronous job was successfully started.
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.

    Example Response:
    {
        "job_id": "3b985cec-dcf4-4d38-9498-8545ebcf5d0f",
        "job_url": "http://localhost/api/v1/jobs/3b985cec-dcf4-4d38-9498-8545ebcf5d0f"
    }
    """
    permission_required = perms.ORGANIZATION_READ_ENROLLMENTS

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return JobAcceptanceSerializer

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves program enrollment data.
        """
        original_url = self.request.build_absolute_uri()
        job_id = invoke_program_enrollment_listing(
            self.request.user, self.program.key, original_url,
        )
        job_url = self.request.build_absolute_uri(
            reverse('api:v0:job-status', kwargs={'job_id': job_id})
        )
        data = {'job_id': job_id, 'job_url': job_url}
        return Response(JobAcceptanceSerializer(data).data, HTTP_202_ACCEPTED)
