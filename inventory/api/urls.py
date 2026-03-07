from django.urls import path
from .views import StockNeededAPIView

urlpatterns = [
    path('stock-needed/', StockNeededAPIView.as_view(), name='inventory_stock_needed'),
]
