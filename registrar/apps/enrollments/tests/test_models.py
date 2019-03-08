""" Tests for enrollment models """
import ddt
from guardian.shortcuts import get_perms
from django.test import TestCase
from registrar.apps.core.tests.factories import UserFactory
# Not sure why this is required, for some reason pylint can't find the file -JK
from registrar.apps.enrollments.tests.factories import OrganizationFactory  # pylint: disable=no-name-in-module
from registrar.apps.enrollments.models import (
    Organization, OrganizationGroup,
)
import registrar.apps.enrollments.permissions as perm


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
        self.user.groups.add(org_group)
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
        self.user.groups.add(org_group)
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
        self.user.groups.add(org_group)
        self.assertTrue(self.user.has_perm(permission, self.organization))
        self.assertFalse(self.user.has_perm(permission, organization2))
