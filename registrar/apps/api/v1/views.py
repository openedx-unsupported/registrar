"""
The public-facing REST API.
"""
import logging

from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
)
from django.http import Http404
from django.shortcuts import get_object_or_404
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_202_ACCEPTED
from rest_framework.views import APIView

from registrar.apps.api import exceptions
from registrar.apps.api.constants import ENROLLMENT_WRITE_MAX_SIZE
from registrar.apps.api.mixins import (
    AuthMixin,
    CourseSpecificViewMixin,
    JobInvokerMixin,
    ProgramSpecificViewMixin,
)
import registrar.apps.api.segment as segment
from registrar.apps.api.serializers import (
    JobAcceptanceSerializer,
    JobStatusSerializer,
)
from registrar.apps.enrollments.models import Program
from registrar.apps.core import permissions as perms
from registrar.apps.core.jobs import get_job_status
from registrar.apps.core.models import Organization
from registrar.apps.enrollments.data import get_discovery_program, write_program_enrollments
from registrar.apps.enrollments.serializers import (
    CourseRunSerializer,
    DiscoveryProgramSerializer,
    ProgramEnrollmentRequestSerializer,
    ProgramSerializer,
)
from registrar.apps.enrollments.tasks import list_program_enrollments


logger = logging.getLogger(__name__)


class ProgramListView(AuthMixin, ListAPIView):
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

    def get_queryset(self):
        org_key = self.request.GET.get('org', None)
        programs = Program.objects.all()
        if org_key:
            programs = programs.filter(managing_organization__key=org_key)
        segment.track(
            self.request.user.username,
            'registrar.v1.list_programs',
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

    def get_queryset(self):
        uuid = self.program.discovery_uuid
        discovery_program = DiscoveryProgram.get(uuid)
        return discovery_program.course_runs



class ProgramEnrollmentView(ProgramSpecificViewMixin, JobInvokerMixin, APIView):
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
    # pylint: disable=unused-argument

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return JobAcceptanceSerializer
        if self.request.method == 'POST' or self.request.method == 'PATCH':
            return ProgramEnrollmentRequestSerializer(many=True)

    def get_permission_required(self, request):
        if request.method == 'GET':
            return perms.ORGANIZATION_READ_ENROLLMENTS
        if request.method == 'POST' or self.request.method == 'PATCH':
            return perms.ORGANIZATION_WRITE_ENROLLMENTS
        return []

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves program enrollment data.
        """
        return self.invoke_job(list_program_enrollments, self.program_key)

    def validate_enrollment_data(self, enrollments):
        """
        Validate enrollments request body
        """
        if not isinstance(enrollments, list):
            raise ValidationError('expected request body type: List')

        if len(enrollments) > ENROLLMENT_WRITE_MAX_SIZE:
            raise exceptions.EnrollmentPayloadTooLarge()

    def write_program_enrollments(self, request):
        """
        Handle Create/Update requests for enrollments
        """
        self.validate_enrollment_data(request.data)
        program_uuid = self.program.discovery_uuid
        discovery_program = get_discovery_program(program_uuid)

        enrollments = [{
            'student_key': enrollment.get('student_key'),
            'status': enrollment.get('status'),
            'curriculum_uuid': discovery_program.active_curriculum_uuid
        } for enrollment in request.data]

        if request.method == 'POST':
            response = write_program_enrollments(program_uuid, enrollments)
        elif request.method == 'PATCH':
            response = write_program_enrollments(program_uuid, enrollments, update=True)
        else:
            raise Exception('unexpected request method.  Expected [POST, PATCH]')

        return Response(response.json(), status=response.status_code)

    def post(self, request, program_key):
        """ POST handler """
        return self.write_program_enrollments(request)

    def patch(self, request, program_key):
        """ PATCH handler """
        return self.write_program_enrollments(request)


class CourseEnrollmentView(CourseSpecificViewMixin, JobInvokerMixin, APIView):
    """
    A view for enrolling students in a program course run.

    Path: /api/v1/programs/{program_key}/courses/{course_id}/enrollments

    Accepts: [GET]

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
    """
    # pylint: disable=unused-argument

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return JobAcceptanceSerializer

    def get_permission_required(self, request):
        if request.method == 'GET':
            return perms.ORGANIZATION_READ_ENROLLMENTS
        return []

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves course run enrollment data.
        """
        self.validate_course_id()
        return self.invoke_job(
            list_course_run_enrollments,
            self.program_key,
            self.kwargs['course_id'],
        )


class JobStatusRetrieveView(RetrieveAPIView):
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

    def get_object(self):
        try:
            job_status = get_job_status(self.request.user, self.kwargs['job_id'])
        except PermissionDenied:
            raise
        except ObjectDoesNotExist:
            raise Http404()
        return job_status
