"""
Root API URLs.

All API URLs should be versioned, so urlpatterns should only
contain namespaces for the active versions of the API.
"""
from django.urls import include, path

from .internal import urls as internal_urls
from .v1 import urls as v1_urls
from .v2 import urls as v2_urls
from .v3 import urls as v3_urls


app_name = 'api'
urlpatterns = [
    path('internal/', include(internal_urls)),
    path('v1/', include(v1_urls)),
    path('v2/', include(v2_urls)),
    path('v3/', include(v3_urls)),
]
