from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from marketing.models import Coupon
from users.models import HeroSlide, PromoGridCategory
from users.serializers import HeroSlideSerializer, PromoGridCategorySerializer
from dashboard.serializers import CouponSerializer


# Admin CRUD viewsets for marketing entities: coupons, hero slides, and promo grid categories
class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all().order_by('-expires_at')
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
