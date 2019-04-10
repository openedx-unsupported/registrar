"""
A mock version of the v1 API, providing dummy data for partner integration
testing.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_202_ACCEPTED,
    HTTP_207_MULTI_STATUS,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from registrar.apps.api.serializers import (
    CourseRunSerializer,
    JobAcceptanceSerializer,
    JobSerializer,
    ProgramSerializer,
    ProgramEnrollmentRequestSerializer,
    ProgramEnrollmentModificationRequestSerializer,
    CourseEnrollmentRequestSerializer,
    CourseEnrollmentModificationRequestSerializer,
)
from registrar.apps.api.v0.data import (
    invoke_fake_course_enrollment_listing_job,
    invoke_fake_program_enrollment_listing_job,
    FAKE_ORG_DICT,
    FAKE_ORG_PROGRAMS,
    FAKE_PROGRAM_DICT,
    FAKE_PROGRAM_COURSE_RUNS,
    FakeJobAcceptance,
    get_fake_job_status,
)


class MockProgramListView(ListAPIView):
    """
    A view for listing program objects.

    Path: /api/v0/programs?org={org_key}

    All programs within organization specified by `org_key` are returned.
    For users with global organization access, `org_key` can be omitted in order
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


class MockProgramSpecificViewMixin(object):
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


class MockProgramCourseSpecificViewMixin(MockProgramSpecificViewMixin):
    """
    A mixin for views that operate on or within a specific course in a program
    """

    @property
    def course(self):
        """
        The course specified by the `course_id` URL parameter.
        """
        course_id = self.kwargs['course_id']
        program_course_runs = FAKE_PROGRAM_COURSE_RUNS[self.program.key]
        course = next(filter(lambda run: run.key == course_id, program_course_runs), None)
        if course is None:
            raise Http404()
        return course


class MockProgramRetrieveView(MockProgramSpecificViewMixin, RetrieveAPIView):
    """
    A view for retrieving a single program object.

    Path: /api/v0/programs/{program_key}

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


class MockProgramCourseListView(MockProgramSpecificViewMixin, ListAPIView):
    """
    A view for listing courses in a program.

    Path: /api/v0/programs/{program_key}/courses

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = CourseRunSerializer

    def get_queryset(self):
        if self.program.managing_organization.metadata_readable:
            return FAKE_PROGRAM_COURSE_RUNS[self.program.key]
        else:
            raise PermissionDenied()


