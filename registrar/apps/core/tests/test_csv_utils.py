"""
Tests for csv_utils.py.
"""
import ddt
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from ..csv_utils import load_records_from_csv, serialize_to_csv


def _create_food(name, is_fruit, rating, color):
    return {
        'name': name,
        'is_fruit': is_fruit,
        'rating': rating,
        'color': color,
    }


@ddt.ddt
class SerializeToCSVTests(TestCase):
    """ Tests for serialize_to_csv """

    field_names = ('name', 'is_fruit', 'rating')
    test_data = [
        _create_food('asparagus', False, 3, 'green'),
        _create_food('avocado', True, 9, 'green'),
        _create_food('purplejollyrancher', True, 6, 'purple'),
    ]
    expected_headers = 'name,is_fruit,rating\r\n'
    expected_csv = (
        'asparagus,False,3\r\n'
        'avocado,True,9\r\n'
        'purplejollyrancher,True,6\r\n'
    )

    @ddt.data(True, False)
    def test_serialize_data(self, include_headers):

        # Assert that our test data includes at least one field that will NOT
        # be serialized, ensuring that `serialize_to_csv` can handle extra
        # fields gracefully.
        data_fields = set(self.test_data[0].keys())
        serialize_fields = set(self.field_names)
        self.assertTrue(serialize_fields.issubset(data_fields))
        self.assertFalse(data_fields.issubset(serialize_fields))

        result = serialize_to_csv(self.test_data, self.field_names, include_headers)
        if include_headers:
            self.assertEqual(self.expected_headers + self.expected_csv, result)
        else:
            self.assertEqual(self.expected_csv, result)


class LoadRecordsFromCSVStringTests(TestCase):
    """ Tests for load_records_from_csv """

    # We want to make sure that we test a CSV with several oddities:
    #  * Inconstent leading, trailing, and padding whitespace
    #  * Both types of line endings
    #  * Blank lines
    #  * Uppercase in field names
    csv_fmt = (
        "toPPing,is_vegetarian, rating  \n"
        "pepperoni,     false,   100\n"
        "               peppers,{pepper_is_vegetarian},100\r\n"
        "onions,true,100        \r\n"
        "\n"
        " pineapple ,true, 17\n"
        "\r\n"
    )
    csv = csv_fmt.format(pepper_is_vegetarian='true')
    csv_with_empty = csv_fmt.format(pepper_is_vegetarian='')  # Empty value

    def test_with_all_field_names(self):
        field_names = {'topping', 'is_vegetarian', 'rating'}
        actual = load_records_from_csv(self.csv, field_names)
        expected = [
            {'topping': 'pepperoni', 'is_vegetarian': 'false', 'rating': '100'},
            {'topping': 'peppers', 'is_vegetarian': 'true', 'rating': '100'},
            {'topping': 'onions', 'is_vegetarian': 'true', 'rating': '100'},
            {'topping': 'pineapple', 'is_vegetarian': 'true', 'rating': '17'},
        ]
        self.assertEqual(actual, expected)

    def test_with_field_names_subset(self):
        field_names = {'topping', 'is_vegetarian'}
        actual = load_records_from_csv(self.csv, field_names)
        expected = [
            {'topping': 'pepperoni', 'is_vegetarian': 'false'},
            {'topping': 'peppers', 'is_vegetarian': 'true'},
            {'topping': 'onions', 'is_vegetarian': 'true'},
            {'topping': 'pineapple', 'is_vegetarian': 'true'},
        ]
        self.assertEqual(actual, expected)

    def test_optional_field_name_null_value(self):
        field_names = {'topping', 'is_vegetarian', 'rating'}
        optional_field_names = {'is_vegetarian'}
        actual = load_records_from_csv(self.csv_with_empty, field_names, optional_field_names)
        expected = [
            {'topping': 'pepperoni', 'is_vegetarian': 'false', 'rating': '100'},
            {'topping': 'peppers', 'is_vegetarian': '', 'rating': '100'},
            {'topping': 'onions', 'is_vegetarian': 'true', 'rating': '100'},
            {'topping': 'pineapple', 'is_vegetarian': 'true', 'rating': '17'},
        ]
        self.assertEqual(actual, expected)

    def test_optional_field_name_header(self):
        field_names = {'topping', 'is_vegetarian', 'rating', 'cost'}
        optional_field_names = {'cost'}
        actual = load_records_from_csv(self.csv, field_names, optional_field_names)
        expected = [
            {'topping': 'pepperoni', 'is_vegetarian': 'false', 'rating': '100'},
            {'topping': 'peppers', 'is_vegetarian': 'true', 'rating': '100'},
            {'topping': 'onions', 'is_vegetarian': 'true', 'rating': '100'},
            {'topping': 'pineapple', 'is_vegetarian': 'true', 'rating': '17'},
        ]
        self.assertEqual(actual, expected)

    def test_missing_field_names_error(self):
        field_names = {'topping', 'is_vegetarian', 'color'}
        with self.assertRaises(ValidationError):
            load_records_from_csv(self.csv, field_names)

    def test_null_values_error(self):
        field_names = {'topping', 'is_vegetarian', 'color'}
        with self.assertRaises(ValidationError):
            load_records_from_csv(self.csv_with_empty, field_names)
