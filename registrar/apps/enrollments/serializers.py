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
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=COURSE_ENROLLMENT_STATUSES)
    account_exists = serializers.BooleanField()


def serialize_course_run_enrollments_to_csv(enrollments):
    """
    Serialize course run enrollments into a CSV-formatted string.

    Arguments:
        enrollments: list[dict]

    Returns: str
    """
    return serialize_to_csv(
        enrollments, ('student_key', 'status', 'account_exists')
    )
