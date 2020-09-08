"""Pagination class for API V3"""
from rest_framework.pagination import PageNumberPagination


DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 100


class CustomPagination(PageNumberPagination):
    """
    Custom class for paginating objects
    """
    page = DEFAULT_PAGE
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = 'page_size'
