from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError, APIException
from django.db.models import Prefetch
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from django.utils import timezone

from .filters import ProductFilter
from .serializers import (
    RegisterSerializer,
    MyTokenObtainPairSerializer,
    CategorySerializer,
    SubcategorySerializer,
    HeroSlideSerializer,
    PromoBannerSerializer,
    ProductDetailSerializer,
    ReviewSerializer,
    ProductSearchSerializer,
    RoomSerializer,
    StyleSerializer,
    PromoGridCategorySerializer,
    ColorSerializer,
    CartSerializer,
    CartItemSerializer, 
    FavoriteSerializer,
    UserProfileSerializer,
    # NEW IMPORTS
    GovernorateSerializer,
    AreaSerializer, 
    CheckoutSerializer,
    UserAddressSerializer, 
    OrderListSerializer, 
    OrderDetailSerializer, 
    ContactMessageSerializer,
)
from .models import (
    Product,
    Review,
    Favorite,
    Category,
    Subcategory,
    HeroSlide,
    PromoBanner,
    Room,
    Style,
    PromoGridCategory,
    Cart,
    CartItem,
    Color,
    # NEW IMPORTS
    Governorate,
    Area,
    Coupon,
    Address, 
    Order, 
    ContactMessage,
)

User = get_user_model()


def home(request):
    """Simple API root endpoint."""
    return HttpResponse("Welcome to the Piano project! Your API is ready.")


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class MyTokenObtainPairView(TokenObtainPairView):
    """Custom token view for JWTs."""
    serializer_class = MyTokenObtainPairSerializer


