""" Tests for core models. """

import ddt
from django.test import TestCase
from django_dynamic_fixture import G
from guardian.shortcuts import get_perms
from social_django.models import UserSocialAuth

import registrar.apps.core.permissions as perm
from registrar.apps.core.models import (
    Organization,
    OrganizationGroup,
    PendingUserOrganizationGroup,
    User,
)
from registrar.apps.core.tests.factories import (
    OrganizationFactory,
    OrganizationGroupFactory,
    UserFactory,
)


class UserTests(TestCase):
    """ User model tests. """
    TEST_CONTEXT = {'foo': 'bar', 'baz': None}

    def test_access_token(self):
        user = G(User)
        self.assertIsNone(user.access_token)

        social_auth = G(UserSocialAuth, user=user)
        self.assertIsNone(user.access_token)

        access_token = 'My voice is my passport. Verify me.'
        social_auth.extra_data['access_token'] = access_token
        social_auth.save()
        self.assertEqual(user.access_token, access_token)

    def test_get_full_name(self):
        """ Test that the user model concatenates first and last name if the full name is not set. """
        full_name = 'George Costanza'
        user = G(User, full_name=full_name)
        self.assertEqual(user.get_full_name(), full_name)

        first_name = 'Jerry'
        last_name = 'Seinfeld'
        user = G(User, full_name=None, first_name=first_name, last_name=last_name)
        expected = '{first_name} {last_name}'.format(first_name=first_name, last_name=last_name)
        self.assertEqual(user.get_full_name(), expected)

        user = G(User, full_name=full_name, first_name=first_name, last_name=last_name)
        self.assertEqual(user.get_full_name(), full_name)

    def test_string(self):
        """Verify that the model's string method returns the user's username """
        username = 'bob'
        user = G(User, username=username)
        self.assertEqual(str(user), username)


@ddt.ddt
class OrganizationGroupTests(TestCase):
    """ Tests for OrganizationGroup model """

    def setUp(self):
        super(OrganizationGroupTests, self).setUp()
        self.organization = OrganizationFactory()
        self.user = UserFactory()

    @ddt.data(
        perm.ReadMetadataRole,
        perm.ReadEnrollmentsRole,
        perm.ReadWriteEnrollmentsRole,
    )
    def test_roles(self, role):
        org_group = OrganizationGroup.objects.create(
            role=role.name,
            organization=self.organization,
        )
        permissions = get_perms(self.user, self.organization)
        self.assertEqual([], permissions)
        self.user.groups.add(org_group)  # pylint: disable=no-member
        permissions = get_perms(self.user, self.organization)
        self.assertEqual(len(role.permissions), len(permissions))
        for permission in Organization._meta.permissions:
            self.assertEqual(
                permission in role.permissions,
                self.user.has_perm(permission, self.organization)
            )

    def test_global_permission_not_granted(self):
        org_group = OrganizationGroup.objects.create(
            role=perm.ReadMetadataRole.name,
            organization=self.organization,
        )
        self.user.groups.add(org_group)  # pylint: disable=no-member
        permission = perm.ReadMetadataRole.permissions[0]
        self.assertTrue(self.user.has_perm(permission, self.organization))
        self.assertFalse(self.user.has_perm(permission))

    def test_roles_are_org_specific(self):
        organization2 = OrganizationFactory()
        permission = perm.ReadMetadataRole.permissions[0]
        self.assertFalse(self.user.has_perm(permission, self.organization))
        self.assertFalse(self.user.has_perm(permission, organization2))
        org_group = OrganizationGroup.objects.create(
            role=perm.ReadMetadataRole.name,
            organization=self.organization,
        )
        self.user.groups.add(org_group)  # pylint: disable=no-member
        self.assertTrue(self.user.has_perm(permission, self.organization))
        self.assertFalse(self.user.has_perm(permission, organization2))

    def test_org_group_recalculates_permissions(self):
        org1 = self.organization
        org2 = OrganizationFactory()
        metdata_permission = perm.READ_METADATA
        write_permission = perm.WRITE_ENROLLMENTS

        # Scenario 1: read/write on org1
        org_group = OrganizationGroup.objects.create(
            role=perm.ReadWriteEnrollmentsRole.name,
            organization=org1,
        )
        self.user.groups.add(org_group)  # pylint: disable=no-member
        self.assertTrue(self.user.has_perm(metdata_permission, org1))
        self.assertTrue(self.user.has_perm(write_permission, org1))
        self.assertFalse(self.user.has_perm(metdata_permission, org2))
        self.assertFalse(self.user.has_perm(write_permission, org2))

        # Scenario 2: metadata only on org1
        org_group.role = perm.ReadEnrollmentsRole.name
        org_group.save()
        self.assertTrue(self.user.has_perm(metdata_permission, org1))
        self.assertFalse(self.user.has_perm(write_permission, org1))
        self.assertFalse(self.user.has_perm(metdata_permission, org2))
        self.assertFalse(self.user.has_perm(write_permission, org2))

        # Scenario 3: metadata only on org2
        org_group.organization = org2
        org_group.save()
        self.assertFalse(self.user.has_perm(metdata_permission, org1))
        self.assertFalse(self.user.has_perm(write_permission, org1))
        self.assertTrue(self.user.has_perm(metdata_permission, org2))
        self.assertFalse(self.user.has_perm(write_permission, org2))

        # Scenario 4: read/write on org2
        org_group.role = perm.ReadWriteEnrollmentsRole.name
        org_group.save()
        self.assertFalse(self.user.has_perm(metdata_permission, org1))
        self.assertFalse(self.user.has_perm(write_permission, org1))
        self.assertTrue(self.user.has_perm(metdata_permission, org2))
        self.assertTrue(self.user.has_perm(write_permission, org2))


class PendingUserOrganizationGroupTests(TestCase):
    """ Tests for PendingUserOrganizationGroup model """

    def setUp(self):
        super(PendingUserOrganizationGroupTests, self).setUp()
        self.organization = OrganizationFactory()
        self.organization_group = OrganizationGroupFactory(organization=self.organization)

    def test_string(self):
        user_email = 'test@example.com'
        pending_user_org_group = PendingUserOrganizationGroup.objects.create(
            user_email=user_email,
            organization_group=self.organization_group,
        )
        pending_user_org_group_string = str(pending_user_org_group)
        self.assertIn('PendingUserOrganizationGroup', pending_user_org_group_string)
        self.assertIn(user_email, pending_user_org_group_string)
        self.assertIn(self.organization.name, pending_user_org_group_string)
        self.assertIn(self.organization_group.role, pending_user_org_group_string)
