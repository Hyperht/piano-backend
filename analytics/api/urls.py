from django.urls import path
from .views import (
    DashboardSummaryAPIView,
    SalesBreakdownAPIView,
    TopProductsAPIView,
    TopProductsAllAPIView,
    TopWatchedAllAPIView,
    TopWishlistedAllAPIView,
    FunnelAnalyticsAPIView,
    IntentAnalyticsAPIView,
    TrafficSourceAPIView
)
from analytics.views import TopCustomersAPIView

urlpatterns = [
    path('summary/', DashboardSummaryAPIView.as_view(), name='analytics_summary'),
    path('sales-breakdown/', SalesBreakdownAPIView.as_view(), name='analytics_sales_breakdown'),
    path('top-products/', TopProductsAPIView.as_view(), name='analytics_top_products'),
    path('top-products/all/', TopProductsAllAPIView.as_view(), name='analytics_top_products_all'),
    path('top-watched/all/', TopWatchedAllAPIView.as_view(), name='analytics_top_watched_all'),
    path('top-wishlisted/all/', TopWishlistedAllAPIView.as_view(), name='analytics_top_wishlisted_all'),
    path('top-customers/', TopCustomersAPIView.as_view(), name='analytics_top_customers'),
    
    path('funnel/', FunnelAnalyticsAPIView.as_view(), name='analytics_funnel'),
    path('intent/', IntentAnalyticsAPIView.as_view(), name='analytics_intent'),
    path('traffic/', TrafficSourceAPIView.as_view(), name='analytics_traffic_source'),
]
