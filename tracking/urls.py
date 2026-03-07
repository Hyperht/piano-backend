from django.urls import path
from .api.views import (
    ProductViewTrackingAPIView,
    AddToCartTrackingAPIView,
    WishlistTrackingAPIView,
    CheckoutTrackingAPIView
)

urlpatterns = [
    path('track/view/', ProductViewTrackingAPIView.as_view(), name='track_product_view'),
    path('track/add-to-cart/', AddToCartTrackingAPIView.as_view(), name='track_add_to_cart'),
    path('track/wishlist/', WishlistTrackingAPIView.as_view(), name='track_wishlist'),
    path('track/checkout/', CheckoutTrackingAPIView.as_view(), name='track_checkout'),
]
