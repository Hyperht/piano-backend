from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from users.models import HeroSlide, PromoBanner, PromoGridCategory
from marketing.api.serializers import (
    HeroSlideSerializer, PromoBannerSerializer, PromoGridCategorySerializer
)
from marketing.selectors.coupon_selectors import (
    get_coupon_analytics,
    get_top_performing_coupons,
    get_campaign_performance,
    get_top_coupons,
)
import openpyxl
from django.http import HttpResponse
from marketing.services.coupon_service import CouponService
from orders.models import Cart


class HeroSlideViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HeroSlide.objects.filter(is_active=True).order_by('order')
    serializer_class = HeroSlideSerializer
    permission_classes = [AllowAny]


class PromoGridCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PromoGridCategory.objects.filter(is_active=True).order_by('order')
    serializer_class = PromoGridCategorySerializer
    permission_classes = [AllowAny]


@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_promo_banner(request):
    promo_banner = PromoBanner.objects.filter(is_active=True).order_by('-end_date').first()
    if promo_banner:
        serializer = PromoBannerSerializer(promo_banner, context={'request': request})
        return Response(serializer.data)
    return Response(
        {"error": "No active promo banner found"},
        status=status.HTTP_404_NOT_FOUND
    )


class CouponAnalyticsAPIView(APIView):
    """
    Returns overall coupon analytics.
    Admin-only endpoint. Thin view — delegates to selector.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = get_coupon_analytics()
        return Response(data)


class TopCouponsAPIView(APIView):
    """
    Returns top performing coupons natively using CouponUsage.
    Admin-only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 5))
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            export = request.query_params.get('export')

            data = get_top_coupons(limit=limit, start_date=start_date, end_date=end_date)
            
            if export == 'excel':
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Top Coupons"
                ws.append(["Coupon Code", "Discount Value", "Usage Count", "Total Generated Revenue"])
                
                for item in data:
                    ws.append([
                        item['code'],
                        float(item['discount_value']) if item.get('discount_value') else 0.0,
                        item.get('usage_count', 0),
                        float(item['revenue_generated']) if item.get('revenue_generated') else 0.0
                    ])
                    
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename=top_coupons.xlsx'
                wb.save(response)
                return response

            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CampaignPerformanceAPIView(APIView):
    """
    Returns campaign performance with revenue lift analysis.
    Admin-only. Thin view.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        vendor_id = request.query_params.get('vendor_id')
        data = get_campaign_performance(vendor=vendor_id)
        return Response(data)


class ValidateCouponView(APIView):
    """
    Public-facing view to validate a coupon code.
    Accessible to any authenticated user.
    """
    permission_classes = [AllowAny] # Change to IsAuthenticated if needed, but usually we allow check

    def post(self, request):
        coupon_code = request.data.get('code')
        if not coupon_code:
            return Response({"error": "Coupon code is required"}, status=status.HTTP_400_BAD_REQUEST)

        # We need the user's cart subtotal to validate
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required to apply coupon"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            cart = Cart.objects.get(user=user)
            cart_subtotal = cart.get_cart_total()
        except Cart.DoesNotExist:
            return Response({"error": "User does not have an active cart"}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = CouponService.validate_and_calculate_discount(
                coupon_code=coupon_code,
                cart_subtotal=cart_subtotal,
                user=user
            )
            coupon = result['coupon']
            discount_amount = result['discount_amount']

            return Response({
                "valid": True,
                "code": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": str(coupon.discount_value),
                "discount_amount": str(discount_amount),
                "new_total": str(cart_subtotal - discount_amount)
            })
        except ValidationError as e:
            return Response({"valid": False, "error": str(e.message) if hasattr(e, 'message') else str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"valid": False, "error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
