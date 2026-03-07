from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError, APIException
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import os
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

from .serializers import (
    RegisterSerializer, MyTokenObtainPairSerializer, UserProfileSerializer,
    GovernorateSerializer, AreaSerializer, UserAddressSerializer, FavoriteSerializer
)
from .models import Favorite, Governorate, Area, Address
from users.services.auth import set_default_address
from users.selectors.profile import get_user_profile
from tracking.services.tracking_service import TrackingService

User = get_user_model()

def home(request):
    """Simple API root endpoint."""
    return HttpResponse("Welcome to the Piano project! Your API is ready.")

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        logger.info(f"Login attempt: {request.data}")
        try:
            response = super().post(request, *args, **kwargs)
            logger.info("Login successful")
            return response
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SessionTokenView(APIView):
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

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # logger.info(f"Profile access for user: {request.user}")
        try:
            profile = get_user_profile(user=request.user)
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        except Exception as e:
            # logger.error(f"Profile access error: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserAddressViewSet(viewsets.ModelViewSet):
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).select_related('area__governorate').order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        is_default = serializer.validated_data.get('is_default', False)
        created_address = serializer.save(user=self.request.user, is_default=False)
        if is_default:
            set_default_address(self.request.user, created_address.pk)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        try:
            address = set_default_address(request.user, pk)
            serializer = self.get_serializer(address)
            return Response(serializer.data)
        except Address.DoesNotExist:
            return Response({'error': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

    def perform_update(self, serializer):
        is_default = serializer.validated_data.get('is_default', None)
        updated_address = serializer.save()
        if is_default is True:
            set_default_address(self.request.user, updated_address.pk)

class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).prefetch_related('product')

    @action(detail=False, methods=['post'])
    def add_or_remove(self, request):
        from products.models import Product
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.get(pk=product_id)
            favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)

            if created:
                try:
                    TrackingService.track_wishlist(request, product)
                except Exception as te:
                    logger.warning(f"Wishlist tracking failed for product {product_id}: {te}")

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