""" API v1 URLs. """

from django.urls import re_path

from registrar.apps.core.constants import (
    COURSE_ID_PATTERN,
    JOB_ID_PATTERN,
    PROGRAM_KEY_PATTERN,
)

from . import views


app_name = 'v1'

urlpatterns = [
    re_path(
        r'^programs/?$',
        views.ProgramListView.as_view(),
        name="program-list",
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/?$',
        views.ProgramRetrieveView.as_view(),
        name="program",
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/enrollments/?$',
        views.ProgramEnrollmentView.as_view(),
        name="program-enrollments",
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/courses/?$',
        views.ProgramCourseListView.as_view(),
        name="program-course-list",
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/enrollments/?$',
        views.ProgramEnrollmentView.as_view(),
        name="program-enrollment",
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/courses/{COURSE_ID_PATTERN}/grades/?$',
        views.CourseGradesView.as_view(),
        name="program-course-grades",
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/courses/{COURSE_ID_PATTERN}/enrollments/?$',
        views.CourseEnrollmentView.as_view(),
        name="program-course-enrollment",
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/enrollments/upload/?$',
        views.ProgramEnrollmentUploadView.as_view(),
        name="program-enrollment-upload"
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/course_enrollments/upload/?$',
        views.CourseRunEnrollmentUploadView.as_view(),
        name="program-course-enrollment-upload"
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/course_enrollments/?$',
        views.CourseRunEnrollmentDownloadView.as_view(),
        name="program-course-enrollment-download"
    ),
    re_path(
        fr'^programs/{PROGRAM_KEY_PATTERN}/reports',
        views.ReportsListView.as_view(),
    ),
    re_path(
        r'^jobs/?$',
        views.JobStatusListView.as_view(),
        name="job-status-list",
    ),
    re_path(
        fr'^jobs/{JOB_ID_PATTERN}/?$',
        views.JobStatusRetrieveView.as_view(),
        name="job-status",
    ),
]
