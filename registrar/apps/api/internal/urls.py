""" API internal URLs. """

from django.urls import re_path

from registrar.apps.core.constants import PROGRAM_KEY_PATTERN

from . import views


app_name = 'internal'

urlpatterns = [
    re_path(
        r'^cache/?$',
        views.FlushProgramCacheView.as_view(),
        name="flush-program-cache-all",
    ),
    re_path(
        fr'^cache/{PROGRAM_KEY_PATTERN}/?$',
        views.FlushProgramCacheView.as_view(),
        name="flush-program-cache-one",
    ),
]
