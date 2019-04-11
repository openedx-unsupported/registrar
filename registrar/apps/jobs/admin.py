""" Admin configuration for jobs models. """

from django.contrib import admin

from registrar.apps.jobs.models import Job


admin.register(Job)
