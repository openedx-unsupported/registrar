"""
The public-facing REST API.
"""
import logging

from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
)
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..mixins import TrackViewMixin
from ..serializers import DetailedProgramSerializer
from ..v1.views import ProgramListView
from .pagination import CustomPagination


logger = logging.getLogger(__name__)


class ProgramListPaginationView(ProgramListView, TrackViewMixin, ListAPIView):
    """
    A view for listing program objects.

    Path: /api/[version]/programs?org={org_key}
    """
    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    serializer_class = DetailedProgramSerializer
    pagination_class = CustomPagination
    event_method_map = {'GET': 'registrar.{api_version}.list_programs'}

    def list(self, request):    # pylint: disable=arguments-differ

        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        result = self.get_paginated_response(serializer.data)
        data = result.data

        return Response(data)
