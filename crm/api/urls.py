from django.urls import path, include
from rest_framework.routers import DefaultRouter
from crm.api.views import (
    ContactMessageViewSet,
    TopCustomersAPIView,
    GeographicSalesAPIView,
    TopCustomersAPIView,
    GeographicSalesAPIView,
    GeographicSalesAPIView,
    CustomerRegionBreakdownAPIView,
    AllCustomersAPIView,
    ExportCustomersAPIView,
)

router = DefaultRouter()
router.register(r'contact', ContactMessageViewSet, basename='contact')

urlpatterns = [
    path('', include(router.urls)),
    path('crm/top-customers/', TopCustomersAPIView.as_view(), name='crm-top-customers'),
    path('crm/customers/', AllCustomersAPIView.as_view(), name='crm-all-customers'),
    path('crm/customers/export/', ExportCustomersAPIView.as_view(), name='crm-export-customers'),
    path('crm/geographic-sales/', GeographicSalesAPIView.as_view(), name='crm-geographic-sales'),
    path('crm/region-breakdown/', CustomerRegionBreakdownAPIView.as_view(), name='crm-region-breakdown'),
]
