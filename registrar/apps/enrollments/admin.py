""" Admin configuration for enrollments models. """
from django.contrib import admin

from registrar.apps.enrollments import models


admin.site.register(models.Program)