class EchoStatusesMixin(object):
    """
    Provides the validate_and_echo_statuses function
    Classes that inherit from EchoStatusesMixin must implement get_serializer_class
    """

    def validate_and_echo_statuses(self, request):
        """ Enroll up to 25 students in program/course """
        if not self.program.managing_organization.enrollments_writeable:
            raise PermissionDenied()

        if not isinstance(request.data, list):
            raise ValidationError()

        if len(request.data) > 25:
            return Response(
                'enrollment limit 25', HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        results = {}
        enrolled_students = set()

        for enrollee in request.data:
            enrollee_serializer = self.get_serializer_class()(data=enrollee)
            if enrollee_serializer.is_valid():
                enrollee = enrollee_serializer.data
                student_id = enrollee["student_key"]
                if student_id in enrolled_students:
                    results[student_id] = 'duplicated'
                else:
                    results[student_id] = enrollee['status']
                    enrolled_students.add(student_id)
            else:
                try:
                    if 'status' in enrollee_serializer.errors and \
                            enrollee_serializer.errors['status'][0].code == 'invalid_choice':
                        results[enrollee["student_key"]] = 'invalid-status'
                    else:
                        return Response(
                            'invalid enrollment record',
                            HTTP_422_UNPROCESSABLE_ENTITY
                        )
                except KeyError:
                    return Response(
                        'student key required', HTTP_422_UNPROCESSABLE_ENTITY
                    )

        if not enrolled_students:
            return Response(results, HTTP_422_UNPROCESSABLE_ENTITY)
        if len(request.data) != len(enrolled_students):
            return Response(results, HTTP_207_MULTI_STATUS)
        else:
            return Response(results)


class MockProgramEnrollmentView(APIView, MockProgramSpecificViewMixin, EchoStatusesMixin):
    """
    A view for enrolling students in a program, or retrieving/modifying program enrollment data.

    Path: /api/v0/programs/{program_key}/enrollments

    Accepts: [POST, PATCH, GET]

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
        "job_id": "fake-job-for-hhp-masters-ce",
        "job_url": "http://localhost/api/v0/jobs/fake-job-for-hhp-masters-ce"
    }

    ------------------------------------------------------------------------------------
    POST / PATCH
    ------------------------------------------------------------------------------------

    Returns:
     * 200: Returns a map of students and their enrollment status.
     * 207: Not all students enrolled. Returns resulting enrollment status.
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
     * 413: Payload too large, over 25 students supplied.
     * 422: Invalid request, unable to enroll students.
    """
    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProgramEnrollmentRequestSerializer
        elif self.request.method == 'PATCH':
            return ProgramEnrollmentModificationRequestSerializer

    def post(self, request, *args, **kwargs):
        return self.validate_and_echo_statuses(request)

    def patch(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return self.validate_and_echo_statuses(request)

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves program enrollment data.
        """
        if not self.program.managing_organization.enrollments_readable:
            raise PermissionDenied()

        fake_job_id = invoke_fake_program_enrollment_listing_job(
            self.program.key, self.request.build_absolute_uri()
        )
        fake_job_url = self.request.build_absolute_uri(
            reverse('api:v0:job-status', kwargs={'job_id': fake_job_id})
        )
        fake_job_acceptance = FakeJobAcceptance(fake_job_id, fake_job_url)

        return Response(
            JobAcceptanceSerializer(fake_job_acceptance).data,
            HTTP_202_ACCEPTED,
        )


class MockCourseEnrollmentView(APIView, MockProgramCourseSpecificViewMixin, EchoStatusesMixin):
    """
    A view for enrolling students in a course.

    Path: /api/v0/programs/{program_key}/courses/{course_id}/enrollments

    Accepts: [POST]

    ------------------------------------------------------------------------------------
    POST / PATCH
    ------------------------------------------------------------------------------------

    Returns:
     * 200: Returns a map of students and their enrollment status.
     * 207: Not all students enrolled. Returns resulting enrollment status.
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist, or course does not exist in program
     * 413: Payload too large, over 25 students supplied.
     * 422: Invalid request, unable to enroll students.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CourseEnrollmentRequestSerializer
        elif self.request.method == 'PATCH':
            return CourseEnrollmentModificationRequestSerializer

    def post(self, request, *args, **kwargs):
        self.course  # trigger 404  # pylint: disable=pointless-statement
        return self.validate_and_echo_statuses(request)

    def patch(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        self.course  # trigger 404  # pylint: disable=pointless-statement
        return self.validate_and_echo_statuses(request)

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves course enrollment data.
        """
        if not self.program.managing_organization.enrollments_readable:
            raise PermissionDenied()

        fake_job_id = invoke_fake_course_enrollment_listing_job(
            self.program.key, self.course.key, self.request.build_absolute_uri()
        )
        fake_job_url = self.request.build_absolute_uri(
            reverse('api:v0:job-status', kwargs={'job_id': fake_job_id})
        )
        fake_job_acceptance = FakeJobAcceptance(fake_job_id, fake_job_url)

        return Response(
            JobAcceptanceSerializer(fake_job_acceptance).data,
            HTTP_202_ACCEPTED,
        )


class MockJobStatusRetrieveView(RetrieveAPIView):
    """
    A view for getting the status of a job.

    Path: /api/v0/jobs/{job_id}

    Accepts: [GET]

    Returns:
     * 200: Returns the status of the job
     * 404: Invalid job ID

    Example:
    {
        "original_url":
            "http://localhost/api/v0/programs/dvi-mba/enrollments/",
        "created": "2019-03-27T18:19:19.189272Z",
        "state": "Succeeded",
        "result":
            "http://localhost/static/api/v0/program-enrollments/thirty.json"
    }
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = JobSerializer

    def get_object(self):
        job_id = self.kwargs.get('job_id')
        job_status = get_fake_job_status(job_id, self.request.build_absolute_uri)
        if job_status:
            return job_status
        else:
            raise Http404
