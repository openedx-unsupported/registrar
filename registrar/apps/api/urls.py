"""
Root API URLs.

All API URLs should be versioned, so urlpatterns should only
contain namespaces for the active versions of the API.
"""
from django.conf.urls import url, include

from registrar.apps.api.internal import urls as internal_urls
from registrar.apps.api.v1_mock import urls as v1_mock_urls
from registrar.apps.api.v1 import urls as v1_urls

app_name = 'api'
urlpatterns = [
    url(r'^internal/', include(internal_urls)),
    url(r'^v1-mock/', include(v1_mock_urls)),
    url(r'^v1/', include(v1_urls)),
]
