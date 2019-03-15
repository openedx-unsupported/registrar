""" Admin configuration for core models. """

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _

from guardian.admin import GuardedModelAdmin
from registrar.apps.core.models import (
    Organization,
    OrganizationGroup,
    PendingUserOrganizationGroup,
    User,
)


class CustomUserAdmin(UserAdmin):
    """ Admin configuration for the custom User model. """
    list_display = ('username', 'email', 'full_name', 'first_name', 'last_name', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )


class OrganizationAdmin(GuardedModelAdmin):
    list_display = ('key', 'name', 'discovery_uuid')
    search_fields = ('key', 'name')
    ordering = ('key',)
    date_hierarchy = 'modified'


class OrganizationGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'role')
    exclude = ('permissions',)


class PendingUserOrganizationGroupAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'organization_group')
    search_fields = ('user_email', )


admin.site.register(User, CustomUserAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(OrganizationGroup, OrganizationGroupAdmin)
admin.site.register(PendingUserOrganizationGroup, PendingUserOrganizationGroupAdmin)
