""" Tests for core models. """

import ddt
from django.contrib.auth.models import Group
from django.test import TestCase
from django_dynamic_fixture import G
from guardian.shortcuts import get_perms
from social_django.models import UserSocialAuth

import registrar.apps.core.permissions as perm
from registrar.apps.core.models import (
    Organization,
    OrganizationGroup,
    PendingUserGroup,
    PendingUserOrganizationGroup,
    Program,
    ProgramOrganizationGroup,
    User,
)
from registrar.apps.core.tests.factories import (
    OrganizationFactory,
    OrganizationGroupFactory,
    ProgramFactory,
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
        perm.OrganizationReadMetadataRole,
        perm.OrganizationReadEnrollmentsRole,
        perm.OrganizationReadWriteEnrollmentsRole,
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
            role=perm.OrganizationReadMetadataRole.name,
            organization=self.organization,
        )
        self.user.groups.add(org_group)  # pylint: disable=no-member
        permission = perm.OrganizationReadMetadataRole.permissions[0]
        self.assertTrue(self.user.has_perm(permission, self.organization))
        self.assertFalse(self.user.has_perm(permission))

    def test_roles_are_org_specific(self):
        organization2 = OrganizationFactory()
        permission = perm.OrganizationReadMetadataRole.permissions[0]
        self.assertFalse(self.user.has_perm(permission, self.organization))
        self.assertFalse(self.user.has_perm(permission, organization2))
        org_group = OrganizationGroup.objects.create(
            role=perm.OrganizationReadMetadataRole.name,
            organization=self.organization,
        )
        self.user.groups.add(org_group)  # pylint: disable=no-member
        self.assertTrue(self.user.has_perm(permission, self.organization))
        self.assertFalse(self.user.has_perm(permission, organization2))

    def test_org_group_recalculates_permissions(self):
        org1 = self.organization
        org2 = OrganizationFactory()
        metdata_permission = perm.ORGANIZATION_READ_METADATA
        write_permission = perm.ORGANIZATION_WRITE_ENROLLMENTS

        # Scenario 1: read/write on org1
        org_group = OrganizationGroup.objects.create(
            role=perm.OrganizationReadWriteEnrollmentsRole.name,
            organization=org1,
        )
        self.user.groups.add(org_group)  # pylint: disable=no-member
        self.assertTrue(self.user.has_perm(metdata_permission, org1))
        self.assertTrue(self.user.has_perm(write_permission, org1))
        self.assertFalse(self.user.has_perm(metdata_permission, org2))
        self.assertFalse(self.user.has_perm(write_permission, org2))

        # Scenario 2: metadata only on org1
        org_group.role = perm.OrganizationReadEnrollmentsRole.name
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
        org_group.role = perm.OrganizationReadWriteEnrollmentsRole.name
        org_group.save()
        self.assertFalse(self.user.has_perm(metdata_permission, org1))
        self.assertFalse(self.user.has_perm(write_permission, org1))
        self.assertTrue(self.user.has_perm(metdata_permission, org2))
        self.assertTrue(self.user.has_perm(write_permission, org2))


