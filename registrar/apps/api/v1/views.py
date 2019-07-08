"""
The public-facing REST API.
"""
import csv
import io
import json
import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from django.utils.functional import cached_property
from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
)
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_409_CONFLICT
from rest_framework.views import APIView

from registrar.apps.api.constants import (
    PERMISSION_QUERY_PARAM_MAP,
    UPLOAD_FILE_MAX_SIZE,
)
from registrar.apps.api.exceptions import FileTooLarge
from registrar.apps.api.mixins import TrackViewMixin
from registrar.apps.api.serializers import (
    CourseRunSerializer,
    JobStatusSerializer,
    ProgramSerializer,
)
from registrar.apps.api.v1.mixins import (
    AuthMixin,
    CourseSpecificViewMixin,
    EnrollmentMixin,
    JobInvokerMixin,
    ProgramSpecificViewMixin,
)
from registrar.apps.core import permissions as perms
from registrar.apps.core.jobs import (
    get_job_status,
    get_processing_jobs_for_user,
)
from registrar.apps.core.models import Organization
from registrar.apps.enrollments.data import DiscoveryProgram
from registrar.apps.enrollments.models import Program
from registrar.apps.enrollments.tasks import (
    list_all_course_run_enrollments,
    list_course_run_enrollments,
    list_program_enrollments,
    write_course_run_enrollments,
    write_program_enrollments,
)
from registrar.apps.enrollments.utils import is_enrollment_job_processing


logger = logging.getLogger(__name__)


class ProgramListView(AuthMixin, TrackViewMixin, ListAPIView):
    """
    A view for listing program objects.

    Path: /api/[version]/programs?org={org_key}

    All programs within organization specified by `org_key` are returned.
    For users will global organization access, `org_key` can be omitted in order
    to return all programs.

    Returns:
     * 200: OK
     * 403: User lacks read access to specified organization.
     * 404: Organization does not exist.
    """

    serializer_class = ProgramSerializer
    event_method_map = {'GET': 'registrar.{api_version}.list_programs'}
    event_parameter_map = {
        'org': 'organization_filter',
        'user_has_perm': 'permission_filter',
    }

    def get_queryset(self):
        programs = Program.objects.all()
        if self.organization_filter:
            programs = programs.filter(
                managing_organization=self.organization_filter
            )
        if self.permission_filter:
            programs = (
                program for program in programs
                if self.request.user.has_perm(
                    self.permission_filter, program.managing_organization
                )
            )
        return programs

    def get_required_permissions(self, _request):
        """
        Returns permissions that user must have on object returned by
        `get_permission_object`.

        If the user specifies a `user_has_perm` filter, then we filter
        programs based on the user's permissions in `get_queryset`, so we
        don't want to require any permissions. In the case that the user does
        not have the specified permissions, they will get a 200 with an empty
        list.

        If the user does NOT specify a `user_has_perm` filter, then we
        enforce that they have metadata-reading permission, and return a 403
        if they do not have it for the specified organization(s).
        """
        if self.permission_filter:
            return []
        else:
            return [perms.ORGANIZATION_READ_METADATA]

    def get_permission_object(self):
        """
        Returns an organization object against which permissions should be checked.

        If the requesting user does not have `organization_read_metadata`
        permission for the organization specified by `org` (or globally
        on the Organization class), Guardian will raise a 403.
        """
        # If this call returns None, Guardian will check for global Organization
        # access instead of access against a specific Organization.
        return self.organization_filter

    @cached_property
    def organization_filter(self):
        """
        Return the organization by which results will be filtered,
        or None if on filter specified.

        Raises 404 for non-existant organiation.
        """
        org_key = self.request.GET.get('org')
        if org_key:
            try:
                return Organization.objects.get(key=org_key)
            except Organization.DoesNotExist:
                self.add_tracking_data(failure='org_not_found')
                raise Http404()
        else:
            return None

    @cached_property
    def permission_filter(self):
        """
        Return the user permissions by which results will be filtered,
        or None if on filter specified.

        Raises 404 for bad permission query param.
        """
        perm_query_param = self.request.GET.get('user_has_perm', None)
        if not perm_query_param:
            return None
        elif perm_query_param in PERMISSION_QUERY_PARAM_MAP:
            return PERMISSION_QUERY_PARAM_MAP[perm_query_param]
        else:
            self.add_tracking_data(failure='no_such_perm')
            raise Http404()


class ProgramRetrieveView(ProgramSpecificViewMixin, RetrieveAPIView):
    """
    A view for retrieving a single program object.

    Path: /api/[version]/programs/{program_key}

    Returns:
     * 200: OK
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """
    serializer_class = ProgramSerializer
    permission_required = [perms.ORGANIZATION_READ_METADATA]
    event_method_map = {'GET': 'registrar.{api_version}.get_program_detail'}
    event_parameter_map = {'program_key': 'program_key'}

    def get_object(self):
        return self.program


