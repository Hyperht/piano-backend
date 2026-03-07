from django.urls import path, include
from rest_framework.routers import DefaultRouter
from orders.api.views import (
    CartViewSet, CartItemViewSet, ApplyCouponView, OrderViewSet, CheckoutView,
    RecentOrdersAPIView, AllOrdersAPIView, ExportOrdersAPIView, UpdateOrderStatusAPIView
)

router = DefaultRouter()
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'cart-items', CartItemViewSet, basename='cart-items')
router.register(r'history', OrderViewSet, basename='orders')

urlpatterns = [
    path('', include(router.urls)),
    path('checkout/', CheckoutView.as_view(), name='checkout-order'),
    path('apply-coupon/', ApplyCouponView.as_view(), name='apply-coupon'),
    path('orders/recent/', RecentOrdersAPIView.as_view(), name='recent-orders'),
    path('orders/export/', ExportOrdersAPIView.as_view(), name='export-orders'),
    path('orders/all/', AllOrdersAPIView.as_view(), name='all-orders'),
    path('orders/<int:order_id>/status/', UpdateOrderStatusAPIView.as_view(), name='update-order-status'),
]
