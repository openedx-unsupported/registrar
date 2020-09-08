""" API v3 URLs. """

from django.conf.urls import url

from . import views


app_name = 'v3'

urlpatterns = [
    url(
        r'^programs/?$',
        views.ProgramListPaginationView.as_view(),
        name="program-list",
    ),
]
