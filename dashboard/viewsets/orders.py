from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.throttling import UserRateThrottle
from orders.models import Order
from dashboard.serializers import OrderSerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related('user').prefetch_related('items__product')
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]
    filterset_fields = ['status', 'user']
    search_fields = ['id', 'user__email']
    ordering_fields = ['created_at', 'total_amount']
