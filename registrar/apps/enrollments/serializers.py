""" Serializers for communicating enrollment data with LMS """

from rest_framework import serializers

from registrar.apps.core.csv_utils import serialize_to_csv

from .constants import COURSE_ENROLLMENT_STATUSES, PROGRAM_ENROLLMENT_STATUSES


# pylint: disable=abstract-method


class ProgramEnrollmentSerializer(serializers.Serializer):
    """
    Serializer for program enrollment API response.
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=PROGRAM_ENROLLMENT_STATUSES)
    account_exists = serializers.BooleanField()


class ProgramEnrollmentWithUsernameEmailSerializer(ProgramEnrollmentSerializer):
    """
    Serializer for program enrollment API response that includes username and email.
    """
    username = serializers.CharField(allow_blank=True)
    email = serializers.CharField(allow_blank=True)


def serialize_program_enrollments_to_csv(enrollments, include_username_email=False):
    """
    Serialize program enrollments into a CSV-formatted string.

    Arguments:
        enrollments: list[dict]

    Returns: str
    """
    if include_username_email:
        field_names = ('student_key', 'status', 'account_exists', 'username', 'email')
    else:
        field_names = ('student_key', 'status', 'account_exists')

    return serialize_to_csv(
        enrollments,
        field_names,
        include_headers=True,
    )


class CourseEnrollmentSerializer(serializers.Serializer):
    """
    Serializer for program enrollment API response.
    """
    course_id = serializers.SerializerMethodField()
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=COURSE_ENROLLMENT_STATUSES)
    account_exists = serializers.BooleanField()

    # pylint: disable=unused-argument
    def get_course_id(self, obj):
        return self.context.get('course_id')


class CourseEnrollmentWithCourseStaffSerializer(CourseEnrollmentSerializer):
    """
    Serializer for program course enrollment API response which includes course_staff.
    """
    course_staff = serializers.BooleanField()


def serialize_course_run_enrollments_to_csv(enrollments):
    """
    Serialize course run enrollments into a CSV-formatted string.

    Arguments:
        enrollments: list[dict]

    Returns: str
    """
    return serialize_to_csv(
        enrollments,
        ('course_id', 'student_key', 'status', 'account_exists'),
        include_headers=True,
    )


def serialize_course_run_enrollments_with_course_staff_to_csv(enrollments):
    """
    Serialize course run enrollments (course_staff field included) into a CSV-formatted string.

    Arguments:
        enrollments: list[dict]

    Returns: str
    """
    return serialize_to_csv(
        enrollments,
        ('course_id', 'student_key', 'status', 'account_exists', 'course_staff'),
        include_headers=True,
    )


def serialize_enrollment_results_to_csv(enrollment_results):
    """
    Serialize enrollment results into a CSV-formatted string.

    Arguments:
        enrollment_results (dict[str: str]):
            Mapping from student keys to enrollment statuses.

    Returns: str
    """
    enrollment_results_list = [
        {
            "student_key": student_key,
            "status": status,
        }
        for student_key, status in enrollment_results.items()
    ]
    return serialize_to_csv(
        enrollment_results_list, ('student_key', 'status'), include_headers=True
    )
