from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from users.models import Governorate, Area, Address
from dashboard.serializers import (
    GovernorateSerializer, AreaSerializer, AddressSerializer
)

class GovernorateViewSet(viewsets.ModelViewSet):
    queryset = Governorate.objects.all().order_by('name')
    serializer_class = GovernorateSerializer
    permission_classes = [IsAdminUser]

class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all().order_by('name')
    serializer_class = AreaSerializer
    permission_classes = [IsAdminUser]

class AddressViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only view of all user addresses for admin purposes.
    """
    queryset = Address.objects.all().order_by('-created_at')
    serializer_class = AddressSerializer
    permission_classes = [IsAdminUser]
