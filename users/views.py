from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError, APIException
from django.db.models import Prefetch, F
from django.db import transaction, IntegrityError
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import os
from urllib.parse import urlencode

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
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'detail': 'User not authenticated via session.'}, status=401)

        refresh = RefreshToken.for_user(request.user)
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
        try:
            # FIXED: Removed slice from Prefetch to avoid TypeError
            qs = User.objects.filter(pk=self.request.user.pk).prefetch_related(
                Prefetch('favorites', queryset=Favorite.objects.select_related('product')),
                Prefetch('orders', queryset=Order.objects.order_by('-created_at'))
            )
            return qs.get()
        except User.DoesNotExist:
            raise NotFound("User not found")
        except Exception as exc:
            import traceback
            traceback.print_exc()
            raise APIException("Failed to retrieve user profile")

    def retrieve(self, request, *args, **kwargs):
        try:
            obj = self.get_object()
            serializer = self.get_serializer(obj)
            return Response(serializer.data)
        except Exception:
            # Fallback
            try:
                user = User.objects.get(pk=request.user.pk)
                fallback_data = {
                    'id': user.id,
                    'email': getattr(user, 'email', None),
                    'name': getattr(user, 'name', None),
                    'phone_number': getattr(user, 'phone_number', None),
                    'favorites': [],
                    'orders': [],
                }
                return Response(fallback_data, status=status.HTTP_200_OK)
            except Exception:
                return Response({'detail': 'Failed to retrieve user profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------
# User Address ViewSet
# -----------------------
class UserAddressViewSet(viewsets.ModelViewSet):
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).select_related('area__governorate').order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        try:
            is_default_requested = bool(serializer.validated_data.get('is_default', False))
        except Exception:
            is_default_requested = False

        try:
            with transaction.atomic():
                created_address = serializer.save(user=self.request.user, is_default=False)
                if is_default_requested:
                    Address.objects.filter(user=self.request.user, is_default=True).exclude(pk=created_address.pk).update(is_default=False)
                    created_address.is_default = True
                    created_address.save(update_fields=['is_default'])
        except IntegrityError:
            raise APIException('Failed to save address due to a database constraint.')

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        try:
            address_to_set = self.get_queryset().get(pk=pk)
            with transaction.atomic():
                self.get_queryset().exclude(pk=pk).update(is_default=False)
                address_to_set.is_default = True
                address_to_set.save(update_fields=['is_default'])
            serializer = self.get_serializer(address_to_set)
            return Response(serializer.data)
        except Address.DoesNotExist:
            return Response({'error': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

    def perform_update(self, serializer):
        try:
            is_default_requested = serializer.validated_data.get('is_default', None)
        except Exception:
            is_default_requested = None

        try:
            with transaction.atomic():
                updated_address = serializer.save()
                if is_default_requested is True:
                    Address.objects.filter(user=self.request.user, is_default=True).exclude(pk=updated_address.pk).update(is_default=False)
                    updated_address.is_default = True
                    updated_address.save(update_fields=['is_default'])
                elif is_default_requested is False:
                    updated_address.is_default = False
                    updated_address.save(update_fields=['is_default'])
        except IntegrityError:
             raise APIException('Failed to update address constraint.')


# -----------------------
# Order ViewSet
# -----------------------
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user).order_by('-created_at')
        if self.action == 'retrieve':
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


class HeroSlideViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HeroSlide.objects.filter(is_active=True).order_by('order')
    serializer_class = HeroSlideSerializer
    permission_classes = [AllowAny]


# --------------------------------------------------------
# CONSOLIDATED PRODUCT VIEWSET
# --------------------------------------------------------
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
            return Product.objects.filter(is_active=True).select_related(
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
        # 1. Atomic View Increment
        try:
            Product.objects.filter(pk=kwargs.get('pk')).update(views=F('views') + 1)
        except Exception:
            pass

        # 2. Serialize
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception:
            # 3. Fallback for Vue Compatibility (if serializer fails)
            import traceback
            traceback.print_exc()
            try:
                pk = kwargs.get('pk')
                product = Product.objects.prefetch_related('colors').get(pk=pk)
                
                color_data = [
                    {
                        "id": c.id,
                        "name": c.name,
                        "hex_code": getattr(c, 'hex_code', '#000000') 
                    } for c in product.colors.all()
                ]

                fallback = {
                    'id': product.id,
                    'name': product.name or '',
                    'short_description': product.short_description or '',
                    'description': product.description or '',
                    'original_price': str(product.original_price),
                    'sale_price': str(product.sale_price) if product.sale_price else None,
                    'is_on_sale': product.is_on_sale,
                    'image': request.build_absolute_uri(product.image.url) if product.image else None,
                    'colors': color_data,
                    'gallery_images': [],
                    'rating': getattr(product, 'rating', 0),
                    'reviews': [],
                    'category': {"id": product.category.id, "name": product.category.name} if product.category else None,
                    'subcategory': {"id": product.subcategory.id, "name": product.subcategory.name} if product.subcategory else None,
                    'is_favorited': False
                }
                return Response(fallback, status=status.HTTP_200_OK)
            except Exception:
                return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='increment-view')
    def increment_view(self, request, pk=None):
        try:
            Product.objects.filter(pk=pk).update(views=F('views') + 1)
            return Response({'status': 'view incremented'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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


class PromoGridCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PromoGridCategory.objects.filter(is_active=True).order_by('order')
    serializer_class = PromoGridCategorySerializer
    permission_classes = [AllowAny]


@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_promo_banner(request):
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
    try:
        params = {k: request.GET.getlist(k) for k in request.GET.keys()}
        base_qs = Product.objects.filter(is_active=True)
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
    q = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 10))
    if not q:
        return Response({'suggestions': []})
    qs = Product.objects.filter(is_active=True, name__istartswith=q).order_by('name')[:limit]
    suggestions = [p.name for p in qs]
    return Response({'suggestions': suggestions})


# -----------------------
# Shopping Cart ViewSet
# -----------------------
class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).select_related('coupon').prefetch_related(
            'items__product__colors',
            'items__product__category',
            'items__product__subcategory',
        )

    def list(self, request, *args, **kwargs):
        try:
            cart = self.get_queryset().get()
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except Cart.DoesNotExist:
            return Response({'items': [], 'cart_subtotal': '0.00', 'coupon_discount_amount': '0.00', 'total_price': '0.00', 'coupon': None}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        try:
            cart, _ = Cart.objects.get_or_create(user=self.request.user)
            product_id = request.data.get('product_id')
            quantity = int(request.data.get('quantity', 1))
            
            try:
                product = Product.objects.get(pk=product_id, is_active=True)
            except Product.DoesNotExist:
                return Response({"error": "Product not found or inactive."}, status=status.HTTP_404_NOT_FOUND)

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            updated_cart = self.get_queryset().get(user=self.request.user)
            serializer = self.get_serializer(updated_cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to add item: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class ApplyCouponView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer
    
    def get_object(self):
        try:
            cart_qs = Cart.objects.filter(user=self.request.user).select_related('coupon').prefetch_related(
                'items__product__colors',
                'items__product__category',
                'items__product__subcategory',
            )
            return cart_qs.get()
        except Cart.DoesNotExist:
            cart, created = Cart.objects.get_or_create(user=self.request.user)
            if created:
                # Re-fetch using logic consistent with CartViewSet if possible, or just return basic cart
                pass
            return cart

    def put(self, request, *args, **kwargs):
        cart = self.get_object() 
        coupon_code = request.data.get('coupon_code', '').strip()
        
        if not coupon_code:
            cart.coupon = None
            cart.save()
            serializer = self.get_serializer(cart) 
            return Response(serializer.data, status=status.HTTP_200_OK)

        try:
            coupon = Coupon.objects.get(
                code__iexact=coupon_code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
        except Coupon.DoesNotExist:
            raise ValidationError({'coupon_code': 'Invalid or expired coupon code.'})

        cart.coupon = coupon
        cart.save()
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user).select_related('product')
    
    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).prefetch_related('product')

    @action(detail=False, methods=['post'])
    def add_or_remove(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product_pk = int(product_id)
            product = Product.objects.get(pk=product_pk)
            favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)

            if not created:
                favorite.delete()
                return Response({'message': 'Product removed from favorites', 'is_favorited': False}, status=status.HTTP_200_OK)

            serializer = FavoriteSerializer(favorite, context={'request': request})
            return Response({'message': 'Product added to favorites', 'is_favorited': True, 'favorite': serializer.data}, status=status.HTTP_201_CREATED)

        except Exception as exc:
            return Response({'error': 'Error toggling favorite', 'details': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        try:
            favorite = self.get_queryset().get(pk=self.kwargs['pk'])
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            return Response({"error": "Favorite not found."}, status=status.HTTP_404_NOT_FOUND)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    
    def get_queryset(self):
        product_pk = self.kwargs.get('product_pk')
        if product_pk:
            return Review.objects.filter(product_id=product_pk).select_related('user').order_by('-created_at')
        return Review.objects.none()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_object(self):
        try:
            obj = self.get_queryset().get(pk=self.kwargs['pk'])
        except Review.DoesNotExist:
            raise NotFound('Review not found.')
        
        if self.action in ['update', 'partial_update', 'destroy'] and obj.user != self.request.user:
            raise NotFound('Review not found or you do not have permission.')
        return obj

    def perform_create(self, serializer):
        product_pk = self.kwargs.get('product_pk')
        try:
            product = Product.objects.get(pk=product_pk)
            # Check for existing review
            if Review.objects.filter(user=self.request.user, product=product).exists():
                raise ValidationError({"non_field_errors": ["You have already reviewed this product."]})
            serializer.save(user=self.request.user, product=product)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")
        except ValidationError:
            raise
        except Exception as e:
            if 'unique constraint' in str(e).lower():
                raise ValidationError({"non_field_errors": ["You have already reviewed this product."]})
            raise e


class GovernorateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Governorate.objects.all().prefetch_related('areas') 
    serializer_class = GovernorateSerializer
    permission_classes = [AllowAny]

class AreaViewSet(viewsets.ReadOnlyModelViewSet):
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
                pass
        return queryset


class CheckoutView(generics.CreateAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.perform_create(serializer)
        order_serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)


class SocialLoginCallbackView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            frontend_url = os.getenv('FRONTEND_URL')
            error_params = urlencode({'error': 'authentication_failed'})
            return redirect(f"{frontend_url}/login?{error_params}")
        
        user = request.user
        try:
            from allauth.socialaccount.models import SocialAccount
            social_account = SocialAccount.objects.filter(user=user).first()
            if social_account:
                extra_data = social_account.extra_data
                if not user.name and extra_data.get('name'):
                    user.name = extra_data.get('name')
                    user.save(update_fields=['name'])
        except Exception:
            pass
        
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        frontend_url = os.getenv('FRONTEND_URL')
        params = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user_id': user.id,
            'user_email': user.email,
            'user_name': getattr(user, 'name', ''),
        }
        
        redirect_url = f"{frontend_url}/auth/callback?{urlencode(params)}"
        return redirect(redirect_url)


class ContactMessageViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']