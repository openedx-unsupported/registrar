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

from . import api_renderer
from .apps.api import urls as api_urls
from .apps.core import views as core_views


admin.site.site_header = 'Registrar Service Administration'
admin.site.site_title = admin.site.site_header
admin.autodiscover()

app_name = 'registrar'

urlpatterns = oauth2_urlpatterns + [
    # '/' and '/login' redirect to '/login/',
    # which attempts LMS OAuth and then redirects to api-docs.
    url(r'^/?$', RedirectView.as_view(url=settings.LOGIN_URL)),
    url(r'^login$', RedirectView.as_view(url=settings.LOGIN_URL)),

    # Use the same auth views for all logins,
    # including those originating from the browseable API.
    url(r'^api-auth/', include(oauth2_urlpatterns)),

    # Swagger documentation UI.
    url(r'^api-docs$', RedirectView.as_view(pattern_name='api-docs')),
    url(r'^api-docs/$', api_renderer.render_yaml_spec, name='api-docs'),

    # Django admin panel.
    url(r'^admin$', RedirectView.as_view(pattern_name='admin:index')),
    url(r'^admin/', admin.site.urls),

    # Health view.
    url(r'^health/?$', core_views.health, name='health'),

    # Auto-auth for testing. View raises 404 if not `settings.ENABLE_AUTO_AUTH`
    url(r'^auto_auth/?$', core_views.AutoAuth.as_view(), name='auto_auth'),

    # The API itself!
    url(r'^api/', include(api_urls)),
]

# edx-drf-extensions csrf app
urlpatterns += [
    url(r'', include('csrf.urls')),
]

if settings.DEBUG and os.environ.get('ENABLE_DJANGO_TOOLBAR', False):  # pragma: no cover
    import debug_toolbar  # pylint: disable=import-error

    urlpatterns.append(url(r'^__debug__/', include(debug_toolbar.urls)))

if settings.DEBUG:  # pragma: no cover
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
