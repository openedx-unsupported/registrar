"""
The public-facing REST API.
"""
import logging

from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
)
from django.http import Http404
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from registrar.apps.api.mixins import TrackViewMixin
from registrar.apps.api.v1.mixins import (
    AuthMixin,
    CourseSpecificViewMixin,
    EnrollmentMixin,
    JobInvokerMixin,
    ProgramSpecificViewMixin,
)
from registrar.apps.api.serializers import (
    CourseRunSerializer,
    JobStatusSerializer,
    ProgramSerializer,
)
from registrar.apps.enrollments.models import Program
from registrar.apps.core import permissions as perms
from registrar.apps.core.jobs import get_job_status
from registrar.apps.core.models import Organization
from registrar.apps.enrollments.data import (
    DiscoveryProgram,
    write_program_enrollments,
    write_program_course_enrollments,
)
from registrar.apps.enrollments.tasks import (
    list_course_run_enrollments,
    list_program_enrollments,
)

logger = logging.getLogger(__name__)


class ProgramListView(AuthMixin, TrackViewMixin, ListAPIView):
    """
    A view for listing program objects.

    Path: /api/v1/programs?org={org_key}

    All programs within organization specified by `org_key` are returned.
    For users will global organization access, `org_key` can be omitted in order
    to return all programs.

    Returns:
     * 200: OK
     * 403: User lacks read access to specified organization.
     * 404: Organization does not exist.
    """

    serializer_class = ProgramSerializer
    permission_required = perms.ORGANIZATION_READ_METADATA
    event_method_map = {'GET': 'registrar.v1.list_programs'}
    event_parameter_map = {'org': 'organization_filter'}

    def get_queryset(self):
        org_key = self.request.GET.get('org', None)
        programs = Program.objects.all()
        if org_key:
            programs = programs.filter(managing_organization__key=org_key)
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
            try:
                return Organization.objects.get(key=org_key)
            except Organization.DoesNotExist:
                self.add_tracking_data(failure='org_not_found')
                raise Http404()
        else:
            # By returning None, Guardian will check for global Organization
            # access instead of access against a specific Organization
            return None


class ProgramRetrieveView(ProgramSpecificViewMixin, RetrieveAPIView):
    """
    A view for retrieving a single program object.

    Path: /api/v1/programs/{program_key}

    Returns:
     * 200: OK
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """
    serializer_class = ProgramSerializer
    permission_required = perms.ORGANIZATION_READ_METADATA
    event_method_map = {'GET': 'registrar.v1.get_program_detail'}
    event_parameter_map = {'program_key': 'program_key'}

    def get_object(self):
        return self.program


class ProgramCourseListView(ProgramSpecificViewMixin, ListAPIView):
    """
    A view for listing courses in a program.

    Path: /api/v1/programs/{program_key}/courses

    Returns:
     * 200: OK
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """
    serializer_class = CourseRunSerializer
    permission_required = perms.ORGANIZATION_READ_METADATA
    event_method_map = {'GET': 'registrar.v1.get_program_courses'}
    event_parameter_map = {'program_key': 'program_key'}

    def get_queryset(self):
        uuid = self.program.discovery_uuid
        discovery_program = DiscoveryProgram.get(uuid)
        return discovery_program.course_runs


class ProgramEnrollmentView(EnrollmentMixin, JobInvokerMixin, APIView):
    """
    A view for enrolling students in a program, or retrieving/modifying program enrollment data.

    Path: /api/v1/programs/{program_key}/enrollments

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
        "job_url": "http://localhost/api/v1/jobs/3b985cec-dcf4-4d38-9498-8545ebcf5d0f"
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
        'GET': 'registrar.v1.get_program_enrollment',
        'POST': 'registrar.v1.post_program_enrollment',
        'PATCH': 'registrar.v1.patch_program_enrollment',
    }
    event_parameter_map = {
        'program_key': 'program_key',
        'fmt': 'result_format',
    }

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves program enrollment data.
        """
        return self.invoke_job(list_program_enrollments, self.program.key)

    def handle_program_enrollments(self, request):
        """
        Handle Create/Update requests for enrollments
        """
        self.validate_enrollment_data(request.data)
        program_uuid = self.program.discovery_uuid
        discovery_program = DiscoveryProgram.get(program_uuid)

        enrollments = [
            {
                'student_key': enrollment.get('student_key'),
                'status': enrollment.get('status'),
                'curriculum_uuid': discovery_program.active_curriculum_uuid
            }
            for enrollment in request.data
        ]

        if request.method == 'POST':
            response = write_program_enrollments(program_uuid, enrollments)
        elif request.method == 'PATCH':
            response = write_program_enrollments(program_uuid, enrollments, update=True)
        else:
            raise Exception('unexpected request method.  Expected [POST, PATCH]')  # pragma: no cover

        self.add_tracking_data_from_lms_response(response)
        return Response(response.json(), status=response.status_code)

    def post(self, request, program_key):
        """ POST handler """
        return self.handle_program_enrollments(request)

    def patch(self, request, program_key):  # pylint: disable=unused-argument
        """ PATCH handler """
        return self.handle_program_enrollments(request)


class CourseEnrollmentView(CourseSpecificViewMixin, JobInvokerMixin, EnrollmentMixin, APIView):
    """
    A view for enrolling students in a program course run.

    Path: /api/v1/programs/{program_key}/courses/{course_id}/enrollments

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
        "job_url": "http://localhost/api/v1/jobs/3b985cec-dcf4-4d38-9498-8545ebcf5d0f"
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
        'GET': 'registrar.v1.get_course_enrollment',
        'POST': 'registrar.v1.post_course_enrollment',
        'PATCH': 'registrar.v1.patch_course_enrollment',
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
        self.validate_course_id()
        return self.invoke_job(
            list_course_run_enrollments,
            self.program.key,
            self.kwargs['course_id'],
        )

    def handle_program_course_enrollments(self, request, course_id):
        """
        Handle create/update requests for program/course enrollments
        """
        self.validate_enrollment_data(request.data)
        program_uuid = self.program.discovery_uuid

        enrollments = request.data

        if request.method == 'POST':
            response = write_program_course_enrollments(program_uuid, course_id, enrollments)
        elif request.method == 'PATCH':
            response = write_program_course_enrollments(program_uuid, course_id, enrollments, update=True)
        else:
            raise Exception('unexpected request method.  Expected [POST, PATCH]')  # pragma: no cover

        self.add_tracking_data_from_lms_response(response)
        return Response(response.json(), status=response.status_code)

    # pylint: disable=unused-argument
    def post(self, request, program_key, course_id):
        """ POST handler """
        return self.handle_program_course_enrollments(request, course_id)

    def patch(self, request, program_key, course_id):
        """ PATCH handler """
        return self.handle_program_course_enrollments(request, course_id)


class JobStatusRetrieveView(TrackViewMixin, RetrieveAPIView):
    """
    A view for getting the status of a job.

    Path: /api/v1/jobs/{job_id}

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
    event_method_map = {'GET': 'registrar.v1.get_job_status'}
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
