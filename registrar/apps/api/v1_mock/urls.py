""" API v1_mock URLs. """

from django.conf.urls import url

from registrar.apps.api.v1_mock import views
from registrar.apps.core.constants import PROGRAM_KEY_PATTERN, COURSE_ID_PATTERN


app_name = 'v1-mock'

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
    url(
        r'programs/{}/courses/{}/enrollments/$'.format(PROGRAM_KEY_PATTERN, COURSE_ID_PATTERN),
        views.MockCourseEnrollmentView.as_view(),
        name="program-enrollment",
    ),
    url(
        r'jobs/(?P<job_id>[0-9a-f-]+)$',
        views.MockJobStatusRetrieveView.as_view(),
        name="job-status",
    ),
]
