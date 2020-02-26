""" Tests for grade serializer error behavior """
from re import escape

import ddt
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from ..serializers import CourseGradeSerializer


@ddt.ddt
class CourseGradeSerializerTest(TestCase):
    """ Tests for additional custom validation on CourseGradeSerializer """
    msg = "Either ['error'] or ['letter_grade', 'percent', 'passed'] are required, but they are mutually exclusive"
    expected_error = escape(msg)

    def test_student_key_only(self):
        input_data = {'student_key': 'learner-01'}
        with self.assertRaisesRegex(ValidationError, self.expected_error):
            CourseGradeSerializer(data=input_data).is_valid(raise_exception=True)

    def test_all_fields(self):
        input_data = {
            'student_key': 'learner-01',
            'letter_grade': 'A',
            'percent': 1.0,
            'passed': True,
            'error': 'There was a problem I think',
        }
        with self.assertRaisesRegex(ValidationError, self.expected_error):
            CourseGradeSerializer(data=input_data).is_valid(raise_exception=True)

    @ddt.data(
        {'passed': True},
        {'letter_grade': 'A'},
        {
            'percent': 0.95,
            'letter_grade': 'B',
        },
    )
    def test_error_and_some_other_fields(self, input_data):
        input_data['student_key'] = 'learner-01'
        input_data['error'] = 'some problem idk'
        with self.assertRaisesRegex(ValidationError, self.expected_error):
            CourseGradeSerializer(data=input_data).is_valid(raise_exception=True)

    @ddt.data('letter_grade', 'percent', 'passed')
    def test_missing_grade_fields(self, dropped_key):
        input_data = {
            'student_key': 'learner-01',
            'letter_grade': 'A',
            'percent': 1.0,
            'passed': True,
        }
        input_data.pop(dropped_key)
        with self.assertRaisesRegex(ValidationError, self.expected_error):
            CourseGradeSerializer(data=input_data).is_valid(raise_exception=True)
