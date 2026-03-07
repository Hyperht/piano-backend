from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from vendors.models import Vendor
from dashboard.serializers import VendorSerializer

class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all().order_by('-created_at')
    serializer_class = VendorSerializer
    permission_classes = [IsAdminUser]
    search_fields = ['name']
    filterset_fields = ['is_active']
