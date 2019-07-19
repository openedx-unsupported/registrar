"""
A mock version of the v1 API, providing dummy data for partner integration
testing.
"""
from django.core.exceptions import PermissionDenied
from django.http import Http404
from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
)
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_202_ACCEPTED,
    HTTP_207_MULTI_STATUS,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_422_UNPROCESSABLE_ENTITY,
)
from rest_framework.views import APIView

from registrar.apps.api.mixins import TrackViewMixin
from registrar.apps.api.serializers import (
    CourseEnrollmentModificationRequestSerializer,
    CourseEnrollmentRequestSerializer,
    CourseRunSerializer,
    JobAcceptanceSerializer,
    JobStatusSerializer,
    ProgramEnrollmentModificationRequestSerializer,
    ProgramEnrollmentRequestSerializer,
    ProgramSerializer,
)
from registrar.apps.api.utils import build_absolute_api_url
from registrar.apps.api.v1_mock.data import (
    FAKE_ORG_DICT,
    FAKE_ORG_PROGRAMS,
    FAKE_PROGRAM_COURSE_RUNS,
    FAKE_PROGRAM_DICT,
    FAKE_PROGRAMS,
    FakeJobAcceptance,
    get_fake_job_status,
    invoke_fake_course_enrollment_listing_job,
    invoke_fake_program_enrollment_listing_job,
)
from registrar.apps.core import permissions as perms


def global_read_metadata_perm(user):
    """
    Returns True iff the given user has the `ORGANIZATION_READ_METADATA`
    perm on all objects.
    """
    return user.has_perm(perms.ORGANIZATION_READ_METADATA)


class MockProgramListView(TrackViewMixin, ListAPIView):
    """
    A view for listing program objects.

    Path: /api/v1-mock/programs?org={org_key}

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
    event_method_map = {'GET': 'registrar.v1_mock.list_programs'}
    event_parameter_map = {'org': 'organization_filter'}

    @property
    def org_key(self):
        return self.request.GET.get('org', None)

    @property
    def organization(self):
        return FAKE_ORG_DICT.get(self.org_key) if self.org_key else None

    def check_permissions(self, request):
        """
        Checks permissions against self.permission_classes.  Also checks
        if the requesting user has metadata read permissions on the requested programs,
        raising a 403 unless the requesting user has global metadata read permissions.
        """
        super().check_permissions(request)
        if not self.org_key and global_read_metadata_perm(request.user):
            return
        elif not self.org_key:
            self.add_tracking_data(
                missing_permissions=[perms.ORGANIZATION_READ_METADATA]
            )
            raise PermissionDenied()
        elif self.organization and not self.organization.metadata_readable:
            if global_read_metadata_perm(request.user):
                return
            self.add_tracking_data(
                missing_permissions=[perms.ORGANIZATION_READ_METADATA]
            )
            raise PermissionDenied()

    def get_queryset(self):
        if not self.org_key:
            # We've already checked permissions, so if we've made it here
            # without an org_key, the requesting user must have global
            # metadata read permissions
            return FAKE_PROGRAMS
        if not self.organization:
            self.add_tracking_data(failure='org_not_found')
            raise Http404()
        return FAKE_ORG_PROGRAMS[self.org_key]


class MockProgramSpecificViewMixin(TrackViewMixin):
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
            self.add_tracking_data(failure='program_not_found')
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
            self.add_tracking_data(failure='course_not_found')
            raise Http404()
        return course


class MockProgramRetrieveView(MockProgramSpecificViewMixin, RetrieveAPIView):
    """
    A view for retrieving a single program object.

    Path: /api/v1-mock/programs/{program_key}

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = ProgramSerializer
    event_method_map = {'GET': 'registrar.v1_mock.get_program_detail'}
    event_parameter_map = {'program_key': 'program_key'}

    def get_object(self):
        if self.program.managing_organization.metadata_readable:
            return self.program
        else:
            self.add_tracking_data(
                missing_permissions=[perms.ORGANIZATION_READ_METADATA]
            )
            raise PermissionDenied()


