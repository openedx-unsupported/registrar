""" Serializers for communicating enrollment data with LMS """

from rest_framework import serializers
from registrar.apps.enrollments.constants import (
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
    Serialize enrollments into a CSV-formatted string.

    Headers are not included.

    Arguments:
        enrollments: list[dict]

    Returns: str
    """
    return '\n'.join(
        '{},{},{}'.format(
            enrollment['student_key'],
            enrollment['status'],
            str(enrollment['account_exists']).lower(),
        )
        for enrollment in enrollments
    )
