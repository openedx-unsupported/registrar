""" API v3 URLs. """

from django.urls import re_path

from . import views


app_name = 'v3'

urlpatterns = [
    re_path(
        r'^programs/?$',
        views.ProgramListPaginationView.as_view(),
        name="program-list",
    ),
]