class MockProgramCourseListView(MockProgramSpecificViewMixin, ListAPIView):
    """
    A view for listing courses in a program.

    Path: /api/v1-mock/programs/{program_key}/courses

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = CourseRunSerializer
    event_method_map = {'GET': 'registrar.v1_mock.get_program_courses'}
    event_parameter_map = {'program_key': 'program_key'}

    def get_queryset(self):
        if self.program.managing_organization.metadata_readable:
            return FAKE_PROGRAM_COURSE_RUNS[self.program.key]
        else:
            self.add_tracking_data(
                missing_permissions=[perms.ORGANIZATION_READ_METADATA]
            )
            raise PermissionDenied()


class EchoStatusesMixin(TrackViewMixin):
    """
    Provides the validate_and_echo_statuses function
    Classes that inherit from EchoStatusesMixin must implement get_serializer_class
    and trackViewMixin
    """

    def validate_and_echo_statuses(self, request):
        """ Enroll up to 25 students in program/course """

        if not self.program.managing_organization.enrollments_writeable:
            self.add_tracking_data(
                missing_permissions=[perms.ORGANIZATION_WRITE_ENROLLMENTS]
            )
            raise PermissionDenied()

        if not isinstance(request.data, list):
            self.add_tracking_data(failure='unprocessable_entity')
            raise ValidationError()

        if len(request.data) > 25:
            self.add_tracking_data(failure='request_entity_too_large')
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
                        self.add_tracking_data(failure='unprocessable_entity')
                        return Response(
                            'invalid enrollment record',
                            HTTP_422_UNPROCESSABLE_ENTITY
                        )
                except KeyError:
                    self.add_tracking_data(failure='unprocessable_entity')
                    return Response(
                        'invalid enrollment record', HTTP_422_UNPROCESSABLE_ENTITY
                    )

        if not enrolled_students:
            self.add_tracking_data(failure='unprocessable_entity')
            return Response(results, HTTP_422_UNPROCESSABLE_ENTITY)
        if len(enrolled_students) != len(request.data):
            return Response(results, HTTP_207_MULTI_STATUS)
        else:
            return Response(results)


class MockProgramEnrollmentView(MockProgramSpecificViewMixin, EchoStatusesMixin, APIView):
    """
    A view for enrolling students in a program, or retrieving/modifying program enrollment data.

    Path: /api/v1-mock/programs/{program_key}/enrollments

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
        "job_url": "http://localhost/api/v1-mock/jobs/fake-job-for-hhp-masters-ce"
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
    event_method_map = {
        'GET': 'registrar.v1_mock.get_program_enrollment',
        'POST': 'registrar.v1_mock.post_program_enrollment',
        'PATCH': 'registrar.v1_mock.patch_program_enrollment',
    }
    event_parameter_map = {'program_key': 'program_key'}

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProgramEnrollmentRequestSerializer
        elif self.request.method == 'PATCH':  # pragma: no branch
            return ProgramEnrollmentModificationRequestSerializer

    def post(self, request, *args, **kwargs):
        """
        The view to handle the POST method on program enrollments
        """
        return self.validate_and_echo_statuses(request)

    def patch(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        The view to handle the PATCH method on program enrollments
        """
        return self.validate_and_echo_statuses(request)

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves program enrollment data.
        """
        if not self.program.managing_organization.enrollments_readable:
            self.add_tracking_data(
                missing_permissions=[perms.ORGANIZATION_READ_ENROLLMENTS]
            )
            raise PermissionDenied()

        fake_job_id = invoke_fake_program_enrollment_listing_job(
            self.program.key
        )
        fake_job_url = build_absolute_api_url(
            'api:v1-mock:job-status', job_id=fake_job_id
        )
        fake_job_acceptance = FakeJobAcceptance(fake_job_id, fake_job_url)

        return Response(
            JobAcceptanceSerializer(fake_job_acceptance).data,
            HTTP_202_ACCEPTED,
        )


class MockCourseEnrollmentView(MockProgramCourseSpecificViewMixin, EchoStatusesMixin, APIView):
    """
    A view for enrolling students in a course.

    Path: /api/v1-mock/programs/{program_key}/courses/{course_id}/enrollments

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
    event_method_map = {
        'GET': 'registrar.v1_mock.get_course_enrollment',
        'POST': 'registrar.v1_mock.post_course_enrollment',
        'PATCH': 'registrar.v1_mock.patch_course_enrollment',
    }
    event_parameter_map = {
        'program_key': 'program_key',
        'course_id': 'course_id',
    }

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CourseEnrollmentRequestSerializer
        elif self.request.method == 'PATCH':  # pragma: no branch
            return CourseEnrollmentModificationRequestSerializer

    def post(self, request, *args, **kwargs):
        """
        The view to handle the POST method on course enrollments
        """
        self.course  # trigger 404  # pylint: disable=pointless-statement
        return self.validate_and_echo_statuses(request)

    def patch(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        The view to handle the PATCH method on course enrollments
        """
        self.course  # trigger 404  # pylint: disable=pointless-statement
        return self.validate_and_echo_statuses(request)

    def get(self, request, *args, **kwargs):
        """
        Submit a user task that retrieves course enrollment data.
        """
        if not self.program.managing_organization.enrollments_readable:
            self.add_tracking_data(
                missing_permissions=[perms.ORGANIZATION_READ_ENROLLMENTS]
            )
            raise PermissionDenied()

        self.course  # trigger 404  # pylint: disable=pointless-statement

        fake_job_id = invoke_fake_course_enrollment_listing_job(
            self.program.key, self.course.key
        )
        fake_job_url = build_absolute_api_url(
            'api:v1-mock:job-status', job_id=fake_job_id
        )
        fake_job_acceptance = FakeJobAcceptance(fake_job_id, fake_job_url)

        return Response(
            JobAcceptanceSerializer(fake_job_acceptance).data,
            HTTP_202_ACCEPTED,
        )


class MockJobStatusRetrieveView(TrackViewMixin, RetrieveAPIView):
    """
    A view for getting the status of a job.

    Path: /api/v1-mock/jobs/{job_id}

    Accepts: [GET]

    Returns:
     * 200: Returns the status of the job
     * 404: Invalid job ID

    Example:
    {
        "created": "2019-03-27T18:19:19.189272Z",
        "state": "Succeeded",
        "result":
            "http://localhost/static/api/v1-mock/program-enrollments/thirty.json"
    }
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = JobStatusSerializer
    event_method_map = {'GET': 'registrar.v1_mock.get_job_status'}
    event_parameter_map = {'job_id': 'job_id'}

    def get_object(self):
        job_id = self.kwargs.get('job_id')
        job_status = get_fake_job_status(job_id, self.request.build_absolute_uri)
        if job_status:
            self.add_tracking_data(job_state=job_status.state)
            return job_status
        else:
            self.add_tracking_data(failure='job_not_found')
            raise Http404
