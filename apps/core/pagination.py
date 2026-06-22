"""
Custom pagination classes for VIPET API.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Default pagination class for the VIPET API.

    - page_size: 20 items per page (default)
    - max_page_size: 100 items per page (maximum allowed via ?page_size= param)
    - page_size_query_param: 'page_size' allows clients to request a custom page size
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
