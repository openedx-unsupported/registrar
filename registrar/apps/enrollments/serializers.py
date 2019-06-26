""" Serializers for communicating enrollment data with LMS """

from rest_framework import serializers

from registrar.apps.core.utils import serialize_to_csv
from registrar.apps.enrollments.constants import (
    COURSE_ENROLLMENT_STATUSES,
    PROGRAM_ENROLLMENT_STATUSES,
)


# pylint: disable=abstract-method


class ProgramEnrollmentSerializer(serializers.Serializer):
    """
    Serializer for program enrollment API response.
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=PROGRAM_ENROLLMENT_STATUSES)
    account_exists = serializers.BooleanField()


def serialize_program_enrollments_to_csv(enrollments):
    """
    Serialize program enrollments into a CSV-formatted string.

    Arguments:
        enrollments: list[dict]

    Returns: str
    """
    return serialize_to_csv(
        enrollments, ('student_key', 'status', 'account_exists')
    )


class CourseEnrollmentSerializer(serializers.Serializer):
    """
    Serializer for program enrollment API response.
    """
    course_key = serializers.SerializerMethodField()
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=COURSE_ENROLLMENT_STATUSES)
    account_exists = serializers.BooleanField()

    # pylint: disable=unused-argument
    def get_course_key(self, obj):
        return self.context.get('course_key')


def serialize_course_run_enrollments_to_csv(enrollments):
    """
    Serialize course run enrollments into a CSV-formatted string.

    Arguments:
        enrollments: list[dict]

    Returns: str
    """
    return serialize_to_csv(
        enrollments, ('course_key', 'student_key', 'status', 'account_exists')
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
