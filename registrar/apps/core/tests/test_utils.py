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


def _create_enrollment(student_key, status, account_created):
    return {
        'student_key': student_key,
        'status': status,
        'account_created': account_created,
    }


@ddt.ddt
class SerializeToCSVTests(TestCase):
    """ Tests for serialize_to_csv """

    field_names = ('student_key', 'status', 'account_created')
    test_data = [
        _create_enrollment('student_1111', 'active', True),
        _create_enrollment('student_2222', 'inactive', True),
        _create_enrollment('student_3333', 'active', False),
        _create_enrollment('student_4444', 'inactive', False),
    ]
    expected_headers = 'student_key,status,account_created\r\n'
    expected_csv = (
        'student_1111,active,True\r\n'
        'student_2222,inactive,True\r\n'
        'student_3333,active,False\r\n'
        'student_4444,inactive,False\r\n'
    )

    @ddt.data(True, False)
    def test_serialize_data(self, include_headers):
        result = serialize_to_csv(self.test_data, self.field_names, include_headers)
        if include_headers:
            self.assertEqual(self.expected_headers + self.expected_csv, result)
        else:
            self.assertEqual(self.expected_csv, result)
