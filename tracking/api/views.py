from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import ProductTrackingSerializer, EmptyTrackingSerializer
from tracking.services.tracking_service import TrackingService
from products.models import Product
from rest_framework.exceptions import NotFound

class ProductViewTrackingAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ProductTrackingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            product = Product.objects.get(id=serializer.validated_data['product_id'])
        except Product.DoesNotExist:
            raise NotFound(detail="Product not found")

        TrackingService.track_product_view(request=request, product=product)

        return Response({"status": "ok"})

class AddToCartTrackingAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ProductTrackingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            product = Product.objects.get(id=serializer.validated_data['product_id'])
        except Product.DoesNotExist:
            raise NotFound(detail="Product not found")

        TrackingService.track_add_to_cart(request=request, product=product)

        return Response({"status": "ok"})

class WishlistTrackingAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ProductTrackingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            product = Product.objects.get(id=serializer.validated_data['product_id'])
        except Product.DoesNotExist:
            raise NotFound(detail="Product not found")

        TrackingService.track_wishlist(request=request, product=product)

        return Response({"status": "ok"})

class CheckoutTrackingAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = EmptyTrackingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        TrackingService.track_checkout(request=request)

        return Response({"status": "ok"})
