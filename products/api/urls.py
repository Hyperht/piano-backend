from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.api.views import (
    ProductViewSet,
    CategoryViewSet,
    SubcategoryViewSet,
    RoomViewSet,
    StyleViewSet,
    ColorViewSet
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'subcategories', SubcategoryViewSet, basename='subcategories')
router.register(r'rooms', RoomViewSet, basename='rooms')
router.register(r'styles', StyleViewSet, basename='styles')
router.register(r'colors', ColorViewSet, basename='colors')

from products.api.views import MostWatchedAPIView

urlpatterns = [
    path('most-watched/', MostWatchedAPIView.as_view(), name='products_most_watched'),
    path('', include(router.urls)),
]
