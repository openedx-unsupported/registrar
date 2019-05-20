"""
Mixins for the public V1 REST API.
"""
from collections.abc import Iterable

from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
)
from django.http import Http404
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_202_ACCEPTED

from registrar.apps.api import exceptions
from registrar.apps.api.constants import ENROLLMENT_WRITE_MAX_SIZE
from registrar.apps.api.mixins import TrackViewMixin
from registrar.apps.api.serializers import JobAcceptanceSerializer
from registrar.apps.api.utils import build_absolute_api_url
from registrar.apps.enrollments.models import Program
from registrar.apps.core import permissions as perms
from registrar.apps.core.jobs import start_job
from registrar.apps.enrollments.data import DiscoveryProgram


class AuthMixin(TrackViewMixin):
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
        return None  # pragma: no cover

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
        if not request.user.is_authenticated:
            raise NotAuthenticated()

        if self.staff_only and not request.user.is_staff:
            self.add_tracking_data(failure='user_is_not_staff')
            self._unauthorized_response()

        required = self.get_permission_required(request)
        if isinstance(required, str):
            required = [required]
        elif isinstance(required, Iterable):
            required = list(required)
        else:  # pragma: no cover
            raise ImproperlyConfigured(
                'get_permission_required must return string or iterable; ' +
                'returned {}'.format(required)
            )

        missing_global_permissions = {
            perm for perm in required
            if not request.user.has_perm(perm)
        }
        obj = self.get_permission_object()
        if not missing_global_permissions:
            missing_permissions = set()
        elif obj:
            missing_permissions = {
                perm for perm in required
                if not request.user.has_perm(perm, obj)
            }
        else:
            missing_permissions = missing_global_permissions

        if missing_permissions:
            self.add_tracking_data(missing_permissions=list(missing_permissions))
            self._unauthorized_response()

    def _unauthorized_response(self):
        """
        Raise 403 or 404, depending on `self.raise_404_if_unauthorized`.
        """
        if self.raise_404_if_unauthorized:
            raise Http404()
        else:
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
            try:
                self._program = Program.objects.get(key=program_key)
            except Program.DoesNotExist:
                self.add_tracking_data(failure='program_not_found')
                raise Http404()
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
            self.add_tracking_data(failure='course_not_found')
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
            self.add_tracking_data(failure='result_format_not_supported')
            raise Http404()
        job_id = start_job(self.request.user, task_fn, file_format, *args, **kwargs)
        job_url = build_absolute_api_url('api:v1:job-status', job_id=job_id)
        data = {'job_id': job_id, 'job_url': job_url}
        return Response(JobAcceptanceSerializer(data).data, HTTP_202_ACCEPTED)


class EnrollmentMixin(ProgramSpecificViewMixin):
    """
    This mixin defines the required permissions
    for any views that read or write program/course enrollment data.
    """
    def get_permission_required(self, request):
        if request.method == 'GET':
            return perms.ORGANIZATION_READ_ENROLLMENTS
        if request.method == 'POST' or self.request.method == 'PATCH':
            return perms.ORGANIZATION_WRITE_ENROLLMENTS
        return []  # pragma: no cover

    def validate_enrollment_data(self, enrollments):
        """
        Validate enrollments request body
        """
        if not isinstance(enrollments, list):
            self.add_tracking_data(failure='unprocessable_entity')
            raise ValidationError('expected request body type: List')

        if len(enrollments) > ENROLLMENT_WRITE_MAX_SIZE:
            self.add_tracking_data(failure='request_entity_too_large')
            raise exceptions.EnrollmentPayloadTooLarge()

    def add_tracking_data_from_lms_response(self, response):
        """
        Given an API response from the LMS, add necessary tracking data.
        """
        if response.status_code == 413:  # pragma: no cover
            self.add_tracking_data(failure='request_entity_too_large')
        elif response.status_code == 422:
            self.add_tracking_data(failure='unprocessable_entity')
