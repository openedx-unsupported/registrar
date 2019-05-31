""" Tests for Core utils.py """
import ddt
from django.contrib.auth.models import Group
from django.test import TestCase

from registrar.apps.core.tests.factories import (
    GroupFactory,
    OrganizationFactory,
    OrganizationGroupFactory,
    UserFactory,
)
from registrar.apps.core.utils import get_user_organizations, serialize_to_csv


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
