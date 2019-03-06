""" API v1 URLs. """
from rest_framework import routers

from registrar.apps.api.v1 import views


app_name = 'v1'

router = routers.DefaultRouter()
router.register(r'programs', views.RetrieveProgramViewSet, basename='program')
router.register(r'programs', views.ListProgramViewSet, basename='program')

urlpatterns = router.urls
