"""
The public-facing REST API.
"""
import json
import logging
import re
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from django.utils.functional import cached_property
from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
)
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ParseError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_409_CONFLICT
from rest_framework.views import APIView

from registrar.apps.api.constants import (
    ENROLLMENT_PERMISSIONS_LIST,
    LEGACY_PERMISSION_QUERY_PARAMS,
    UPLOAD_FILE_MAX_SIZE,
)
from registrar.apps.api.exceptions import FileTooLarge
from registrar.apps.api.mixins import TrackViewMixin
from registrar.apps.api.serializers import (
    CourseRunSerializer,
    JobStatusSerializer,
    ProgramReportMetadataSerializer,
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
from registrar.apps.core.filestore import get_program_reports_filestore
from registrar.apps.core.jobs import (
    get_job_status,
    get_processing_jobs_for_user,
)
from registrar.apps.core.models import Organization, Program
from registrar.apps.core.permissions import APIReadMetadataPermission
from registrar.apps.core.utils import (
    get_user_api_permissions,
    load_records_from_uploaded_csv,
)
from registrar.apps.enrollments.data import DiscoveryProgram
from registrar.apps.enrollments.tasks import (
    list_all_course_run_enrollments,
    list_course_run_enrollments,
    list_program_enrollments,
    write_course_run_enrollments,
    write_program_enrollments,
)
from registrar.apps.enrollments.utils import is_enrollment_write_blocked
from registrar.apps.grades.tasks import get_course_run_grades


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
        user = self.request.user

        if self.organization_filter:
            programs = programs.filter(
                managing_organization=self.organization_filter
            )

        if self.permission_filter:
            required_permission = self.permission_filter
        else:
            required_permission = APIReadMetadataPermission

        programs = (
            program for program in programs
            if required_permission in get_user_api_permissions(user, program).union(
                get_user_api_permissions(user, program.managing_organization)
            )
        )
        # Filter out programs with enrollments disabled if the user requested
        # permission filter to operate on enrollments
        if self.permission_filter in ENROLLMENT_PERMISSIONS_LIST:
            programs = [program for program in programs if program.is_enrollment_enabled]
        return programs

    def get_required_permissions(self, _request):
        """
        Return a list of required permissions.
        Here an empty list is returned because for this endpoint, permission check is done in get_queryset.
        """
        return []

    def get_permission_objects(self):
        """
        Returns a list of objects against which permissions should be checked.
        Here an empty list is returned because for this endpoint, permission check is done in get_queryset.
        """
        return []

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
        Return a list of ApiPermissionBase by which results will be filtered,
        or None if no filter specified.

        Raises 404 for bad permission query param.
        """
        perm_query_param = self.request.GET.get('user_has_perm', None)
        if not perm_query_param:
            return None

        try:
            return next(p for p in perms.API_PERMISSIONS if p.name == perm_query_param)
        except StopIteration:
            # maintains functionality with the currently deployed version of the UI
            # and can be removed once these query params are no loger in use
            if perm_query_param in LEGACY_PERMISSION_QUERY_PARAMS:
                return LEGACY_PERMISSION_QUERY_PARAMS[perm_query_param]
            else:
                self.add_tracking_data(failure='no_such_perm')
                raise Http404()


class ProgramRetrieveView(ProgramSpecificViewMixin, RetrieveAPIView):
    """
    A view for retrieving a single program object.

    Path: /api/[version]/programs/{program_key}

    Returns:
     * 200: OK
     * 403: User lacks read access to the specified program.
     * 404: Program does not exist.
    """
    serializer_class = ProgramSerializer
    permission_required = [perms.APIReadMetadataPermission]
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
     * 403: User lacks read access to the specified program.
     * 404: Program does not exist.
    """
    serializer_class = CourseRunSerializer
    permission_required = [perms.APIReadMetadataPermission]
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
     * 403: User lacks enrollment read access to the specified program.
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
     * 403: User lacks enrollment write access to the specified program.
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
     * 403: User lacks enrollment read access to the program of specified course run.
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
     * 403: User lacks enrollment write access to the  specified program.
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
        'course_id': 'course_id',
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
    field_names = set()  # Override in subclass
    task_fn = None  # Override in subclass

    def post(self, request, *args, **kwargs):
        """ POST handler """
        if 'file' not in request.data:
            raise ParseError('No file content uploaded')

        csv_file = request.data['file']
        if csv_file.size > UPLOAD_FILE_MAX_SIZE:
            raise FileTooLarge()

        if is_enrollment_write_blocked(self.program.key):
            return Response('Job already in progress for program', HTTP_409_CONFLICT)

        enrollments = load_records_from_uploaded_csv(csv_file, self.field_names)
        return self.invoke_upload_job(self.task_fn, json.dumps(enrollments), *args, **kwargs)


class ProgramEnrollmentUploadView(EnrollmentMixin, EnrollmentUploadView):
    """
    A view for uploading program enrollments via csv file

    Path: /api/[version]/programs/{program_key}/enrollments
    """
    field_names = {'student_key', 'status'}
    task_fn = write_program_enrollments
    event_method_map = {'POST': 'registrar.{api_version}.upload_program_enrollments'}
    event_parameter_map = {'program_key': 'program_key'}


class CourseRunEnrollmentUploadView(EnrollmentMixin, CourseSpecificViewMixin, EnrollmentUploadView):
    """
    A view for uploading course enrollments via csv file

    Path: /api/[version]/programs/{program_key}/course_enrollments
    """
    field_names = {'student_key', 'course_id', 'status'}
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


class CourseGradesView(CourseSpecificViewMixin, JobInvokerMixin, APIView):
    """
    Invokes a Django User Task that retrieves student grade data for the given course run.

    Returns:
     * 202: Accepted, an asynchronous job was successfully started.
     * 401: User is not authenticated
     * 403: User lacks enrollment read access to organization of specified program
     * 404: Program was not found, course was not found, or course was not found in program.

    Example Response:
    {
        "job_id": "3b985cec-dcf4-4d38-9498-8545ebcf5d0f",
        "job_url": "http://localhost/api/[version]/jobs/3b985cec-dcf4-4d38-9498-8545ebcf5d0f"
    }

    Path: /api/[version]/programs/{program_key}/courses/{course_id}/grades
    """
    permission_required = [perms.APIReadEnrollmentsPermission]
    event_method_map = {
        'GET': 'registrar.v1.get_course_grades',
    }
    event_parameter_map = {
        'program_key': 'program_key',
        'course_id': 'course_id',
        'fmt': 'result_format',
    }

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves course grade data for the given course
        """
        return self.invoke_download_job(
            get_course_run_grades,
            self.program.key,
            self.internal_course_key,
        )


class ReportsListView(ProgramSpecificViewMixin, APIView):
    """
    A view for listing metadata about reports for a program.

    Path: /api/[version]/programs/{program_key}/reports?min_created_date={min_created_date}

    Example Response:
    [
        {
            "name":"individual_report__2019-12-11.txt",
            "created_date":"2019-12-11",
            "download_url":null
        },
        {
            "name":"aggregate_report__2019-12-12.txt",
            "created_date":"2019_12_12",
            "download_url":null
        },
        {
            "name":"individual_report__2019-12-12.txt",
            "created_date":"2019-12-12",
            "download_url":null
        }
    ]

    Returns:
     * 200: Returns a list of metadata about available reports for a program.
     * 401: User is not authenticated.
     * 403: User is not authorized to view program reports.
     * 404: Program does not exist.
    """
    event_method_map = {
        'GET': 'registrar.v1.list_program_reports',
    }
    event_parameter_map = {
        'program_key': 'program_key',
        'min_created_date': 'min_created_date',
    }
    permission_required = [perms.APIReadReportsPermission]

    def get(self, request, *args, **kwargs):
        """
        Get a list of reports for a program.
        """
        filestore = get_program_reports_filestore()
        file_prefix = '{}/{}'.format(self.program.managing_organization.key, self.program.discovery_uuid.hex)
        date_format_string = '%Y-%m-%d'

        reports_metadata = []

        # list method of the filestore returns a 2-tuple containing a
        # list of directories and a list of files on the path, respectively,
        # so iterate the list of files
        reports = filestore.list(file_prefix)[1]

        for report_name in reports:
            report_metadata = {
                'name': report_name,
                'created_date': self._get_file_created_date(
                    report_name, date_format_string,
                ),
            }
            reports_metadata.append(report_metadata)

        if 'min_created_date' in request.query_params:
            min_created_date = datetime.strptime(
                request.query_params['min_created_date'],
                date_format_string
            )

            reports_metadata = [
                r for r
                in reports_metadata
                if r['created_date'] is not None and
                datetime.strptime(r['created_date'], date_format_string) >= min_created_date
            ]

        # wait to generate the download url until after we've done any filtering
        # to avoid generating unnecessary urls
        for report in reports_metadata:
            report['download_url'] = filestore.get_url('{}/{}'.format(file_prefix, report['name']))

        serializer = ProgramReportMetadataSerializer(reports_metadata, many=True)
        return Response(serializer.data)

    def _get_file_created_date(self, filename, date_format_string):
        """
        Return the date the file was created based on the date in the filename.

        Parameters:
            - filename: the name of the file
            - date_format_string: a string representing the expected format of dates

        Returns:
            - String: the date the file was created as a formatted string that matches date_format_string
            - None: if the date is not in the filename or the date is misformatted
        """
        # pull out the date string from the filename
        pattern = re.compile(r'.*__(\d*-\d*-\d*)[.]*\w*')
        match = pattern.match(filename)

        if match is None:
            # if the filename is not as expected, return None
            self._log_invalid_filename(filename)
            return None

        date_string = match.group(1)

        try:
            # validate that the date is actually a date; otherwise,
            # return None
            date = datetime.strptime(date_string, date_format_string)
        except ValueError:
            self._log_invalid_filename(filename)
            return None
        return datetime.strftime(date, date_format_string)

    def _log_invalid_filename(self, filename):
        logger.warning('Filename {} is not in the expected format: report_name__YYYY-MM-DD.extension.'.format(filename))