@ddt.ddt
class ProgramOrganizationGroupTests(TestCase):
    """ Tests for ProgramOrganizationGroup model """

    def setUp(self):
        super(ProgramOrganizationGroupTests, self).setUp()
        self.program = ProgramFactory()
        self.user = UserFactory()

    @ddt.data(
        perm.ProgramReadMetadataRole,
        perm.ProgramReadEnrollmentsRole,
        perm.ProgramReadWriteEnrollmentsRole,
    )
    def test_roles(self, role):
        program_group = ProgramOrganizationGroup.objects.create(
            role=role.name,
            program=self.program,
            granting_organization=self.program.managing_organization,
        )
        permissions = get_perms(self.user, self.program)
        self.assertEqual([], permissions)
        self.user.groups.add(program_group)  # pylint: disable=no-member
        permissions = get_perms(self.user, self.program)
        self.assertEqual(len(role.permissions), len(permissions))
        for permission in Program._meta.permissions:
            self.assertEqual(
                permission in role.permissions,
                self.user.has_perm(permission, self.program)
            )

    def test_global_permission_not_granted(self):
        program_group = ProgramOrganizationGroup.objects.create(
            role=perm.ProgramReadMetadataRole.name,
            program=self.program,
            granting_organization=self.program.managing_organization,
        )
        self.user.groups.add(program_group)  # pylint: disable=no-member
        permission = perm.ProgramReadMetadataRole.permissions[0]
        self.assertTrue(self.user.has_perm(permission, self.program))
        self.assertFalse(self.user.has_perm(permission))

    def test_roles_are_program_specific(self):
        program2 = ProgramFactory()
        permission = perm.ProgramReadMetadataRole.permissions[0]
        self.assertFalse(self.user.has_perm(permission, self.program))
        self.assertFalse(self.user.has_perm(permission, program2))
        program_group = ProgramOrganizationGroup.objects.create(
            role=perm.ProgramReadMetadataRole.name,
            program=self.program,
            granting_organization=self.program.managing_organization,
        )
        self.user.groups.add(program_group)  # pylint: disable=no-member
        self.assertTrue(self.user.has_perm(permission, self.program))
        self.assertFalse(self.user.has_perm(permission, program2))

    def test_program_group_recalculates_permissions(self):
        program1 = self.program
        program2 = ProgramFactory()
        metdata_permission = perm.PROGRAM_READ_METADATA
        write_permission = perm.PROGRAM_WRITE_ENROLLMENTS

        # Scenario 1: read/write on program1
        program_group = ProgramOrganizationGroup.objects.create(
            role=perm.ProgramReadWriteEnrollmentsRole.name,
            program=program1,
            granting_organization=program1.managing_organization,
        )
        self.user.groups.add(program_group)  # pylint: disable=no-member
        self.assertTrue(self.user.has_perm(metdata_permission, program1))
        self.assertTrue(self.user.has_perm(write_permission, program1))
        self.assertFalse(self.user.has_perm(metdata_permission, program2))
        self.assertFalse(self.user.has_perm(write_permission, program2))

        # Scenario 2: metadata only on program1
        program_group.role = perm.ProgramReadEnrollmentsRole.name
        program_group.save()
        self.assertTrue(self.user.has_perm(metdata_permission, program1))
        self.assertFalse(self.user.has_perm(write_permission, program1))
        self.assertFalse(self.user.has_perm(metdata_permission, program2))
        self.assertFalse(self.user.has_perm(write_permission, program2))

        # Scenario 3: metadata only on program2
        program_group.program = program2
        program_group.save()
        self.assertFalse(self.user.has_perm(metdata_permission, program1))
        self.assertFalse(self.user.has_perm(write_permission, program1))
        self.assertTrue(self.user.has_perm(metdata_permission, program2))
        self.assertFalse(self.user.has_perm(write_permission, program2))

        # Scenario 4: read/write on program2
        program_group.role = perm.ProgramReadWriteEnrollmentsRole.name
        program_group.save()
        self.assertFalse(self.user.has_perm(metdata_permission, program1))
        self.assertFalse(self.user.has_perm(write_permission, program1))
        self.assertTrue(self.user.has_perm(metdata_permission, program2))
        self.assertTrue(self.user.has_perm(write_permission, program2))


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


class PendingUserGroupTests(TestCase):
    """ Tests for PendingUserGroup model """

    def setUp(self):
        super(PendingUserGroupTests, self).setUp()
        self.organization = OrganizationFactory()
        self.organization_group = OrganizationGroupFactory(organization=self.organization)
        self.program = ProgramFactory()
        self.program_group = ProgramOrganizationGroup.objects.create(
            program=self.program,
            granting_organization=self.program.managing_organization,
        )
        self.generic_group = Group.objects.create(name='generic_group')

    def test_pending_org_group_string(self):
        user_email = 'test_pending_org_group@example.com'
        pending_user_group = PendingUserGroup.objects.create(
            user_email=user_email,
            group=self.organization_group,
        )
        pending_user_group_string = str(pending_user_group)
        self.assertIn('PendingUserGroup', pending_user_group_string)
        self.assertIn(user_email, pending_user_group_string)
        self.assertIn(self.organization.name, pending_user_group_string)
        self.assertIn(self.organization_group.role, pending_user_group_string)

    def test_pending_program_group_string(self):
        user_email = 'test_pending_program_group@example.com'
        pending_user_group = PendingUserGroup.objects.create(
            user_email=user_email,
            group=self.program_group,
        )
        pending_user_group_string = str(pending_user_group)
        self.assertIn('PendingUserGroup', pending_user_group_string)
        self.assertIn(user_email, pending_user_group_string)
        self.assertIn(self.program.managing_organization.name, pending_user_group_string)
        self.assertIn(self.program.key, pending_user_group_string)
        self.assertIn(self.program_group.role, pending_user_group_string)

    def test_pending_generic_group_string(self):
        user_email = 'test_pending_generic_group@example.com'
        pending_user_group = PendingUserGroup.objects.create(
            user_email=user_email,
            group=self.generic_group,
        )
        pending_user_group_string = str(pending_user_group)
        self.assertIn('PendingUserGroup', pending_user_group_string)
        self.assertIn(user_email, pending_user_group_string)
        self.assertIn(self.generic_group.name, pending_user_group_string)
