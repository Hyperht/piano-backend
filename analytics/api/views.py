from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import AnalyticsFilterSerializer
from analytics.services.aggregation_service import AggregationService
from analytics.selectors.sales import (
    get_revenue_chart, get_orders_chart, get_top_selling,
    get_most_watched, get_most_wishlisted
)
from dashboard.serializers import UserSerializer

class DashboardSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        vendor_id = serializer.validated_data.get('vendor_id')
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        
        data = AggregationService.get_dashboard_summary(
            vendor=vendor_id, 
            start_date=start_date, 
            end_date=end_date
        )
        return Response(data)

class SalesBreakdownAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        vendor_id = serializer.validated_data.get('vendor_id')
        
        data = AggregationService.get_sales_breakdown(vendor=vendor_id)
        return Response(data)

class TopProductsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        vendor_id = serializer.validated_data.get('vendor_id')
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        category_val = request.query_params.get('category_id') or request.query_params.get('category')
        category_id = None
        if category_val:
            if str(category_val).isdigit():
                category_id = int(category_val)
            else:
                from products.models import Category
                cat = Category.objects.filter(name=category_val).first()
                if cat:
                    category_id = cat.id

        data = AggregationService.get_top_performing_products(
            vendor=vendor_id, 
            limit=5, 
            category_id=category_id,
            start_date=start_date,
            end_date=end_date
        )
        return Response(data)

from rest_framework.pagination import PageNumberPagination
from analytics.selectors.aggregations import get_top_products

class TopProductsAllAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        vendor_id = serializer.validated_data.get('vendor_id')
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        category_val = request.query_params.get('category_id') or request.query_params.get('category')
        category_id = None
        if category_val:
            if str(category_val).isdigit():
                category_id = int(category_val)
            else:
                from products.models import Category
                cat = Category.objects.filter(name=category_val).first()
                if cat:
                    category_id = cat.id

        # Limit 1000 for See All, paginated via DRF
        products = get_top_products(
            limit=1000, 
            category_id=category_id, 
            start_date=start_date, 
            end_date=end_date, 
            vendor=vendor_id
        )
        
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_products = paginator.paginate_queryset(products, request)
        return paginator.get_paginated_response(paginated_products)

class TopWatchedAllAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Using 1000 limit for simplicity in this detail view
        products = get_most_watched(limit=1000)
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_data = paginator.paginate_queryset(products, request)
        return paginator.get_paginated_response(paginated_data)

class TopWishlistedAllAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        products = get_most_wishlisted(limit=1000)
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_data = paginator.paginate_queryset(products, request)
        return paginator.get_paginated_response(paginated_data)

class FunnelAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        from analytics.services.funnel_service import FunnelService
        data = FunnelService.get_funnel_data(filters=serializer.validated_data)
        return Response(data)

class IntentAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        from analytics.services.funnel_service import FunnelService
        data = FunnelService.get_intent_data(filters=serializer.validated_data)
        return Response(data)

class TrafficSourceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        from analytics.services.funnel_service import FunnelService
        data = FunnelService.get_traffic_source_data(filters=serializer.validated_data)
        return Response(data)

# Dashboard Legacy Views (Restored for dashboard.urls.py)
class DashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = AggregationService.get_dashboard_summary(
            vendor=None,
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date'),
        )
        return Response(data)

class RevenueChartView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        period = request.query_params.get('period', 30)
        return Response(get_revenue_chart(period=period))

class OrdersChartView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        period = request.query_params.get('period', 30)
        return Response(get_orders_chart(period=period))

class TopProductsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        category_val = request.query_params.get('category', '')
        category_id = None
        if category_val:
            if str(category_val).isdigit():
                category_id = int(category_val)
            else:
                from products.models import Category
                cat = Category.objects.filter(name=category_val).first()
                if cat:
                    category_id = cat.id
        
        data = AggregationService.get_top_performing_products(
            vendor=None,
            limit=5,
            category_id=category_id,
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date'),
        )
        return Response(data.get('by_units', []))

class AdminProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({
            'user': {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'role': 'admin' if request.user.is_staff else 'user'
            }
        })
