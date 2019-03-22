"""
A mock version of the v1 API, providing dummy data for partner integration
testing.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_202_ACCEPTED,
    HTTP_207_MULTI_STATUS,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from registrar.apps.api.serializers import (
    AcceptedJobSerializer,
    CourseRunSerializer,
    ProgramEnrollmentRequestSerializer,
    ProgramSerializer,
)
from registrar.apps.api.v0.data import (
    FAKE_ORG_DICT,
    FAKE_ORG_PROGRAMS,
    FAKE_PROGRAM_DICT,
    FAKE_PROGRAM_COURSE_RUNS,
    FAKE_TASK_IDS_BY_PROGRAM,
    FakeTask,
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


class MockProgramEnrollmentView(CreateAPIView, RetrieveAPIView, MockProgramSpecificViewMixin):
    """
    A view for enrolling students in a program, or retrieving program enrollment data.

    Path: /api/v1/programs/{program_key}/enrollments

    Accepts: [POST, GET]

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
        "job_url": "http://localhost/api/v1/jobs/fake-job-for-hhp-masters-ce"
    }

    ------------------------------------------------------------------------------------
    POST
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
    serializer_class = ProgramEnrollmentRequestSerializer

    def post(self, request, *args, **kwargs):
        """ Enroll up to 25 students in program """
        if not self.program.managing_organization.enrollments_writeable:
            raise PermissionDenied()

        response = {}
        enrolled_students = []

        if not isinstance(request.data, list):
            raise ValidationError()

        if len(request.data) > 25:
            return Response(
                'enrollment limit 25', HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        for enrollee in request.data:
            enrollee_serializer = ProgramEnrollmentRequestSerializer(
                data=enrollee
            )

            if enrollee_serializer.is_valid():
                enrollee = enrollee_serializer.data
                student_key = enrollee['student_key']
                if student_key in enrolled_students:
                    response[student_key] = 'duplicated'
                else:
                    response[student_key] = enrollee['status']
                    enrolled_students.append(student_key)
            else:
                try:
                    if 'status' in enrollee_serializer.errors:
                        response[enrollee['student_key']] = 'invalid-status'
                    else:
                        return Response(
                            'invalid enrollemnt record',
                            HTTP_422_UNPROCESSABLE_ENTITY
                        )
                except KeyError:
                    return Response(
                        'student_key required', HTTP_422_UNPROCESSABLE_ENTITY
                    )

        if len(enrolled_students) < 1:
            return Response(response, HTTP_422_UNPROCESSABLE_ENTITY)
        if len(request.data) != len(enrolled_students):
            return Response(response, HTTP_207_MULTI_STATUS)
        else:
            return Response(response)

    def retrieve(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves program enrollment data.
        """
        if not self.program.managing_organization.enrollments_readable:
            raise PermissionDenied()

        fake_task_id = FAKE_TASK_IDS_BY_PROGRAM[self.program.key]

        # TODO: EDUCATOR-4179 This should use reverse() of the job results view.
        fake_task_url = 'http://foo/{}'.format(fake_task_id)
        fake_task = FakeTask(fake_task_id, fake_task_url)

        return Response(AcceptedJobSerializer(fake_task).data, HTTP_202_ACCEPTED)
