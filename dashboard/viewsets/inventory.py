from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from inventory.models import StockMovement
from dashboard.serializers import StockMovementSerializer

class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all().order_by('-created_at')
    serializer_class = StockMovementSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['product', 'reason']
