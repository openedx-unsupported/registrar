""" API v1 URLs. """

from django.conf.urls import url

from registrar.apps.core.constants import PROGRAM_KEY_PATTERN
from registrar.apps.api.v1 import views


app_name = 'v1'

urlpatterns = [
    url(
        r'programs/$',
        views.ProgramListView.as_view(),
        name="program-list",
    ),
    url(
        r'programs/{}/$'.format(PROGRAM_KEY_PATTERN),
        views.ProgramRetrieveView.as_view(),
        name="program",
    ),
    url(
        r'programs/{}/courses/$'.format(PROGRAM_KEY_PATTERN),
        views.ProgramCourseListView.as_view(),
        name="program-course-list",
    ),
]