class SessionTokenView(APIView):
    """
    Exchanges a Django session (from allauth login) for a JWT access/refresh token pair.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        print("DEBUG: SessionTokenView called")
        print(f"DEBUG: User authenticated? {request.user.is_authenticated}")
        print(f"DEBUG: User: {request.user}")
        print(f"DEBUG: Cookies: {request.COOKIES}")
        print(f"DEBUG: Session ID: {request.session.session_key}")

        # Generate the JWT tokens for the authenticated user
        refresh = RefreshToken.for_user(request.user)
        
        # You can customize the user response as needed
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': request.user.id,
                'email': getattr(request.user, 'email', ''),
                'name': getattr(request.user, 'name', ''),
            }
        })


# --- User Profile View ---
class UserProfileView(generics.RetrieveAPIView):
    """Returns the authenticated user's profile, favorites, and recent orders."""
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Custom get_object that pre-fetches related data for the authenticated user.
        Raises NotFound if the user somehow doesn't exist (unlikely if authenticated).
        """
        try:
            # Filter by the authenticated user's ID (pk)
            qs = User.objects.filter(pk=self.request.user.pk).prefetch_related(
                # Prefetch related data for the serializer
                Prefetch('favorites', queryset=Favorite.objects.select_related('product')),
                Prefetch('order_set', queryset=Order.objects.order_by('-created_at')[:10])
            )
            return qs.get()
        except User.DoesNotExist:
            raise NotFound("User not found")
        except Exception as exc:
            # Emit traceback to server logs for debugging
            import traceback
            traceback.print_exc()
            raise APIException("Failed to retrieve user profile")

    def retrieve(self, request, *args, **kwargs):
        """
        Attempts full retrieve, falls back to a minimal user object on serialization error.
        """
        try:
            obj = self.get_object()
            serializer = self.get_serializer(obj)
            return Response(serializer.data)
        except Exception as exc:
            # Log full traceback for debugging
            import traceback
            traceback.print_exc()
            
            # Try a minimal fallback: return the user without prefetching related data
            try:
                user = User.objects.get(pk=request.user.pk)
                fallback_data = {
                    'id': user.id,
                    'email': getattr(user, 'email', None),
                    'name': getattr(user, 'name', None),
                    'phone_number': getattr(user, 'phone_number', None),
                    # Ensure fields expected by the serializer are present
                    'favorites': [],
                    'orders': [],
                }
                return Response(fallback_data, status=status.HTTP_200_OK)
            except Exception:
                # If even the fallback fails, return a clear API error
                return Response({'detail': 'Failed to retrieve user profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------
# User Address ViewSet
# -----------------------
class UserAddressViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for a user's saved shipping addresses.
    """
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Prefetch the related area and its governorate for read operations
        return Address.objects.filter(user=self.request.user).select_related('area__governorate').order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        """
        Handles creation, ensuring only one default address exists per user
        using an atomic transaction.
        """
        try:
            # Default to False if not present or cannot be parsed
            is_default_requested = bool(serializer.validated_data.get('is_default', False))
        except Exception:
            is_default_requested = False

        try:
            with transaction.atomic():
                # 1) Save the address with is_default=False initially
                created_address = serializer.save(user=self.request.user, is_default=False)

                # 2) If requested, set it as default and clear all others
                if is_default_requested:
                    # Clear any existing default addresses for this user
                    Address.objects.filter(user=self.request.user, is_default=True).exclude(pk=created_address.pk).update(is_default=False)
                    created_address.is_default = True
                    created_address.save(update_fields=['is_default'])
        except IntegrityError as ie:
            import traceback
            traceback.print_exc()
            raise APIException('Failed to save address due to a database constraint. Try again.')
        except Exception:
            import traceback
            traceback.print_exc()
            raise APIException('Failed to save address. Contact support if the problem persists.')

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Action to explicitly set an address as the default."""
        try:
            address_to_set = self.get_queryset().get(pk=pk)
            
            with transaction.atomic():
                # Clear default flag on all other addresses
                self.get_queryset().exclude(pk=pk).update(is_default=False)
                
                # Set this address as default
                address_to_set.is_default = True
                address_to_set.save(update_fields=['is_default'])
            
            serializer = self.get_serializer(address_to_set)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Address.DoesNotExist:
            return Response({'error': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

    def perform_update(self, serializer):
        """
        When updating an address, manage the default flag atomically.
        """
        try:
            is_default_requested = serializer.validated_data.get('is_default', None)
        except Exception:
            is_default_requested = None

        try:
            with transaction.atomic():
                # Save the update with is_default=False first to avoid uniqueness conflict (if it was set)
                # This ensures we get the updated instance back.
                updated_address = serializer.save()

                if is_default_requested is True:
                    # Clear other defaults and set this one
                    Address.objects.filter(user=self.request.user, is_default=True).exclude(pk=updated_address.pk).update(is_default=False)
                    updated_address.is_default = True
                    updated_address.save(update_fields=['is_default'])
                elif is_default_requested is False:
                    # If setting to false, ensure the update takes effect
                    updated_address.is_default = False
                    updated_address.save(update_fields=['is_default'])
                # If is_default_requested is None, no action is taken beyond serializer.save()

        except IntegrityError:
            import traceback
            traceback.print_exc()
            raise APIException('Failed to update address due to a database constraint.')
        except Exception:
            import traceback
            traceback.print_exc()
            raise APIException('Failed to update address. Contact support if the problem persists.')


# -----------------------
# Order ViewSet
# -----------------------
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail views for a user's past orders.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Base queryset: only orders belonging to the authenticated user
        queryset = Order.objects.filter(user=self.request.user).order_by('-created_at')
        
        if self.action == 'retrieve':
            # Optimize detail view to pull all related data
            queryset = queryset.prefetch_related('items__product').select_related('shipping_address__area__governorate', 'coupon')
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return super().get_serializer_class()


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self,):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class SubcategoryListView(generics.ListAPIView):
    serializer_class = SubcategorySerializer
    queryset = Subcategory.objects.all()
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(parent_category__id=category_id)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class HeroSlideViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HeroSlide.objects.filter(is_active=True).order_by('order')
    serializer_class = HeroSlideSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# EDITED: Combine ProductViewSet and ProductDetailViewSet
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing products.
    Includes optimized prefetching for detail view and robust fallback logic for Vue.
    """
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    permission_classes = [AllowAny]

    # -----------------------------------------------------
    # YOUR code
        #filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
        #search_fields = ['name', 'short_description', 'description']
    # MY code
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    # -----------------------------------------------------

    ordering_fields = ['original_price', 'rating', 'created_at']
    ordering = ['-created_at']
    filterset_class = ProductFilter

    def get_queryset(self):
        # Optimized to prefetch related data for detail view
        if self.action == 'retrieve':
            return Product.objects.filter(is_active=True).prefetch_related(
                'colors',
                'gallery_images__color',
                'rooms',
                'styles',
                Prefetch(
                    'reviews',
                    queryset=Review.objects.select_related('user').order_with_respect_to('product') if hasattr(Review.objects, 'order_with_respect_to') else Review.objects.select_related('user').order_by('-created_at')
                ),
                Prefetch(
                    'favorite_set',
                    queryset=Favorite.objects.filter(user=self.request.user)
                    if self.request.user.is_authenticated
                    else Favorite.objects.none()
                )
            ).select_related('category', 'subcategory')
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
        """
        Custom retrieve that forces essential data into the response 
        even if the main serializer encounters an error.
        """
        try:
            # Try normal serialization first
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            # Fallback logic for Vue frontend if the ProductDetailSerializer fails
            import traceback
            print(f"SERIALIZATION ERROR in ProductViewSet: {str(e)}")
            traceback.print_exc()
            
            try:
                pk = kwargs.get('pk')
                product = Product.objects.prefetch_related('colors').get(pk=pk)
                
                # Manually build response structure for Vue frontend
                color_data = [
                    {
                        "id": c.id,
                        "name": c.name,
                        "hex_code": getattr(c, 'hex_code', '#000000') 
                    } for c in product.colors.all()
                ]

                fallback_data = {
                    "id": product.id,
                    "name": product.name or '',
                    "short_description": product.short_description or '',
                    "description": product.description or '',
                    "original_price": str(product.original_price),
                    "sale_price": str(product.sale_price) if product.sale_price else None,
                    "is_on_sale": product.is_on_sale,
                    "image": request.build_absolute_uri(product.image.url) if product.image else None,
                    "colors": color_data,
                    "gallery_images": [],
                    "rating": float(getattr(product, 'rating', 0) or 0),
                    "reviews": [],
                    "category": {"id": product.category.id, "name": product.category.name} if product.category else None,
                    "subcategory": {"id": product.subcategory.id, "name": product.subcategory.name} if product.subcategory else None,
                    "is_favorited": False,
                }
                return Response(fallback_data)
            except Exception:
                return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)



    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['original_price', 'rating', 'created_at']
    ordering = ['-created_at']
    filterset_class = ProductFilter

    queryset = Product.objects.filter(is_active=True)

    def get_queryset(self):
        if self.action == 'retrieve':
            return self.queryset.select_related(
                'category',
                'subcategory'
            ).prefetch_related(
                'colors',
                'gallery_images__color',
                'rooms',
                'styles',
                Prefetch(
                    'reviews',
                    queryset=Review.objects.select_related('user').order_by('-created_at')
                ),
                Prefetch(
                    'favorite_set',
                    queryset=Favorite.objects.filter(user=self.request.user)
                    if self.request.user.is_authenticated
                    else Favorite.objects.none()
                )
            )
        return self.queryset.order_by('-created_at')

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == 'retrieve' else ProductSearchSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    permission_classes = [AllowAny]
   #filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    #search_fields = ['name', 'short_description', 'description']
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['original_price', 'rating', 'created_at']
    ordering = ['-created_at']
    filterset_class = ProductFilter

    def get_queryset(self):
        """
        Optimized queryset.
        Prefetch EVERYTHING needed for product detail page.
        """
        qs = Product.objects.filter(is_active=True)

        if self.action == 'retrieve':
            return qs.select_related(
                'category',
                'subcategory'
            ).prefetch_related(
                'colors',                      # ✅ THIS FIXES YOUR ISSUE
                'gallery_images__color',
                'rooms',
                'styles',
                Prefetch(
                    'reviews',
                    queryset=Review.objects.select_related('user').order_by('-created_at')
                ),
                Prefetch(
                    'favorite_set',
                    queryset=Favorite.objects.filter(user=self.request.user)
                    if self.request.user.is_authenticated
                    else Favorite.objects.none()
                )
            )

        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSearchSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    search_fields = ['name', 'short_description', 'description']
    filterset_class = ProductFilter
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSearchSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            # Try the standard serializer first
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            # If serializer fails, this fallback MANUALLY provides the colors Vue needs
            import traceback
            traceback.print_exc() # Check your terminal to see why the serializer failed!
            
            try:
                product = Product.objects.prefetch_related('colors').get(pk=kwargs.get('pk'))
                
                # We format this exactly how your Vue template :key="colorOption.hex_code" expects
                color_data = [
                    {
                        "name": c.name,
                        "hex_code": getattr(c, 'hex_code', '#000000') 
                    } for c in product.colors.all()
                ]

                fallback_data = {
                    "id": product.id,
                    "name": product.name or '',
                    "name_en": getattr(product, 'name_en', ''),
                    "name_ar": getattr(product, 'name_ar', ''),
                    "short_description": product.short_description or '',
                    "short_description_en": getattr(product, 'short_description_en', ''),
                    "short_description_ar": getattr(product, 'short_description_ar', ''),
                    "description": product.description or '',
                    "description_en": getattr(product, 'description_en', ''),
                    "description_ar": getattr(product, 'description_ar', ''),
                    "original_price": str(product.original_price),
                    "sale_price": str(product.sale_price) if product.sale_price else None,
                    "is_on_sale": product.is_on_sale,
                    "image": request.build_absolute_uri(product.image.url) if getattr(product, 'image', None) else None,
                    "colors": color_data,
                    "gallery_images": [],
                    "rating": getattr(product, 'rating', 0),
                    "reviews": [],
                    "category": {"id": product.category.id, "name": product.category.name} if getattr(product, 'category', None) else None,
                    "subcategory": {"id": product.subcategory.id, "name": product.subcategory.name} if getattr(product, 'subcategory', None) else None,
                    "is_favorited": False,
                }
                return Response(fallback_data)
            except Exception:
                return Response({"detail": "Not found"}, status=404)
            
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    permission_classes = [AllowAny]
    #filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    #search_fields = ['name', 'short_description', 'description']
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['original_price', 'rating', 'created_at']
    ordering = ['-created_at']
    filterset_class = ProductFilter
    
    def get_queryset(self):
        # Optimized to prefetch related data for detail view
        if self.action == 'retrieve':
            return Product.objects.filter(is_active=True).prefetch_related(
                'gallery_images__color',
                'colors',
                'rooms',
                'styles',
                Prefetch('reviews', queryset=Review.objects.select_related('user').order_by('-created_at')), 
                Prefetch(
                    'favorite_set',
                    queryset=Favorite.objects.filter(user=self.request.user) if self.request.user.is_authenticated else Favorite.objects.none()
                )
            ).select_related('category', 'subcategory')
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductSearchSerializer
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Custom retrieve that forces color data into the response 
        even if the main serializer hits an error.
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception:
            # Fallback logic if the ProductDetailSerializer fails
            import traceback
            traceback.print_exc()
            try:
                pk = kwargs.get('pk')
                product = Product.objects.prefetch_related('colors').get(pk=pk)
                
                # MANUALLY BUILD COLOR DATA FOR VUE
                fallback_colors = [
                    {
                        "id": c.id, 
                        "name": c.name, 
                        "hex_code": getattr(c, 'hex_code', '#CCCCCC')
                    } for c in product.colors.all()
                ]

                fallback = {
                    'id': product.id,
                    'name': product.name or '',
                    'name_en': getattr(product, 'name_en', ''),
                    'name_ar': getattr(product, 'name_ar', ''),
                    'short_description': product.short_description or '',
                    'short_description_en': getattr(product, 'short_description_en', ''),
                    'short_description_ar': getattr(product, 'short_description_ar', ''),
                    'original_price': str(product.original_price),
                    'sale_price': str(product.sale_price) if product.sale_price else None,
                    'is_on_sale': product.is_on_sale,
                    'image': request.build_absolute_uri(product.image.url) if getattr(product, 'image', None) else None,
                    'colors': fallback_colors,
                    'rating': getattr(product, 'rating', 0),
                    'gallery_images': [],
                    'reviews': [],
                    'is_favorited': False,
                }
                return Response(fallback, status=status.HTTP_200_OK)
            except Exception:
                return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
            
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    permission_classes = [AllowAny]
    #filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    #search_fields = ['name', 'short_description', 'description']
    ordering_fields = ['original_price', 'rating', 'created_at']
    ordering = ['-created_at']
    filterset_class = ProductFilter
    
    def get_queryset(self):
        # We prefetch 'colors' here so they are available in the fallback too
        if self.action == 'retrieve':
            return Product.objects.filter(is_active=True).prefetch_related(
                'colors', # CRITICAL: Ensure colors are fetched
                'gallery_images',
                'rooms',
                'styles',
                Prefetch('reviews', queryset=Review.objects.select_related('user').order_by('-created_at')), 
                Prefetch(
                    'favorite_set',
                    queryset=Favorite.objects.filter(user=self.request.user) if self.request.user.is_authenticated else Favorite.objects.none()
                )
            ).select_related('category', 'subcategory')
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductSearchSerializer
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSearchSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        try:
            # Try normal serialization first
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            # Log the exact error to your terminal so you can see why it's failing
            print(f"SERIALIZATION ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

            # FALLBACK LOGIC: If the serializer crashes, we still need to send color data
            try:
                pk = kwargs.get('pk')
                product = Product.objects.prefetch_related('colors').get(pk=pk)
                
                # We manually build the color list for the frontend
                fallback_colors = [
                    {"id": c.id, "name": c.name, "hex_code": c.hex_code} 
                    for c in product.colors.all()
                ]

                fallback = {
                    'id': product.id,
                    'name': product.name,
                    'short_description': product.short_description,
                    'original_price': str(product.original_price),
                    'sale_price': str(product.sale_price) if product.sale_price else None,
                    'is_on_sale': product.is_on_sale,
                    'image': request.build_absolute_uri(product.image.url) if product.image else None,
                    'colors': fallback_colors, # FIXED: Added colors to fallback
                    'gallery_images': [],
                    'is_favorited': False
                }
                return Response(fallback, status=status.HTTP_200_OK)
            except Exception:
                return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    permission_classes = [AllowAny]
    #filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    #search_fields = ['name', 'short_description', 'description']
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['original_price', 'rating', 'created_at']
    ordering = ['-created_at']
    filterset_class = ProductFilter
    
    def get_queryset(self):
        # Optimized to prefetch related data for detail view or specific actions
        if self.action == 'retrieve':
            return Product.objects.prefetch_related(
                'gallery_images__color',
                'colors',
                'rooms',
                'styles',
                # Optimize to only fetch reviews and user data for reviews
                Prefetch('reviews', queryset=Review.objects.select_related('user').order_by('-created_at')), 
                Prefetch(
                    'favorite_set',
                    # Only fetch the favorite object if the current user has favorited it
                    queryset=Favorite.objects.filter(user=self.request.user) if self.request.user.is_authenticated else Favorite.objects.none()
                )
            ).select_related(
                'category',
                'subcategory'
            )
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductSearchSerializer
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Robust retrieve: try the full serialization path, but on unexpected
        exceptions return a minimal product representation.
        """
        try:
            obj = self.get_object()
            serializer = self.get_serializer(obj)
            return Response(serializer.data)
        except Exception:
            import traceback
            traceback.print_exc()
            # Attempt a minimal fallback response
            try:
                pk = kwargs.get('pk') or request.parser_context.get('kwargs', {}).get('pk')
                product = Product.objects.filter(pk=pk).first()
                if not product:
                    return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

                # Return minimal data structure
                fallback = {
                    'id': product.id,
                    'name': product.name or '',
                    'name_en': getattr(product, 'name_en', ''),
                    'name_ar': getattr(product, 'name_ar', ''),
                    'short_description': product.short_description or '',
                    'short_description_en': getattr(product, 'short_description_en', ''),
                    'short_description_ar': getattr(product, 'short_description_ar', ''),
                    'original_price': str(product.original_price),
                    'sale_price': str(product.sale_price) if product.sale_price is not None else None,
                    'is_on_sale': product.is_on_sale,
                    'image': request.build_absolute_uri(product.image.url) if product.image and hasattr(product.image, 'url') else None,
                    'colors': [],
                    'gallery_images': [],
                    'reviews': [],
                }
                return Response(fallback, status=status.HTTP_200_OK)
            except Exception:
                traceback.print_exc()
                return Response({'detail': 'Failed to retrieve product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoomViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Room.objects.all().order_by('name')
    serializer_class = RoomSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self,):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class StyleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Style.objects.all().order_by('name')
    serializer_class = StyleSerializer
    permission_classes = [AllowAny]


class ColorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Color.objects.all().order_by('name')
    serializer_class = ColorSerializer
    permission_classes = [AllowAny]


class PromoGridCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PromoGridCategory.objects.filter(is_active=True).order_by('order')
    serializer_class = PromoGridCategorySerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_promo_banner(request):
    """Retrieve the single active promo banner."""
    try:
        promo_banner = PromoBanner.objects.filter(is_active=True).order_by('-end_date').first()
        if promo_banner:
            serializer = PromoBannerSerializer(promo_banner, context={'request': request})
            return Response(serializer.data)
        else:
            return Response({"error": "No active promo banner found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def debug_filters(request):
    """Debug endpoint: echoes query params and shows how ProductFilter resolves them."""
    try:
        params = {k: request.GET.getlist(k) for k in request.GET.keys()}
        base_qs = Product.objects.filter(is_active=True)
        # apply ProductFilter (pass request so FilterSet can access getlist and other helpers)
        pf = ProductFilter(request.GET, queryset=base_qs, request=request)
        qs = pf.qs
        count = qs.count()
        sample = list(qs.values('id', 'name')[:5])
        return JsonResponse({'received': params, 'count': count, 'sample': sample})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_suggestions(request):
    """Simple suggestions endpoint: returns product name suggestions based on a prefix."""
    q = request.GET.get('q', '')
    try:
        limit = int(request.GET.get('limit', 10))
    except Exception:
        limit = 10
    if not q:
        return Response({'suggestions': []})
    qs = Product.objects.filter(is_active=True, name__istartswith=q).order_by('name')[:limit]
    suggestions = [p.name for p in qs]
    return Response({'suggestions': suggestions})


# -----------------------
# Shopping Cart ViewSet
# -----------------------
class CartViewSet(viewsets.ModelViewSet):
    """
    Handles retrieval and modifications (via actions) of the user's single cart.
    """
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Returns the single cart for the authenticated user."""
        return Cart.objects.filter(user=self.request.user).select_related('coupon').prefetch_related(
            'items__product__colors',
            'items__product__category',
            'items__product__subcategory',
        )

    def list(self, request, *args, **kwargs):
        """GET /api/cart/ will return the user's cart object."""
        try:
            # Get the cart and its data (using the optimized queryset)
            cart = self.get_queryset().get()
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except Cart.DoesNotExist:
            # If the cart doesn't exist, return an empty structure (200 OK)
            return Response({'items': [], 'cart_subtotal': '0.00', 'coupon_discount_amount': '0.00', 'total_price': '0.00', 'coupon': None}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        # Redirect retrieve to list for simpler URL routing for the single cart instance
        return self.list(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Action to add a product to the cart (or increase quantity)."""
        try:
            cart, _ = Cart.objects.get_or_create(user=self.request.user)
            product_id = request.data.get('product_id')
            quantity = int(request.data.get('quantity', 1))
            
            try:
                # Ensure the product exists and is active
                product = Product.objects.get(pk=product_id, is_active=True)
            except Product.DoesNotExist:
                return Response({"error": "Product not found or inactive."}, status=status.HTTP_404_NOT_FOUND)

            # Get or create the cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )

            if not created:
                # If item already exists, increase quantity
                cart_item.quantity += quantity
                cart_item.save()
            
            # Return the updated cart (re-fetch to apply model/serializer calculations)
            updated_cart = self.get_queryset().get(user=self.request.user)
            serializer = self.get_serializer(updated_cart)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except (ValueError, TypeError):
             return Response({"error": "Quantity must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to add item: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

# -----------------------
# Apply Coupon View
# -----------------------
class ApplyCouponView(generics.UpdateAPIView):
    """Handles applying or removing a coupon code to the user's cart."""
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer
    
    def get_object(self):
        """Returns the cart object for the authenticated user."""
        try:
            # Use the optimized queryset logic from CartViewSet
            cart_qs = Cart.objects.filter(user=self.request.user).select_related('coupon').prefetch_related(
                'items__product__colors',
                'items__product__category',
                'items__product__subcategory',
            )
            cart = cart_qs.get()
            return cart
        except Cart.DoesNotExist:
            # CRITICAL: We create the cart if it doesn't exist, to apply a coupon.
            cart, created = Cart.objects.get_or_create(user=self.request.user)
            # Re-fetch with prefetch if we just created it.
            if created:
                cart = self.get_queryset().get(pk=cart.pk) # Using CartViewSet's queryset logic
            return cart

    def put(self, request, *args, **kwargs):
        # Get the cart instance
        cart = self.get_object() 
        coupon_code = request.data.get('coupon_code', '').strip()
        
        # --- Logic to remove a coupon (if code is empty) ---
        if not coupon_code:
            cart.coupon = None
            cart.save()
            # Return the updated cart
            serializer = self.get_serializer(cart) 
            return Response(serializer.data, status=status.HTTP_200_OK)

        # --- Logic to apply a new coupon ---
        try:
            coupon = Coupon.objects.get(
                code__iexact=coupon_code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
        except Coupon.DoesNotExist:
            raise ValidationError({'coupon_code': 'Invalid or expired coupon code.'})

        # Apply the coupon
        cart.coupon = coupon
        cart.save()
        
        # Return the updated cart
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------
# Shopping Cart Item ViewSet
# -----------------------
class CartItemViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD operations for individual cart items (e.g., updating quantity, deletion).
    """
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only allow users to see and modify their own cart items."""
        return CartItem.objects.filter(cart__user=self.request.user).select_related('product')
    
    # NOTE: The add_item action on CartViewSet is often preferred over a custom create method here,
    # but for completeness, we ensure perform_create works.
    def perform_create(self, serializer):
        # Ensure the item is created in the user's cart
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        # The serializer handles product validation, we supply the cart
        serializer.save(cart=cart)
    

# -----------------------
# User Favorites ViewSet
# -----------------------
class FavoriteViewSet(viewsets.ModelViewSet):
    """
    A viewset for a user's favorite products.
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Optimized to prefetch the product data
        return Favorite.objects.filter(user=self.request.user).prefetch_related('product')

    @action(detail=False, methods=['post'])
    def add_or_remove(self, request):
        """Toggles a product's favorite status for the authenticated user."""
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product_pk = int(product_id)
        except (ValueError, TypeError):
            return Response({'error': 'Product ID must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)

            if not created:
                # Removal
                favorite.delete()
                return Response({'message': 'Product removed from favorites', 'is_favorited': False}, status=status.HTTP_200_OK)

            # Addition
            serializer = FavoriteSerializer(favorite, context={'request': request})
            return Response({'message': 'Product added to favorites', 'is_favorited': True, 'favorite': serializer.data}, status=status.HTTP_201_CREATED)

        except Exception as exc:
            import traceback
            traceback.print_exc()
            return Response({'error': 'Internal server error toggling favorite', 'details': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        # Overridden to ensure the user only deletes their own favorite
        try:
            favorite = self.get_queryset().get(pk=self.kwargs['pk'])
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            return Response({"error": "Favorite not found."}, status=status.HTTP_404_NOT_FOUND)


# -----------------------
# Product Review ViewSet
# -----------------------
class ReviewViewSet(viewsets.ModelViewSet):
    """
    Handles nested reviews under a product (e.g., /products/1/reviews/).
    """
    serializer_class = ReviewSerializer
    
    def get_queryset(self):
        # Filter reviews based on the URL's product_pk
        product_pk = self.kwargs.get('product_pk')
        if product_pk:
            # Select related user for the review serializer
            return Review.objects.filter(product_id=product_pk).select_related('user').order_by('-created_at')
        return Review.objects.none()
    
    def get_permissions(self):
        # Only authenticated users can create/update/delete reviews
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        # All users can view reviews
        return [AllowAny()]
    
    def get_object(self):
        """Ensures the user only updates/deletes their own review."""
        # Use get_queryset to ensure the review belongs to the correct product
        # and then filter by the primary key from the URL kwargs.
        try:
            obj = self.get_queryset().get(pk=self.kwargs['pk'])
        except Review.DoesNotExist:
            raise NotFound('Review not found.')
        
        if self.action in ['update', 'partial_update', 'destroy'] and obj.user != self.request.user:
            # Raise 404 (NotFound) to hide existence/deny access
            raise NotFound('Review not found or you do not have permission.')
        
        return obj

    def perform_create(self, serializer):
        product_pk = self.kwargs.get('product_pk')
        try:
            product = Product.objects.get(pk=product_pk)
            # Check for existing review explicitly before saving
            if Review.objects.filter(user=self.request.user, product=product).exists():
                raise ValidationError({"non_field_errors": ["You have already reviewed this product."]})

            serializer.save(user=self.request.user, product=product)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")
        except ValidationError:
            # Re-raise the validation error for DRF to handle
            raise
        except Exception as e:
            # Catch potential unique constraint errors
            if 'unique constraint' in str(e).lower():
                raise ValidationError({"non_field_errors": ["You have already reviewed this product."]})
            raise e

# -----------------------
# Location ViewSet (Governorates & Areas)
# -----------------------
class GovernorateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a list of Governorates and their associated Areas and shipping costs.
    """
    # CRITICAL: Prefetch the related 'areas' for nested serialization
    queryset = Governorate.objects.all().prefetch_related('areas') 
    serializer_class = GovernorateSerializer
    permission_classes = [AllowAny]

class AreaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a list of Areas, used for populating shipping address forms.
    Can be filtered by governorate_id via query params.
    """
    # CRITICAL: Select related governorate to display shipping info
    queryset = Area.objects.all().select_related('governorate')
    serializer_class = AreaSerializer 
    permission_classes = [AllowAny] 

    def get_queryset(self):
        queryset = super().get_queryset()
        governorate_id = self.request.query_params.get('governorate_id')
        if governorate_id:
            try:
                queryset = queryset.filter(governorate__id=int(governorate_id))
            except ValueError:
                # Ignore invalid governorate_id and return all
                pass
        return queryset
    
# -----------------------
# Final Checkout View
# -----------------------
class CheckoutView(generics.CreateAPIView):
    """
    Handles the final POST request to convert the user's cart into an Order.
    """
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Validate data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # `perform_create` calls serializer.create(), which executes the atomic logic
        order = self.perform_create(serializer)
        
        # Using OrderDetailSerializer to return the full order object for immediate confirmation
        order_serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(
            order_serializer.data, 
            status=status.HTTP_201_CREATED
        )

    def perform_create(self, serializer):
        # This calls the complex, atomic logic defined in CheckoutSerializer's create()
        return serializer.save(user=self.request.user)


# -----------------------
# Contact Message ViewSet
# -----------------------
class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    A viewset for creating contact messages.
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']