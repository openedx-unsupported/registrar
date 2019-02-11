""" API v1 URLs. """
# pylint: disable=unused-import
from django.conf.urls import url
from rest_framework import routers

from .views import ProgramEnrollmentView


app_name = 'v1'
urlpatterns = []
