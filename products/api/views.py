from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch

from products.models import Product, Category, Subcategory, Room, Style, Color
from users.filters import ProductFilter  # Will need to move this later or keep importing for now
from products.api.serializers import (
    ProductDetailSerializer, ProductSearchSerializer, 
    CategorySerializer, SubcategorySerializer, 
    RoomSerializer, StyleSerializer, ColorSerializer,
    ReviewSerializer
)
from products.selectors.catalog import get_product_detail_queryset, get_most_watched
from products.services.catalog import increment_product_views
from tracking.services.tracking_service import TrackingService
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

class MostWatchedAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        limit = int(request.query_params.get('limit', 1000))
        queryset = get_most_watched(limit=limit)
        
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(paginated_queryset)

class ProductViewSet(viewsets.ModelViewSet):
    """
    Unified ProductViewSet handling list, search, filter, and retrieve.
    """
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['name', 'short_description', 'description']
    ordering_fields = ['original_price', 'rating', 'created_at']
    ordering = ['-created_at']
    filterset_class = ProductFilter

    def get_queryset(self):
        # Optimized queryset for retrieve
        if self.action == 'retrieve':
            return get_product_detail_queryset(self.request.user)
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSearchSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        # 1. Atomic View Increment via Service
        pk = kwargs.get('pk')
        increment_product_views(pk)

        # 2. Track Event
        try:
            instance = self.get_object()
            TrackingService.track_product_view(request, instance)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception:
            # 3. Fallback for Vue Compatibility (if serializer fails)
            import traceback
            traceback.print_exc()
            try:
                product = Product.objects.prefetch_related('colors').get(pk=pk)
                
                color_data = [
                    {
                        "id": c.id,
                        "name": c.name,
                        "hex_code": getattr(c, 'hex_code', '#000000') 
                    } for c in product.colors.all()
                ]

                # Fixed fallback image access
                first_img = product.gallery_images.filter(is_primary=True).first() or product.gallery_images.first()
                fallback = {
                    'id': product.id,
                    'name': product.name or '',
                    'short_description': product.short_description or '',
                    'description': product.description or '',
                    'original_price': str(product.original_price),
                    'sale_price': str(product.sale_price) if product.sale_price else None,
                    'is_on_sale': product.is_on_sale,
                    'image': request.build_absolute_uri(first_img.image.url) if first_img and first_img.image else None,
                    'colors': color_data,
                    'gallery_images': [],
                    'rating': getattr(product, 'rating', 0),
                    'reviews': [],
                    'category': {"id": product.category.id, "name": product.category.name} if product.category else None,
                    'subcategory': {"id": product.subcategory.id, "name": product.subcategory.name} if product.subcategory else None,
                    'is_favorited': False,
                    'views_count': getattr(product, 'views_count', 0)
                }
                return Response(fallback, status=status.HTTP_200_OK)
            except Exception:
                return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='increment-view')
    def increment_view(self, request, pk=None):
        try:
            product = self.get_object()
            increment_product_views(pk)
            TrackingService.track_product_view(request, product)
            return Response({'status': 'view incremented'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        try:
            product = self.get_object()
            reviews = product.reviews.all().order_by('-created_at')
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class SubcategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubcategorySerializer
    queryset = Subcategory.objects.all()
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(parent_category__id=category_id)
        return queryset


class RoomViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Room.objects.all().order_by('name')
    serializer_class = RoomSerializer
    permission_classes = [AllowAny]


class StyleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Style.objects.all().order_by('name')
    serializer_class = StyleSerializer
    permission_classes = [AllowAny]


class ColorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Color.objects.all().order_by('name')
    serializer_class = ColorSerializer
    permission_classes = [AllowAny]
