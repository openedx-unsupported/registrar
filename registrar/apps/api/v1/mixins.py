"""
Mixins for the public V1 REST API.
"""
import uuid
from collections.abc import Iterable

from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import Http404
from django.utils.functional import cached_property
from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
)
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_202_ACCEPTED,
    HTTP_207_MULTI_STATUS,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from registrar.apps.api import exceptions
from registrar.apps.api.constants import ENROLLMENT_WRITE_MAX_SIZE
from registrar.apps.api.mixins import TrackViewMixin
from registrar.apps.api.serializers import JobAcceptanceSerializer
from registrar.apps.api.utils import build_absolute_api_url
from registrar.apps.core import permissions as perms
from registrar.apps.core.constants import UPLOADS_PATH_PREFIX
from registrar.apps.core.filestore import get_filestore
from registrar.apps.core.jobs import start_job
from registrar.apps.enrollments.data import (
    write_course_run_enrollments,
    write_program_enrollments,
)
from registrar.apps.enrollments.models import Program


upload_filestore = get_filestore(UPLOADS_PATH_PREFIX)


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

    def get_required_permissions(self, _request):
        """
        Returns list of permissions in format <app_label>.<codename> that
        should be checked against request.user and object. By default, it
        returns list from `permission_required` attribute.
        """
        if isinstance(self.permission_required, str):
            return [self.permission_required]
        elif isinstance(self.permission_required, Iterable):
            return [p for p in self.permission_required]
        else:  # pragma: no cover
            raise ImproperlyConfigured(
                'permission_required must be a string or iterable; ' +
                'was {}'.format(self.permission_required)
            )

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

        required = self.get_required_permissions(request)
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
    """

    @cached_property
    def program(self):
        """
        The program specified by the `program_key` URL parameter.
        """
        program_key = self.kwargs['program_key']
        try:
            return Program.objects.get(key=program_key)
        except Program.DoesNotExist:
            self.add_tracking_data(failure='program_not_found')
            raise Http404()

    def get_permission_object(self):
        """
        Returns an organization object against which permissions should be checked.
        """
        return self.program.managing_organization


class CourseSpecificViewMixin(ProgramSpecificViewMixin):
    """
    A mixin for views that operate on or within a specific program course run.

    In addition to the functionality provided in `ProgramSpecificViewMixin`,
    this mixin provides the `internal_course_key` and `external_course_key` properties,
    which return the edX course key of the course referred to in the URL (either by the
    edX course key itself or by an external course key). It also validates
    that the course key exists within the program, raising 404 if not.
    """

    @cached_property
    def course_run(self):
        """
        Raises a 404 if the course run identified by the `course_id` path
        parameter is not part of self.program.
        """
        provided_course_id = self.kwargs['course_id']
        real_course_run = self.program.discovery_program.find_course_run(
            provided_course_id
        )
        if not real_course_run:
            self.add_tracking_data(failure='course_not_found')
            raise Http404()
        return real_course_run

    @property
    def internal_course_key(self):
        return self.course_run.key

    @property
    def external_course_key(self):
        return self.course_run.external_key


class JobInvokerMixin(object):
    """
    A mixin for views that invoke jobs and return ID and status URL.
    """
    def invoke_upload_job(self, task_fn, upload_content, *args, **kwargs):
        """
        Invoke a data upload job with task_fn and the path to an input file.
        Returns a 202 with job_id and job_url.

        *args and **kwargs are passed to task_fn *in addition* to
        job_id, user_id, and file_format.
        """
        job_id = str(uuid.uuid4())
        file_path = '{}.{}'.format(job_id, 'json')
        upload_filestore.store(file_path, upload_content)
        return self._invoke_job(task_fn, file_path, job_id=job_id, *args, **kwargs)

    def invoke_download_job(self, task_fn, *args, **kwargs):
        """
        Invoke a data download job with task_fn,
        and a return a 202 with job_id and job_url.

        *args and **kwargs are passed to task_fn *in addition* to
        job_id, user_id, and file_format.
        """
        file_format = self.request.query_params.get('fmt', 'json')
        if file_format not in {'json', 'csv'}:
            self.add_tracking_data(failure='result_format_not_supported')
            raise Http404()

        return self._invoke_job(task_fn, file_format, *args, **kwargs)

    def _invoke_job(self, task_fn, *args, **kwargs):
        """
        Invoke a job with task_fn
        """
        job_id = start_job(self.request.user, task_fn, *args, **kwargs)
        job_url = build_absolute_api_url('api:v1:job-status', job_id=job_id)
        data = {'job_id': job_id, 'job_url': job_url}
        return Response(JobAcceptanceSerializer(data).data, HTTP_202_ACCEPTED)


class EnrollmentMixin(ProgramSpecificViewMixin):
    """
    This mixin defines the required permissions
    for any views that read or write program/course enrollment data.
    """
    def get_required_permissions(self, request):
        if request.method == 'GET':
            return [perms.ORGANIZATION_READ_ENROLLMENTS]
        if request.method == 'POST' or self.request.method == 'PATCH':
            return [perms.ORGANIZATION_WRITE_ENROLLMENTS]
        return []  # pragma: no cover

    def handle_enrollments(self, course_id=None):
        """
        Handle Create/Update requests for program/course-run enrollments.

        Expects `course_id` to be internal course key.

        Does program enrollments if `course_id` is None.
        Does course run enrollments otherwise.
        """
        self.validate_enrollment_data(self.request.data)
        if course_id:
            good, bad, results = write_course_run_enrollments(
                self.request.method,
                self.program.discovery_uuid,
                course_id,
                self.request.data,
            )
        else:
            good, bad, results = write_program_enrollments(
                self.request.method,
                self.program.discovery_uuid,
                self.request.data,
            )
        if good and bad:
            status = HTTP_207_MULTI_STATUS
        elif good:
            status = HTTP_200_OK
        else:
            status = HTTP_422_UNPROCESSABLE_ENTITY
            self.add_tracking_data(failure='unprocessable_entity')
        return Response(results, status=status)

    def validate_enrollment_data(self, enrollments):
        """
        Validate enrollments request body
        """
        if not isinstance(enrollments, list):
            self.add_tracking_data(failure='bad_request')
            raise ValidationError('expected request body type: List')

        if len(enrollments) > ENROLLMENT_WRITE_MAX_SIZE:
            self.add_tracking_data(failure='request_entity_too_large')
            raise exceptions.EnrollmentPayloadTooLarge()

        for enrollment in enrollments:
            if not isinstance(enrollment, dict):
                self.add_tracking_data(failure='bad_request')
                raise ValidationError(
                    'expected items in request to be of type Dict'
                )
            if not isinstance(enrollment.get('student_key'), str):
                self.add_tracking_data(failure='bad_request')
                raise ValidationError(
                    'expected request dicts to have string value for "student_key"'
                )
            if not isinstance(enrollment.get('status'), str):
                self.add_tracking_data(failure='bad_request')
                raise ValidationError(
                    'expected request dicts to have string value for "status"'
                )
