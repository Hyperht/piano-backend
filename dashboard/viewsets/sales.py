from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from users.models import Favorite
from orders.models import Cart, CartItem
from users.serializers import CartSerializer, CartItemSerializer, FavoriteSerializer

class CartViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin view to inspect user carts.
    """
    queryset = Cart.objects.all().order_by('-updated_at')
    serializer_class = CartSerializer
    permission_classes = [IsAdminUser]

class CartItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [IsAdminUser]

class FavoriteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Favorite.objects.all().order_by('-created_at')
    serializer_class = FavoriteSerializer
    permission_classes = [IsAdminUser]
