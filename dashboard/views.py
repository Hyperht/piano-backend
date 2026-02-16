from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.throttling import UserRateThrottle
from rest_framework import status
from .services import DashboardService

class DashboardAnalyticsView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        try:
            data = DashboardService.get_aggregated_analytics()
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RevenueChartView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        period = request.query_params.get('period', 30)
        try:
            data = DashboardService.get_revenue_chart(period)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrdersChartView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        period = request.query_params.get('period', 30)
        try:
            data = DashboardService.get_orders_chart(period)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TopProductsView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        category = request.query_params.get('category')
        try:
            data = DashboardService.get_top_selling_products(category)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminProfileView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_superuser": user.is_superuser
        })

from rest_framework import viewsets
from users.models import Product, Category, Subcategory, Order, CustomUser, Color, Room, Style
from .serializers import (
    ProductSerializer, CategorySerializer, SubcategorySerializer, 
    OrderSerializer, UserSerializer, ColorSerializer, RoomSerializer, StyleSerializer
)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category', 'subcategory').prefetch_related('colors', 'rooms', 'styles')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]
    filterset_fields = ['category', 'is_on_sale', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    def retrieve(self, request, *args, **kwargs):
        from django.db.models import F
        instance = self.get_object()
        Product.objects.filter(pk=instance.pk).update(views=F('views') + 1)
        instance.views += 1
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all().select_related('parent_category')
    serializer_class = SubcategorySerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related('user').prefetch_related('items__product')
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]
    filterset_fields = ['status', 'user']
    search_fields = ['id', 'user__email']
    ordering_fields = ['created_at', 'final_total']

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]
    search_fields = ['email', 'username']

class ColorViewSet(viewsets.ModelViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

class StyleViewSet(viewsets.ModelViewSet):
    queryset = Style.objects.all()
    serializer_class = StyleSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]
