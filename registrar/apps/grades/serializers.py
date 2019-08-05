""" Serializers for the grades app """
from rest_framework import serializers

from registrar.apps.core.utils import serialize_to_csv


# pylint: disable=abstract-method


class CourseGradeSerializer(serializers.Serializer):
    """
    Serializer for grades API response
    """

    student_key = serializers.CharField()
    letter_grade = serializers.CharField(allow_null=True)
    # max_value, min_value, decimal_places, max_digits
    percent = serializers.DecimalField(max_digits=4, decimal_places=3)
    passed = serializers.BooleanField()


def serialize_course_run_grades_to_csv(grades):
    """
    Serialize grades into a CSV-formatted string.

    Arguments:
        grades (list[dict]):
            List of grade responses

    Returns: str
    """
    return serialize_to_csv(
        grades,
        ('student_key', 'letter_grade', 'percent', 'passed'),
        include_headers=True,
    )
