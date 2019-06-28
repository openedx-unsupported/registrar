""" URL patterns for the v2 REST API. """

from registrar.apps.api.v1.urls import urlpatterns as v1_urlpatterns


app_name = 'v2'

urlpatterns = [pattern for pattern in v1_urlpatterns]