class ProgramCourseListView(ProgramSpecificViewMixin, ListAPIView):
    """
    A view for listing courses in a program.

    Path: /api/[version]/programs/{program_key}/courses

    Returns:
     * 200: OK
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """
    serializer_class = CourseRunSerializer
    permission_required = perms.ORGANIZATION_READ_METADATA
    event_method_map = {'GET': 'registrar.{api_version}.get_program_courses'}
    event_parameter_map = {'program_key': 'program_key'}

    def get_queryset(self):
        uuid = self.program.discovery_uuid
        discovery_program = DiscoveryProgram.get(uuid)
        return discovery_program.course_runs


class ProgramEnrollmentView(EnrollmentMixin, JobInvokerMixin, APIView):
    """
    A view for enrolling students in a program, or retrieving/modifying program enrollment data.

    Path: /api/[version]/programs/{program_key}/enrollments

    Accepts: [GET, POST, PATCH]

    ------------------------------------------------------------------------------------
    GET
    ------------------------------------------------------------------------------------

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
        "job_url": "http://localhost/api/[version]/jobs/3b985cec-dcf4-4d38-9498-8545ebcf5d0f"
    }

    ------------------------------------------------------------------------------------
    POST / PATCH
    ------------------------------------------------------------------------------------

    Create or modify program enrollments. Checks user permissions and forwards request
    to the LMS program_enrollments endpoint.  Accepts up to 25 enrollments

    Returns:
     * 200: Returns a map of students and their enrollment status.
     * 207: Not all students enrolled. Returns resulting enrollment status.
     * 401: User is not authenticated
     * 403: User lacks read access for the organization of specified program.
     * 404: Program does not exist.
     * 413: Payload too large, over 25 students supplied.
     * 422: Invalid request, unable to enroll students.
    """
    event_method_map = {
        'GET': 'registrar.{api_version}.get_program_enrollment',
        'POST': 'registrar.{api_version}.post_program_enrollment',
        'PATCH': 'registrar.{api_version}.patch_program_enrollment',
    }
    event_parameter_map = {
        'program_key': 'program_key',
        'fmt': 'result_format',
    }

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves program enrollment data.
        """
        return self.invoke_download_job(list_program_enrollments, self.program.key)

    def post(self, request, program_key):
        """ POST handler """
        return self.handle_enrollments()

    def patch(self, request, program_key):  # pylint: disable=unused-argument
        """ PATCH handler """
        return self.handle_enrollments()


class CourseEnrollmentView(CourseSpecificViewMixin, JobInvokerMixin, EnrollmentMixin, APIView):
    """
    A view for enrolling students in a program course run.

    Path: /api/[version]/programs/{program_key}/courses/{course_id}/enrollments

    Accepts: [GET, PATCH, POST]

    ------------------------------------------------------------------------------------
    GET
    ------------------------------------------------------------------------------------

    Invokes a Django User Task that retrieves student enrollment
    data for a given program course run.

    Returns:
     * 202: Accepted, an asynchronous job was successfully started.
     * 401: User is not authenticated
     * 403: User lacks enrollment read access to organization of specified course run.
     * 404: Course run does not exist within specified program.

    Example Response:
    {
        "job_id": "3b985cec-dcf4-4d38-9498-8545ebcf5d0f",
        "job_url": "http://localhost/api/[version]/jobs/3b985cec-dcf4-4d38-9498-8545ebcf5d0f"
    }

    ------------------------------------------------------------------------------------
    POST / PATCH
    ------------------------------------------------------------------------------------

    Create or modify program course enrollments. Checks user permissions and forwards request
    to the LMS program_enrollments endpoint.  Accepts up to 25 enrollments

    Returns:
     * 200: Returns a map of students and their course enrollment status.
     * 207: Not all students enrolled. Returns resulting enrollment status.
     * 401: User is not authenticated
     * 403: User lacks read access for the organization of specified program.
     * 404: Program does not exist.
     * 413: Payload too large, over 25 students supplied.
     * 422: Invalid request, unable to enroll students.
    """
    event_method_map = {
        'GET': 'registrar.{api_version}.get_course_enrollment',
        'POST': 'registrar.{api_version}.post_course_enrollment',
        'PATCH': 'registrar.{api_version}.patch_course_enrollment',
    }
    event_parameter_map = {
        'program_key': 'program_key',
        'course_id': 'course_key',
        'fmt': 'result_format',
    }

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves course run enrollment data.
        """
        return self.invoke_download_job(
            list_course_run_enrollments,
            self.program.key,
            self.internal_course_key,
            self.external_course_key,
        )

    def post(self, request, program_key, course_id):
        """ POST handler """
        return self.handle_enrollments(self.internal_course_key)

    def patch(self, request, program_key, course_id):  # pylint: disable=unused-argument
        """ PATCH handler """
        return self.handle_enrollments(self.internal_course_key)


