""" API v1 URLs. """

from django.conf.urls import url

from registrar.apps.api.v1 import views
from registrar.apps.core.constants import (
    COURSE_ID_PATTERN,
    JOB_ID_PATTERN,
    PROGRAM_KEY_PATTERN,
)


app_name = 'v1'

urlpatterns = [
    url(
        r'^programs/?$',
        views.ProgramListView.as_view(),
        name="program-list",
    ),
    url(
        r'^programs/{}/?$'.format(PROGRAM_KEY_PATTERN),
        views.ProgramRetrieveView.as_view(),
        name="program",
    ),
    url(
        r'^programs/{}/enrollments/?$'.format(PROGRAM_KEY_PATTERN),
        views.ProgramEnrollmentView.as_view(),
        name="program-enrollments",
    ),
    url(
        r'^programs/{}/courses/?$'.format(PROGRAM_KEY_PATTERN),
        views.ProgramCourseListView.as_view(),
        name="program-course-list",
    ),
    url(
        r'^programs/{}/enrollments/?$'.format(PROGRAM_KEY_PATTERN),
        views.ProgramEnrollmentView.as_view(),
        name="program-enrollment",
    ),
    url(
        r'^programs/{}/courses/{}/grades/?$'.format(PROGRAM_KEY_PATTERN, COURSE_ID_PATTERN),
        views.CourseGradesView.as_view(),
        name="program-course-grades",
    ),
    url(
        r'^programs/{}/courses/{}/enrollments/?$'.format(PROGRAM_KEY_PATTERN, COURSE_ID_PATTERN),
        views.CourseEnrollmentView.as_view(),
        name="program-course-enrollment",
    ),
    url(
        r'^programs/{}/enrollments/upload/?$'.format(PROGRAM_KEY_PATTERN),
        views.ProgramEnrollmentUploadView.as_view(),
        name="program-enrollment-upload"
    ),
    url(
        r'^programs/{}/course_enrollments/upload/?$'.format(PROGRAM_KEY_PATTERN),
        views.CourseRunEnrollmentUploadView.as_view(),
        name="program-course-enrollment-upload"
    ),
    url(
        r'^programs/{}/course_enrollments/?$'.format(PROGRAM_KEY_PATTERN),
        views.CourseRunEnrollmentDownloadView.as_view(),
        name="program-course-enrollment-download"
    ),
    url(
        r'^jobs/?$',
        views.JobStatusListView.as_view(),
        name="job-status-list",
    ),
    url(
        r'^jobs/{}/?$'.format(JOB_ID_PATTERN),
        views.JobStatusRetrieveView.as_view(),
        name="job-status",
    ),
]
