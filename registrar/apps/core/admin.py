""" Admin configuration for core models. """

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from guardian.admin import GuardedModelAdmin

from .models import (
    Organization,
    OrganizationGroup,
    PendingUserGroup,
    Program,
    ProgramOrganizationGroup,
    User,
    UserGroup,
)


class CustomUserAdmin(UserAdmin):
    """ Admin configuration for the custom User model. """
    list_display = ('id', 'username', 'email', 'full_name', 'first_name', 'last_name', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )


class UserGroupAdmin(UserAdmin):
    """
    Admin configuration for the UserGroup model. UserGroup is just a proxy to
    User. This admin class only allows for editing a user's group assignements.
    """
    readonly_fields = ('username',)
    fieldsets = (
        (None, {'fields': ('username',)}),
        (_('Permissions'), {'fields': ('groups',)}),
    )


class OrganizationAdmin(GuardedModelAdmin):
    list_display = ('key', 'name', 'discovery_uuid')
    search_fields = ('key', 'name', 'discovery_uuid')
    ordering = ('key',)
    date_hierarchy = 'modified'


class GroupAdmin(admin.ModelAdmin):
    """
    Custom admin class for OrganizationGroupAdmin and ProgramGroupAdmin
    """
    def group_users(self, obj):
        """Return comma separated list of users in group"""
        return ", ".join([user.username for user in User.objects.filter(groups__name=obj.name)])


class OrganizationGroupAdmin(GroupAdmin):
    """
    Admin tool for the OrganizationGroup model
    """
    list_display = ('name', 'organization', 'role', 'group_users')
    fields = ('name', 'organization', 'role', 'group_users')
    readonly_fields = ('group_users',)
    search_fields = ('name', 'organization__key', 'organization__name', 'role')
    ordering = ('name',)
    exclude = ('permissions',)


class PendingUserGroupAdmin(admin.ModelAdmin):
    list_display = ("group", "user_email")
    search_fields = ("group__name", "user_email")
    ordering = ("group", "user_email")


class ProgramAdmin(admin.ModelAdmin):
    """
    Admin tool for the ProgramEnrollment model
    """
    list_display = ("managing_organization", "key", "discovery_uuid")
    search_fields = ("managing_organization__name", "key", "discovery_uuid")
    ordering = ("managing_organization", "key")


class ProgramGroupAdmin(GroupAdmin):
    """
    Admin tool for the ProgramOrganizationGroup model
    """
    list_display = ('name', 'program', 'granting_organization', 'role', 'group_users')
    fields = ('name', 'program', 'granting_organization', 'role', 'group_users')
    readonly_fields = ('group_users',)
    search_fields = ('name', 'program__key', 'granting_organization__name', 'role')
    ordering = ('name',)
    exclude = ('permissions', )


admin.site.register(User, CustomUserAdmin)
admin.site.register(UserGroup, UserGroupAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(OrganizationGroup, OrganizationGroupAdmin)
admin.site.register(PendingUserGroup, PendingUserGroupAdmin)
admin.site.register(Program, ProgramAdmin)
admin.site.register(ProgramOrganizationGroup, ProgramGroupAdmin)