class JobStatusRetrieveView(TrackViewMixin, RetrieveAPIView):
    """
    A view for getting the status of a job.

    Path: /api/[version]/jobs/{job_id}

    Accepts: [GET]

    Returns:
     * 200: Returns the status of the job
     * 404: Invalid job ID

    Example:
    {
        "created": "2019-03-27T18:19:19.189272Z",
        "state": "Succeeded",
        "result":
            "http://localhost/files/3b985cec-dcf4-4d38-9498-8545ebcf5d0f.json"
    }
    """
    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = JobStatusSerializer
    event_method_map = {'GET': 'registrar.{api_version}.get_job_status'}
    event_parameter_map = {'job_id': 'job_id'}

    def get_object(self):
        try:
            status = get_job_status(self.request.user, self.kwargs['job_id'])
        except PermissionDenied:
            self.add_tracking_data(missing_permissions=[perms.JOB_GLOBAL_READ])
            raise
        except ObjectDoesNotExist:
            self.add_tracking_data(failure='job_not_found')
            raise Http404()
        self.add_tracking_data(job_state=status.state)
        return status


class JobStatusListView(AuthMixin, TrackViewMixin, ListAPIView):
    """
    A view for listing currently processing jobs.

    Path: /api/[version]/jobs/

    Returns:
     * 200: OK
     * 401: User is not logged in.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = JobStatusSerializer
    event_method_map = {'GET': 'registrar.{api_version}.list_job_statuses'}

    def get_queryset(self):
        return get_processing_jobs_for_user(self.request.user)


class EnrollmentUploadView(JobInvokerMixin, APIView):
    """
    Base view for uploading enrollments via csv file

    Returns:
     * 202: Upload created
     * 403: User lack write access at specified program
     * 400: Validation error, missing or invalid file
     * 404: Program does not exist
     * 409: Job already processing for this program
     * 413: File too large
    """
    parser_classes = (MultiPartParser,)
    field_names = []  # Override in subclass
    task_fn = None  # Override in subclass

    def post(self, request, *args, **kwargs):
        """ POST handler """
        if 'file' not in request.data:
            raise ParseError('No file content uploaded')

        csv_file = request.data['file']
        if csv_file.size > UPLOAD_FILE_MAX_SIZE:
            raise FileTooLarge()

        if is_enrollment_job_processing(self.program.key):
            return Response('Job already in progress for program', HTTP_409_CONFLICT)

        file_itr = io.StringIO(csv_file.read().decode('utf-8'))

        enrollments = []
        # If the `fieldnames` kwargs is omitted, the values in the
        # first row of file_itr will be used as the fieldnames.
        reader = csv.DictReader(file_itr)
        if not set(reader.fieldnames).issuperset(set(self.field_names)):
            raise ValidationError('Invalid csv headers')

        for n, row in enumerate(reader, 1):
            if not self._is_valid_row(row):
                raise ValidationError('Unable to begin upload. Encountered missing data at row {}'.format(n))
            enrollments.append(row)

        return self.invoke_upload_job(self.task_fn, json.dumps(enrollments), *args, **kwargs)

    def _is_valid_row(self, row):
        """ validate row data has required headers """
        if None in row:
            return False
        for field in self.field_names:
            if not row[field]:
                return False
        return True


class ProgramEnrollmentUploadView(ProgramSpecificViewMixin, EnrollmentUploadView):
    """
    A view for uploading program enrollments via csv file

    Path: /api/[version]/programs/{program_key}/enrollments
    """
    field_names = ['student_key', 'status']
    task_fn = write_program_enrollments
    event_method_map = {'POST': 'registrar.{api_version}.upload_program_enrollments'}
    event_parameter_map = {'program_key': 'program_key'}


class CourseRunEnrollmentUploadView(ProgramSpecificViewMixin, EnrollmentUploadView):
    """
    A view for uploading course enrollments via csv file

    Path: /api/[version]/programs/{program_key}/course_enrollments
    """
    field_names = ['student_key', 'course_key', 'status']
    task_fn = write_course_run_enrollments
    event_method_map = {'POST': 'registrar.{api_version}.upload_course_enrollments'}
    event_parameter_map = {'program_key': 'program_key'}


class CourseRunEnrollmentDownloadView(EnrollmentMixin, JobInvokerMixin, APIView):
    """
    Invokes a Django User Task that retrieves student enrollment
    data for all course runs within this program.

    Returns:
     * 202: Accepted, an asynchronous job was successfully started.
     * 401: User is not authenticated
     * 403: User lacks enrollment read access to organization of specified program
     * 404: Program was not found.

    Example Response:
    {
        "job_id": "3b985cec-dcf4-4d38-9498-8545ebcf5d0f",
        "job_url": "http://localhost/api/[version]/jobs/3b985cec-dcf4-4d38-9498-8545ebcf5d0f"
    }

    Path: /api/[version]/programs/{program_key}/course_enrollments
    """
    event_method_map = {
        'GET': 'registrar.v1.download_course_enrollments',
    }
    event_parameter_map = {
        'program_key': 'program_key',
        'fmt': 'result_format',
    }

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves course run enrollment data for the given program.
        """
        return self.invoke_download_job(
            list_all_course_run_enrollments,
            self.program.key,
        )
