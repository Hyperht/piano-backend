from rest_framework import serializers
from orders.models import Cart, CartItem, Order, OrderItem
from users.models import Address, Area
from products.api.serializers import ProductSearchSerializer
from orders.services.order_service import OrderService

class ShippingAddressSerializer(serializers.ModelSerializer):
    area_id = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), 
        source='area', 
        write_only=True
    )
    governorate_name = serializers.CharField(source='area.governorate.name', read_only=True)
    area_name = serializers.CharField(source='area.name', read_only=True)

    class Meta:
        model = Address
        fields = [
            'first_name', 
            'last_name', 
            'phone_number_1', # The old implementation said phone_number but model says phone_number_1
            'phone_number_2',
            'street_address', 
            'apartment_details', 
            'id', 
            'area_id', 
            'governorate_name', 
            'area_name'
        ]
        read_only_fields = ['id', 'governorate_name', 'area_name']

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSearchSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    cart_subtotal = serializers.SerializerMethodField() 
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'cart_subtotal', 'created_at']

    def get_cart_subtotal(self, obj):
        return obj.get_cart_total()

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    item_total = serializers.DecimalField(source='subtotal', max_digits=10, decimal_places=2, read_only=True)

    def get_product_name(self, obj):
        return obj.product.name if obj.product else 'Deleted Product'

    def get_product_image(self, obj):
        try:
            if obj.product:
                image_obj = obj.product.gallery_images.filter(is_primary=True).first()
                if not image_obj:
                    image_obj = obj.product.gallery_images.first()
                if image_obj and image_obj.image:
                    request = self.context.get('request')
                    url = image_obj.image.url
                    return request.build_absolute_uri(url) if request else url
            return None
        except Exception:
            return None

    class Meta:
        model = OrderItem
        fields = ['product_id', 'product_name', 'product_image', 'quantity', 'price_snapshot', 'item_total']
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 
            'final_total', 
            'status', 
            'status_display',
            'created_at'
        ]
        read_only_fields = fields

class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = ShippingAddressSerializer(read_only=True) 
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 
            'user', 
            'shipping_address',
            'cart_subtotal', 
            'shipping_cost', 
            'coupon_discount', 
            'final_total',
            'coupon_code_used',
            'payment_method',
            'payment_status',
            'transaction_id',
            'status',
            'status_display',
            'created_at',
            'items', 
        ]
        read_only_fields = fields 

class CheckoutSerializer(serializers.Serializer):
    shipping_address = ShippingAddressSerializer(help_text="Nested fields for the shipping address.")
    payment_method = serializers.CharField(max_length=50)
    coupon_code = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        allow_null=True,
        default='',
        help_text="Optional coupon code to apply at checkout."
    )

    def create(self, validated_data):
        user = self.context['request'].user
        address_data = validated_data.pop('shipping_address')
        payment_method = validated_data.pop('payment_method')
        coupon_code = validated_data.pop('coupon_code', '') or None

        try:
            return OrderService.place_order(user, address_data, payment_method, coupon_code=coupon_code)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

