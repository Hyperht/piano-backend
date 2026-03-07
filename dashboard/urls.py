from django.urls import path, include
from rest_framework.routers import DefaultRouter
from analytics.api.views import (
    DashboardAnalyticsView, RevenueChartView, OrdersChartView, AdminProfileView, TopProductsView
)
from dashboard.viewsets.catalog import (
    ProductViewSet, CategoryViewSet, SubcategoryViewSet, 
    ColorViewSet, RoomViewSet, StyleViewSet, PromoBannerViewSet,
    ProductImageViewSet
)
from dashboard.viewsets.orders import OrderViewSet
from dashboard.viewsets.users import UserViewSet
from dashboard.exports.views import ExportAnalyticsView
from dashboard.imports.views import ImportDataView

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubcategoryViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'users', UserViewSet)
router.register(r'colors', ColorViewSet)
router.register(r'rooms', RoomViewSet)
router.register(r'styles', StyleViewSet)
router.register(r'promo-banners', PromoBannerViewSet)
router.register(r'products/images', ProductImageViewSet, basename="product-images")

# Marketing
from dashboard.viewsets.marketing import CouponViewSet, HeroSlideViewSet, PromoGridCategoryViewSet
router.register(r'coupons', CouponViewSet)
router.register(r'hero-slides', HeroSlideViewSet)
router.register(r'promo-grid', PromoGridCategoryViewSet)

# Support
from dashboard.viewsets.support import ReviewViewSet, ContactMessageViewSet
router.register(r'reviews', ReviewViewSet)
router.register(r'contact', ContactMessageViewSet)

# Locations
from dashboard.viewsets.locations import GovernorateViewSet, AreaViewSet, AddressViewSet
router.register(r'governorates', GovernorateViewSet)
router.register(r'areas', AreaViewSet)
router.register(r'addresses', AddressViewSet)

# Sales
# Sales
from dashboard.viewsets.sales import CartViewSet, CartItemViewSet, FavoriteViewSet
router.register(r'cart', CartViewSet)
router.register(r'cart-items', CartItemViewSet)
router.register(r'favorites', FavoriteViewSet)

# Inventory & Tracking & Vendors
from dashboard.viewsets.inventory import StockMovementViewSet
from dashboard.viewsets.vendors import VendorViewSet

router.register(r'inventory', StockMovementViewSet)
router.register(r'vendors', VendorViewSet)

urlpatterns = [
    path('analytics/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
    path('revenue-chart/', RevenueChartView.as_view(), name='revenue-chart'),
    path('orders-chart/', OrdersChartView.as_view(), name='orders-chart'),
    path('top-products/', TopProductsView.as_view(), name='top-products'),
    path('profile/', AdminProfileView.as_view(), name='admin-profile'),
    path('export/', ExportAnalyticsView.as_view(), name='export-analytics'),
    path('import/<str:model_name>/', ImportDataView.as_view(), name='import-data'),
    path('', include(router.urls)),
]
