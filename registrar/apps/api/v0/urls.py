""" API v0 URLs. """

from django.conf.urls import url

from registrar.apps.api.v0 import views
from registrar.apps.core.constants import (
    COURSE_ID_PATTERN,
    PROGRAM_KEY_PATTERN,
    JOB_ID_PATTERN,
)


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
    url(
        r'programs/{}/courses/{}/enrollments/$'.format(PROGRAM_KEY_PATTERN, COURSE_ID_PATTERN),
        views.MockCourseEnrollmentView.as_view(),
        name="program-enrollment",
    ),
    url(
        r'jobs/{}/$'.format(JOB_ID_PATTERN),
        views.MockJobStatusRetrieveView.as_view(),
        name="job-status",
    ),
]
