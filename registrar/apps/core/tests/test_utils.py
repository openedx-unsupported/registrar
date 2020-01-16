""" Tests for Core utils.py """
import ddt
from django.contrib.auth.models import Group
from django.test import TestCase
from guardian.shortcuts import assign_perm
from rest_framework.exceptions import ValidationError

from registrar.apps.core.permissions import (
    ORGANIZATION_READ_METADATA,
    ORGANIZATION_READ_REPORTS,
    APIReadEnrollmentsPermission,
    APIReadMetadataPermission,
    APIReadReportsPermission,
    APIWriteEnrollmentsPermission,
    OrganizationReadWriteEnrollmentsRole,
)
from registrar.apps.core.tests.factories import (
    GroupFactory,
    OrganizationFactory,
    OrganizationGroupFactory,
    UserFactory,
)
from registrar.apps.core.utils import (
    get_user_api_permissions,
    get_user_organizations,
    load_records_from_csv,
    serialize_to_csv,
)


@ddt.ddt
class GetUserOrganizationsTests(TestCase):
    """ Tests for get_user_organizations """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        org1 = OrganizationFactory(key='org1')
        OrganizationGroupFactory(
            organization=org1, name='org1a'
        )
        OrganizationGroupFactory(
            organization=org1, name='org1b'
        )
        org2 = OrganizationFactory(key='org2')
        OrganizationGroupFactory(
            organization=org2, name='org2a'
        )
        OrganizationGroupFactory(
            organization=org2, name='org2b'
        )
        OrganizationFactory(key='org3')
        GroupFactory(name='normal_group')

    @ddt.data(
        ({'org1a', 'org1b', 'org2a'}, {'org1', 'org2'}),
        ({'org2a', 'org2b', 'normal_group'}, {'org2'}),
        ({'normal_group'}, set()),
        (set(), set()),
    )
    @ddt.unpack
    def test_get_user_organizations(self, group_names, expected_org_keys):
        groups = [Group.objects.get(name=name) for name in group_names]
        user = UserFactory(groups=groups)
        orgs = get_user_organizations(user)
        org_keys = {org.key for org in orgs}
        self.assertEqual(org_keys, expected_org_keys)


class GetUserAPIPermissionsTests(TestCase):
    """ Tests for get_user_api_permissions """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.org1 = OrganizationFactory()
        org1_readwrite = OrganizationGroupFactory(
            organization=cls.org1,
            role=OrganizationReadWriteEnrollmentsRole.name
        )

        cls.org2 = OrganizationFactory()
        cls.org3 = OrganizationFactory()

        cls.user = UserFactory(groups=[org1_readwrite])
        assign_perm(ORGANIZATION_READ_METADATA, cls.user)
        assign_perm(ORGANIZATION_READ_REPORTS, cls.user, cls.org3)

    def test_get_api_permissions(self):
        # validate permissions assigned by a group
        perms = get_user_api_permissions(self.user, self.org1)
        self.assertSetEqual(perms, set([
            APIReadMetadataPermission,
            APIReadEnrollmentsPermission,
            APIWriteEnrollmentsPermission,
        ]))

        # validate permissions assigned globally
        perms = get_user_api_permissions(self.user, self.org2)
        self.assertSetEqual(perms, set([APIReadMetadataPermission]))

        # validate permissions assigned directly on the object
        perms = get_user_api_permissions(self.user, self.org3)
        self.assertSetEqual(perms, set([APIReadReportsPermission, APIReadMetadataPermission]))

        # request only permissions assigned globally
        perms = get_user_api_permissions(self.user)
        self.assertSetEqual(perms, set([APIReadMetadataPermission]))


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
    bad_csv = csv_fmt.format(pepper_is_vegetarian='')  # Empty value

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

    def test_missing_field_names_error(self):
        field_names = {'topping', 'is_vegetarian', 'color'}
        with self.assertRaises(ValidationError):
            load_records_from_csv(self.csv, field_names)

    def test_null_values_error(self):
        field_names = {'topping', 'is_vegetarian', 'color'}
        with self.assertRaises(ValidationError):
            load_records_from_csv(self.bad_csv, field_names)
