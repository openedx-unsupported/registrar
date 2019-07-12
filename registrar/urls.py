"""registrar URL Configuration
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""

import os

from auth_backends.urls import oauth2_urlpatterns
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic.base import RedirectView

from registrar import api_renderer
from registrar.apps.api import urls as api_urls
from registrar.apps.core import views as core_views


admin.site.site_header = 'Registrar Service Administration'
admin.site.site_title = admin.site.site_header
admin.autodiscover()

app_name = 'registrar'

urlpatterns = oauth2_urlpatterns + [
    url(r'^admin/', admin.site.urls),
    url(r'^admin$', RedirectView.as_view(pattern_name='admin:index')),
    url(r'^api/', include(api_urls)),
    url(r'^api-docs/', api_renderer.render_yaml_spec, name='api-docs'),
    url(r'^api-docs', RedirectView.as_view(pattern_name='api-docs')),
    # Use the same auth views for all logins, including those originating from the browseable API.
    url(r'^api-auth/', include(oauth2_urlpatterns)),
    url(r'^auto_auth/?$', core_views.AutoAuth.as_view(), name='auto_auth'),
    url(r'^health/?$', core_views.health, name='health'),
]

# edx-drf-extensions csrf app
urlpatterns += [
    url(r'', include('csrf.urls')),
]

if settings.DEBUG and os.environ.get('ENABLE_DJANGO_TOOLBAR', False):  # pragma: no cover
    import debug_toolbar
    urlpatterns.append(url(r'^__debug__/', include(debug_toolbar.urls)))

if settings.DEBUG:  # pragma: no cover
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
