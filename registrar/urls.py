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
from edx_api_doc_tools import make_api_info, make_docs_ui_view

from . import api_renderer
from .apps.api import urls as api_urls
from .apps.core import views as core_views


admin.site.site_header = 'Registrar Service Administration'
admin.site.site_title = admin.site.site_header
admin.autodiscover()

app_name = 'registrar'

new_api_ui_view = make_docs_ui_view(
    make_api_info(
        title="Registrar API - Online Documentation",
        version="v2",
        email="masters-dev@edx.org",
        description=(
            "<b>Administer student enrollments in degree-bearing edX programs. </b>"
            "<br/><br/>"
            "<b>A Note on Student Keys</b>"
            "<br/><br/>"
            "The Program and Course Enrollment creation/modification endpoints "
            "all require partners to provide student_keys in order to identify "
            "students being enrolled. For data privacy reasons, the student_key "
            "attribute cannot be, or include, sensitive personal information "
            "like a student’s official university ID number, social security number, "
            "or some other government-issued ID number. It is the responsibility "
            "of the partner to determine a system for associating their students "
            "enrolled in edX-hosted programs with unique identification strings "
            "without sensitive personal information. "
            "<br/><br/>"
            "<b>Authentication</b>"
            "<br/><br/>"
            "Authentication for the edX Registrar Service REST API is handled via "
            "JWT Tokens issued by the edX LMS. In order to request a JWT token, "
            "you must first have an edX LMS account that has been granted API access. "
            "<br/><br/>"
            "<b>API Access Request</b>"
            "<br/><br/>"
            "To create an API Access Request, first log in to the edX LMS. "
            "Make sure you are logged into the LMS with the account you are "
            "planning to use for integration with the API. For example, "
            "if you are planning to have a peoplesoft instance communicate with "
            "the edX Registrar API, we recommend creating a new LMS account called "
            "something like 'peoplesoft_worker@school.edu' on the edX LMS, and then "
            "logging in as that worker. Next, navigate to https://courses.edx.org/api-admin/. "
            "Submitting the form will create a request which will be reviewed and approved "
            "by an edX administrator. "
            "<br/>"
            "Once the request has been approved, you can navigate to "
            "https://courses.edx.org/api-admin/status which will display your client_id "
            "and client_secret. "
            "<br/><br/>"
            "<b>JWT Token Request</b>"
            "<br/><br/>"
            "Once you have your client_id and client_secret, you can make a POST request "
            "to https://api.edx.org/oauth2/access_token/  which will return a JSON "
            "dictionary containing the token."
            "<br/><br/>"
            "<b>Sample Request & Response</b>"
            "<br/><br/>"
            "POST https://api.edx.org/oauth2/access_token/ "
            "<br/><br/>"
            "&nbsp;&nbsp;Content-Type: application/x-www-form-urlencoded"
            "<br/><br/>"
            "&nbsp;&nbsp;client_id=my-client-id&"
            "<br/>"
            "&nbsp;&nbsp;client_secret=my-client-secret&"
            "<br/>"    
            "&nbsp;&nbsp;grant_type=client_credentials&"
            "<br/>"
            "&nbsp;&nbsp;token_type=jwt"
            "<br/><br/>"
            "200 OK"
            "<br/>"
            "{"
            "<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;\"token_type\": \"JWT\","
            "<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;\"access_token\": \"really-long-generated-jwt\","
            "<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;\"scope\": \"read write profile email\","
            "<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;\"expires_in\": 3600"
            "<br/>"
            "}"
        ),
    )
)

urlpatterns = oauth2_urlpatterns + [
    # '/' and '/login' redirect to '/login/',
    # which attempts LMS OAuth and then redirects to api-docs.
    url(r'^/?$', RedirectView.as_view(url=settings.LOGIN_URL)),
    url(r'^login$', RedirectView.as_view(url=settings.LOGIN_URL)),

    # Use the same auth views for all logins,
    # including those originating from the browseable API.
    url(r'^api-auth/', include(oauth2_urlpatterns)),

    # NEW Swagger documentation UI, generated using edx-api-doc-tools.
    # TODO: Make this the default as part of MST-195.
    url(r'^api-docs/new$', RedirectView.as_view(pattern_name='api-docs-new')),
    url(r'^api-docs/new/$', new_api_ui_view, name='api-docs-new'),

    # Swagger documentation UI.
    # TODO: Remove as part of MST-195.
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
