from django.urls import path, include
from rest_framework.routers import DefaultRouter
from marketing.api.views import (
    HeroSlideViewSet, PromoGridCategoryViewSet, get_active_promo_banner,
    ValidateCouponView, CouponAnalyticsAPIView, TopCouponsAPIView, CampaignPerformanceAPIView,
)

router = DefaultRouter()
router.register(r'hero-slides', HeroSlideViewSet, basename='hero-slides')
router.register(r'promo-grid-categories', PromoGridCategoryViewSet, basename='promo-grid-categories')

urlpatterns = [
    path('', include(router.urls)),
    path('promo-banner/', get_active_promo_banner, name='active-promo-banner'),
    path('validate-coupon/', ValidateCouponView.as_view(), name='validate-coupon'),
    path('coupon-analytics/', CouponAnalyticsAPIView.as_view(), name='coupon-analytics'),
    path('coupons/analytics/', TopCouponsAPIView.as_view(), name='top-coupons-analytics'),
    path('campaign-performance/', CampaignPerformanceAPIView.as_view(), name='campaign-performance'),
]
