""" Serializers for the grades app """
from rest_framework import serializers

from registrar.apps.core.csv_utils import serialize_to_csv


# pylint: disable=abstract-method


class CourseGradeSerializer(serializers.Serializer):
    """
    Serializer for grades API response
    """

    student_key = serializers.CharField()

    letter_grade = serializers.CharField(required=False, allow_null=True)
    percent = serializers.DecimalField(required=False, max_digits=4, decimal_places=3)
    passed = serializers.BooleanField(required=False)

    error = serializers.CharField(required=False)

    # pylint: disable=arguments-renamed
    def validate(self, data):
        """
        Either ['error'] or ['letter_grade', 'percent', 'passed'] are required, but they are mutually exclusive
        """
        msg = "Either ['error'] or ['letter_grade', 'percent', 'passed'] are required, but they are mutually exclusive"
        error = 'error' in data
        grade_fields_in_data = [target_field in data for target_field in ('letter_grade', 'percent', 'passed')]
        any_grade_fields = any(grade_fields_in_data)

        if not any_grade_fields and not error:
            raise serializers.ValidationError(msg)
        if 'error' in data and any_grade_fields:
            raise serializers.ValidationError(msg)
        if any_grade_fields and not all(grade_fields_in_data):
            raise serializers.ValidationError(msg)

        return data


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
        ('student_key', 'letter_grade', 'percent', 'passed', 'error'),
        include_headers=True,
    )
