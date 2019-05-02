""" Serializers for communicating enrollment data with LMS """

from rest_framework import serializers

from registrar.apps.core.utils import serialize_to_csv
from registrar.apps.enrollments.constants import (
    PROGRAM_ENROLLMENT_STATUSES,
    COURSE_ENROLLMENT_STATUSES,
)
from registrar.apps.enrollments.models import Program
from registrar.apps.enrollments.utils import get_active_curriculum


# pylint: disable=abstract-method


class ProgramSerializer(serializers.ModelSerializer):
    """
    Serializer for Programs.
    """
    program_key = serializers.CharField(source='key')
    program_title = serializers.CharField(source='title')
    program_url = serializers.URLField(source='url')

    class Meta:
        model = Program
        fields = ('program_key', 'program_title', 'program_url')


class CourseRunSerializer(serializers.Serializer):
    """
    Serializer for course runs from discovery program GET response.
    """
    course_id = serializers.CharField(source='key')
    course_title = serializers.CharField(source='title')
    course_url = serializers.URLField(source='marketing_url')


class CourseSerializer(serializers.Serializer):
    """
    Serializer for courses from discovery program GET response.
    """
    course_runs = CourseRunSerializer(many=True)


class CurriculumSerializer(serializers.Serializer):
    """
    Serializer for curricula from discovery program GET response.
    """
    uuid = serializers.UUIDField()
    is_active = serializers.BooleanField()
    courses = CourseSerializer(many=True)


class DiscoveryProgramSerializer(serializers.Serializer):
    """
    Serializer for discovery program GET response.
    """
    curricula = CurriculumSerializer(many=True)

    def validate_curricula(self, curricula):
        if not get_active_curriculum(curricula):
            raise ValidationError(
                "No active curricula in program from Discovery"
            )


class ProgramEnrollmentRequestSerializer(serializers.Serializer):
    """
    Serializer for request to create a program enrollment
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=PROGRAM_ENROLLMENT_STATUSES)


class ProgramEnrollmentModificationRequestSerializer(serializers.Serializer):
    """
    Serializer for request to modify a program enrollment
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=PROGRAM_ENROLLMENT_STATUSES)


class CourseEnrollmentRequestSerializer(serializers.Serializer):
    """
    Serializer for a request to create a course enrollment
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=COURSE_ENROLLMENT_STATUSES)


class CourseEnrollmentModificationRequestSerializer(serializers.Serializer):
    """
    Serializer for a request to modify a course enrollment
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=COURSE_ENROLLMENT_STATUSES)


class ProgramEnrollmentSerializer(serializers.Serializer):
    """
    Serializer for program enrollment API response.
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=PROGRAM_ENROLLMENT_STATUSES)
    account_exists = serializers.BooleanField()


class CourseEnrollmentSerializer(serializers.Serializer):
    """
    Serializer for program enrollment API response.
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=COURSE_ENROLLMENT_STATUSES)
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
    status = serializers.ChoiceField(choices=PROGRAM_ENROLLMENT_STATUSES)
    account_exists = serializers.BooleanField()


def serialize_course_enrollments_to_csv(enrollments):
    """
    Serialize course enrollments into a CSV-formatted string.

    Arguments:
        enrollments: list[dict]

    Returns: str
    """
    return serialize_to_csv(
        enrollments, ('student_key', 'status', 'account_exists')
    )
