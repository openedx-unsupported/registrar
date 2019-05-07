"""
Mixins for the public REST API.
"""
from collections.abc import Iterable

from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
)
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import resolve
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from guardian.shortcuts import get_objects_for_user
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_202_ACCEPTED

from registrar.apps.api import exceptions
from registrar.apps.api.constants import ENROLLMENT_WRITE_MAX_SIZE
from registrar.apps.api.serializers import JobAcceptanceSerializer, ProgramEnrollmentRequestSerializer
from registrar.apps.api.utils import build_absolute_api_url
from registrar.apps.enrollments.models import Program
from registrar.apps.core import permissions as perms
from registrar.apps.core.jobs import start_job
from registrar.apps.enrollments.data import DiscoveryProgram


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
    staff_only = False

    def get_permission_object(self):
        """
        Get an object against which required permissions will be checked.

        If None, permissions will be checked globally.
        """
        return None

    def get_permission_required(self, _request):
        """
        Gets permission(s) to be checked.

        Must return a string or an iterable of strings.
        Can be overridden in subclass.
        Default to class-level `permission_required` attribute.
        """
        return self.permission_required

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

        if not request.user.is_authenticated:
            raise NotAuthenticated()

        if self.staff_only and not request.user.is_staff:
            self.unauthorized_response()

        required = self.get_permission_required(request)
        if isinstance(required, str):
            required = [required]
        elif isinstance(required, Iterable):
            required = list(required)
        else:
            raise ImproperlyConfigured(
                'get_permission_required must return string or iterable; ' +
                'returned {}'.format(required)
            )

        if all(request.user.has_perm(perm) for perm in required):
            return
        obj = self.get_permission_object()
        if obj and all(request.user.has_perm(perm, obj) for perm in required):
            return
        self.unauthorized_response()

    def unauthorized_response(self):
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


class ProgramSpecificViewMixin(AuthMixin):
    """
    A mixin for views that operate on or within a specific program.

    Provides a `program` property. On first access, the property is loaded
    based on the `program_key` URL parameter, and cached for subsequent
    calls. This avoids redundant database queries between `get_object/queryset`
    and `get_permission_object`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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


class CourseSpecificViewMixin(ProgramSpecificViewMixin):
    """
    A mixin for views that operate on or within a specific program course run.

    In addition to the functionality provided in `ProgramSpecificViewMixin`,
    this mixin provides a `validate_course_id` function, which confirms
    that the course ID (provided in the `course_id` path parameter)
    exists within a program. If it does not, a 404 is raised.
    """

    def validate_course_id(self):
        """
        Raises a 404 if the course run identified by the `course_id` path
        parameter is not part of self.program.
        """
        course_id = self.kwargs['course_id']
        program_uuid = self.program.discovery_uuid
        discovery_program = DiscoveryProgram.get(program_uuid)
        program_course_run_ids = {
            run.key for run in discovery_program.course_runs
        }
        if course_id not in program_course_run_ids:
            raise Http404()


class JobInvokerMixin(object):
    """
    A mixin for views that invoke jobs and return ID and status URL.
    """

    def invoke_job(self, task_fn, *args, **kwargs):
        """
        Invoke a job with task_fn, and a return a 202 with job_id and job_url.

        *args and **kwargs are passed to task_fn *in addition* to
        job_id, user_id, and file_format.
        """
        file_format = self.request.query_params.get('fmt', 'json')
        if file_format not in {'json', 'csv'}:
            raise Http404()
        job_id = start_job(self.request.user, task_fn, file_format, *args, **kwargs)
        job_url = build_absolute_api_url('api:v1:job-status', job_id=job_id)
        data = {'job_id': job_id, 'job_url': job_url}
        return Response(JobAcceptanceSerializer(data).data, HTTP_202_ACCEPTED)


class EnrollmentMixin(ProgramSpecificViewMixin):
    """
    This mixin defines the serializers and required permissions
    for any views that read or write program/course enrollment data.
    """
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return JobAcceptanceSerializer
        if self.request.method == 'POST' or self.request.method == 'PATCH':
            return ProgramEnrollmentRequestSerializer(multiple=True)

    def get_permission_required(self, request):
        if request.method == 'GET':
            return perms.ORGANIZATION_READ_ENROLLMENTS
        if request.method == 'POST' or self.request.method == 'PATCH':
            return perms.ORGANIZATION_WRITE_ENROLLMENTS
        return []

    def validate_enrollment_data(self, enrollments):
        """
        Validate enrollments request body
        """
        if not isinstance(enrollments, list):
            raise ValidationError('expected request body type: List')

        if len(enrollments) > ENROLLMENT_WRITE_MAX_SIZE:
            raise exceptions.EnrollmentPayloadTooLarge()
