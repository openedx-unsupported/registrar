""" URL patterns for the v2 REST API. """

from ..v1.urls import urlpatterns as v1_urlpatterns


app_name = 'v2'

urlpatterns = v1_urlpatterns.copy()
