"""
The public-facing REST API.
"""
import logging

from edx_api_doc_tools import query_parameter, schema_for
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

SCHEMA_COMMON_RESPONSES = {
    401: 'User is not authenticated.',
    405: 'HTTP method not support on this path.'
}


@schema_for(
    'get',
    parameters=[
        query_parameter('org_key', str, 'Organization filter'),
        query_parameter('user_has_perm', str, 'Permission filter'),
    ],
    responses={
        403: 'User lacks access to organization.',
        404: 'Organization does not exist.',
        **SCHEMA_COMMON_RESPONSES,
    },
)
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
