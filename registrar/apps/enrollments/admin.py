""" Admin configuration for enrollments models. """
from django.contrib import admin

from registrar.apps.enrollments import models


class ProgramAdmin(admin.ModelAdmin):
    """
    Admin tool for the ProgramEnrollment model
    """
    list_display = ("key", "discovery_uuid", "managing_organization")


admin.site.register(models.Program, ProgramAdmin)
