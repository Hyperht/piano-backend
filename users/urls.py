from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MyTokenObtainPairView,
    SessionTokenView,
    SocialLoginCallbackView,
    RegisterView,
    UserProfileView,
    UserAddressViewSet,
    GovernorateViewSet,
    AreaViewSet,
    FavoriteViewSet,
    home
)

router = DefaultRouter()
router.register(r'user/addresses', UserAddressViewSet, basename='user-addresses')
router.register(r'governorates', GovernorateViewSet, basename='governorates')
router.register(r'areas', AreaViewSet, basename='areas')
router.register(r'favorites', FavoriteViewSet, basename='favorites')

urlpatterns = [
    path('', home, name='api-home'),
    path('', include(router.urls)),

    # Authentication
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/session-token/', SessionTokenView.as_view(), name='session_token_exchange'),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('auth/social/callback/', SocialLoginCallbackView.as_view(), name='social_login_callback'),

    # User Profile
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
]