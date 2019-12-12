"""
Tests for signal handlers in this app
"""
import ddt
from django.apps import apps
from django.test import TestCase

from registrar.apps.core import permissions as perms
from registrar.apps.core.models import PendingUserOrganizationGroup, User
from registrar.apps.core.tests.factories import (
    OrganizationGroupFactory,
    PendingUserOrganizationGroupFactory,
)


@ddt.ddt
class HandleUserPostSaveTests(TestCase):
    """
    Tests for the handle_user_post_save
    """
    def setUp(self):
        super(HandleUserPostSaveTests, self).setUp()
        self.organization_group = OrganizationGroupFactory()
        self.user_email = 'test@edx.org'
        self.user_password = 'password'
        self.pending_user_org_group = PendingUserOrganizationGroupFactory(
            organization_group=self.organization_group,
            user_email=self.user_email
        )
        apps.get_app_config('core').ready()

    def test_single_pending_org_group(self):
        user = User.objects.create(
            username=self.user_email,
            email=self.user_email,
            password=self.user_password
        )
        self._assert_group_membership(user, self.organization_group.name)
        self._assert_deletion()

    @ddt.data(
        perms.ReadEnrollmentsRole.name,
        perms.ReadMetadataRole.name,
        perms.ReadWriteEnrollmentsRole.name,
    )
    def test_multiple_pending_org_group(self, role_name):
        another_group = OrganizationGroupFactory(
            role=role_name
        )
        PendingUserOrganizationGroupFactory(
            user_email=self.user_email,
            organization_group=another_group,
        )
        user = User.objects.create(
            username=self.user_email,
            email=self.user_email,
            password=self.user_password
        )
        self._assert_group_membership(user, self.organization_group.name)
        self._assert_group_membership(user, another_group.name)
        self._assert_deletion()

    def test_already_member_of_group(self):
        user = User.objects.create(
            username=self.user_email,
            email=self.user_email,
            password=self.user_password
        )
        self._assert_group_membership(user, self.organization_group.name)
        self._assert_deletion()
        PendingUserOrganizationGroupFactory(
            user_email=self.user_email,
            organization_group=self.organization_group,
        )
        user.full_name = 'test name'
        user.save()
        self.assertEqual(len(user.groups.all()), 1)
        self._assert_deletion()

    def test_no_pending_user_organization_group(self):
        self.pending_user_org_group.delete()
        user = User.objects.create(
            username=self.user_email,
            email=self.user_email,
            password=self.user_password
        )
        self.assertEqual(len(user.groups.all()), 0)

    def _assert_deletion(self):
        with self.assertRaises(PendingUserOrganizationGroup.DoesNotExist):
            PendingUserOrganizationGroup.objects.get(
                user_email=self.user_email
            )

    def _assert_group_membership(self, user, group_name):
        self.assertTrue(user.groups.filter(name=group_name).exists())
