""" API v1 URLs. """
from rest_framework import routers

from .views import ProgramReadOnlyViewSet


app_name = 'v1'

router = routers.DefaultRouter()
router.register(r'programs', ProgramReadOnlyViewSet, basename='program')

urlpatterns = router.urls
