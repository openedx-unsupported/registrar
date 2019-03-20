""" API v0 URLs. """

from django.conf.urls import url

from registrar.apps.api.v0 import views
from registrar.apps.core.constants import PROGRAM_KEY_PATTERN


app_name = 'v0'

urlpatterns = [
    url(
        r'programs/$',
        views.MockProgramListView.as_view(),
        name="program-list",
    ),
    url(
        r'programs/{}/$'.format(PROGRAM_KEY_PATTERN),
        views.MockProgramRetrieveView.as_view(),
        name="program",
    ),
    url(
        r'programs/{}/courses/$'.format(PROGRAM_KEY_PATTERN),
        views.MockProgramCourseListView.as_view(),
        name="program-course-list",
    ),
    url(
        r'programs/{}/enrollments/$'.format(PROGRAM_KEY_PATTERN),
        views.MockProgramEnrollmentView.as_view(),
        name="program-enrollment",
    ),
]
