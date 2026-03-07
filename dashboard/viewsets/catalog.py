import logging
from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser
from rest_framework.throttling import UserRateThrottle
from rest_framework.decorators import action
from rest_framework.response import Response
from products.models import Product, Category, Subcategory, Color, Room, Style, ProductImage
from users.models import PromoBanner
from dashboard.serializers import (
    CategorySerializer, SubcategorySerializer,
    ColorSerializer, RoomSerializer, StyleSerializer, PromoBannerSerializer,
    ProductSerializer, ProductImageSerializer
)

logger = logging.getLogger(__name__)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = (
        Product.objects
        .all()
        .select_related('category', 'subcategory', 'vendor')
        .prefetch_related('colors', 'rooms', 'styles', 'gallery_images')
    )
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]
    filterset_fields = ['category', 'is_on_sale', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['original_price', 'created_at']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error("Product create validation error: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        product = serializer.save()
        return Response(self.get_serializer(product).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            logger.error("Product update validation error (id=%s): %s", instance.pk, serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        product = serializer.save()
        return Response(self.get_serializer(product).data, status=status.HTTP_200_OK)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def perform_create(self, serializer):
        from products.services.category import create_category
        category = create_category(**serializer.validated_data)
        serializer.instance = category


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


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]


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
