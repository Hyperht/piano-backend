from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from users.models import Coupon, HeroSlide, PromoGridCategory
from users.serializers import (
    HeroSlideSerializer, 
    PromoGridCategorySerializer,
    # Assuming CouponSerializer exists or needs to be created. 
    # If it doesn't exist in users.serializers, we might need to define it here or imported generically.
    # Looking at users/views.py, ApplyCouponView uses CartSerializer, so we might need a specific CouponSerializer.
)
from rest_framework import serializers

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all().order_by('-valid_to')
    serializer_class = CouponSerializer
    permission_classes = [IsAdminUser]

class HeroSlideViewSet(viewsets.ModelViewSet):
    queryset = HeroSlide.objects.all().order_by('order')
    serializer_class = HeroSlideSerializer
    permission_classes = [IsAdminUser]

class PromoGridCategoryViewSet(viewsets.ModelViewSet):
    queryset = PromoGridCategory.objects.all().order_by('order')
    serializer_class = PromoGridCategorySerializer
    permission_classes = [IsAdminUser]
