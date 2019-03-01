""" Admin configuration for enrollments models. """
from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from registrar.apps.enrollments import models


class OrganizationAdmin(GuardedModelAdmin):
    list_display = ('key', 'name', 'discovery_uuid')
    search_fields = ('key', 'name')
    ordering = ('key',)
    date_hierarchy = 'modified'


admin.site.register(models.Learner)
admin.site.register(models.LearnerProgramEnrollment)
admin.site.register(models.Organization, OrganizationAdmin)
admin.site.register(models.Program)
admin.site.register(models.OrgGroup)
admin.site.register(models.OrgGroupFutureMembership)
