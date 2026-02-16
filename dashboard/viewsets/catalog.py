from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.throttling import UserRateThrottle
from users.models import Product, Category, Subcategory, Color, Room, Style, PromoBanner
from dashboard.serializers import (
    ProductSerializer, CategorySerializer, SubcategorySerializer, 
    ColorSerializer, RoomSerializer, StyleSerializer, PromoBannerSerializer
)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category', 'subcategory').prefetch_related('colors', 'rooms', 'styles')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]
    filterset_fields = ['category', 'is_on_sale', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['original_price', 'created_at']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print(f"DEBUG: Product Create Errors: {serializer.errors}")
            return Response(serializer.errors, status=400)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            print(f"DEBUG: Product Update Errors: {serializer.errors}")
            return Response(serializer.errors, status=400)
        return super().update(request, *args, **kwargs, partial=partial)

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
    filterset_fields = ['parent_category']


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

from rest_framework.decorators import action
from rest_framework.response import Response

class PromoBannerViewSet(viewsets.ModelViewSet):
    queryset = PromoBanner.objects.all().order_by('-id')
    serializer_class = PromoBannerSerializer
    permission_classes = [IsAdminUser]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'active']:
            return []
        return [IsAdminUser()]

    @action(detail=False, methods=['get'])
    def active(self, request):
        banner = PromoBanner.objects.filter(is_active=True).order_by('-id').first()
        if banner:
            serializer = self.get_serializer(banner)
            return Response(serializer.data)
        return Response({})
