from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from inventory.selectors.stock import get_stock_needed

class StockNeededAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 1000))
        # limit=1000 initially, with pagination taking care of standard lists
        products = get_stock_needed(limit=limit)
        
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_products = paginator.paginate_queryset(products, request)
        return paginator.get_paginated_response(paginated_products)
