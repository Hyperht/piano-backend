# Admin serializers for all dashboard CRUD views — FK fields accept integer IDs, M2M use PrimaryKeyRelatedField
import logging
from rest_framework import serializers
from users.models import CustomUser, PromoBanner, Governorate, Area, Address
from products.models import Product, Category, Subcategory, Color, Room, Style, ProductImage
from orders.models import Order, OrderItem
from marketing.models import Coupon

logger = logging.getLogger(__name__)

# ─── Catalog ─────────────────────────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ['slug']


class SubcategorySerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='parent_category.name')

    class Meta:
        model = Subcategory
        fields = ['id', 'name', 'parent_category', 'category_name', 'image', 'slug']
        read_only_fields = ['id', 'category_name']


class ProductSerializer(serializers.ModelSerializer):
    """
    Full admin product serializer.

    Write rules:
      - colors / rooms / styles → array of integer IDs
      - vendor / category / subcategory → integer ID
      - image → file upload (optional)
      - ALL computed / normalized fields are read-only
    """
    # Image: write-only upload; read back via to_representation
    image = serializers.ImageField(write_only=True, required=False, allow_null=True)

    # Read-only display helpers
    category_name    = serializers.ReadOnlyField(source='category.name')
    subcategory_name = serializers.ReadOnlyField(source='subcategory.name')
    vendor_name      = serializers.ReadOnlyField(source='vendor.name')

    # Explicit M2M write fields — MUST be PrimaryKeyRelatedField for IDs to work
    colors = serializers.PrimaryKeyRelatedField(
        queryset=Color.objects.all(), many=True, required=False
    )
    rooms = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(), many=True, required=False
    )
    styles = serializers.PrimaryKeyRelatedField(
        queryset=Style.objects.all(), many=True, required=False
    )

    class Meta:
        model = Product
        # Explicit field list — excludes editable=False computed columns
        # (name_normalized, description_normalized) so they never arrive
        # in validated_data and cause unexpected errors.
        fields = [
            'id',
            # Core
            'name', 'description', 'dimensions',
            # Pricing
            'original_price', 'sale_price', 'is_on_sale',
            # Meta
            'rating', 'views_count', 'quantity', 'low_stock_threshold',
            'is_active', 'created_at',
            # FK
            'vendor', 'category', 'subcategory',
            # M2M
            'colors', 'rooms', 'styles',
            # Image (write-only)
            'image',
            # Read-only display
            'vendor_name', 'category_name', 'subcategory_name',
        ]
        read_only_fields = ['id', 'created_at', 'views_count', 'vendor_name', 'category_name', 'subcategory_name']
        extra_kwargs = {
            'rating': {'required': False, 'allow_null': True},
            'sale_price': {'required': False, 'allow_null': True},
            'subcategory': {'required': False, 'allow_null': True},
            'dimensions': {'required': False, 'allow_blank': True, 'allow_null': True},
            'quantity': {'required': False},
            'low_stock_threshold': {'required': False},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        img = instance.gallery_images.filter(is_primary=True).first() or instance.gallery_images.first()
        if img and img.image:
            request = self.context.get('request')
            data['image'] = request.build_absolute_uri(img.image.url) if request else img.image.url
        else:
            data['image'] = None
        return data

    def validate(self, data):
        """Validate subcategory belongs to selected category."""
        category   = data.get('category', getattr(self.instance, 'category', None))
        subcategory = data.get('subcategory', getattr(self.instance, 'subcategory', None))

        if subcategory and category:
            if subcategory.parent_category != category:
                raise serializers.ValidationError({
                    'subcategory': 'Selected subcategory does not belong to the chosen category.'
                })
        return data

    def create(self, validated_data):
        image = validated_data.pop('image', None)
        # M2M are popped by ProductService — we pass them through
        product = self.Meta.model.objects.create(
            **{k: v for k, v in validated_data.items()
               if k not in ('colors', 'rooms', 'styles')}
        )
        colors = validated_data.get('colors', [])
        rooms  = validated_data.get('rooms',  [])
        styles = validated_data.get('styles', [])
        if colors: product.colors.set(colors)
        if rooms:  product.rooms.set(rooms)
        if styles: product.styles.set(styles)

        if image:
            from products.models import ProductImage
            ProductImage.objects.create(product=product, image=image, is_primary=True)

        return product

    def update(self, instance, validated_data):
        image  = validated_data.pop('image',  None)
        colors = validated_data.pop('colors', None)
        rooms  = validated_data.pop('rooms',  None)
        styles = validated_data.pop('styles', None)

        # Update scalar fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        # Update M2M — only when explicitly provided
        if colors is not None: instance.colors.set(colors)
        if rooms  is not None: instance.rooms.set(rooms)
        if styles is not None: instance.styles.set(styles)

        if image:
            from products.models import ProductImage
            ProductImage.objects.filter(product=instance).update(is_primary=False)
            ProductImage.objects.create(product=instance, image=image, is_primary=True)

        return instance


# ─── Orders ──────────────────────────────────────────────────────────────────

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ['price_snapshot', 'subtotal', 'commission_amount', 'vendor', 'order']


class OrderSerializer(serializers.ModelSerializer):
    """
    Admin Order serializer.
    Update: only status and payment_status are writable.
    All financial totals are read-only computed values.
    """
    items       = OrderItemSerializer(many=True, read_only=True)
    user_email  = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = [
            'total_amount', 'final_total', 'cart_subtotal',
            'shipping_cost', 'coupon_discount',
            'created_at', 'updated_at',
            'user', 'coupon', 'shipping_address',
            'region_snapshot',
        ]

    def update(self, instance, validated_data):
        """Only allow status and payment_status updates from admin panel."""
        instance.status = validated_data.get('status', instance.status)
        instance.payment_status = validated_data.get('payment_status', instance.payment_status)
        instance.save()
        return instance


# ─── Users ───────────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined']
        read_only_fields = ['id', 'date_joined']


# ─── Lookup Tables ───────────────────────────────────────────────────────────

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = '__all__'

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'

class StyleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Style
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'

class PromoBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoBanner
        fields = '__all__'


# ─── Inventory & Tracking ────────────────────────────────────────────────────

from inventory.models import StockMovement
from tracking.models import ProductViewEvent

class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    class Meta:
        model = StockMovement
        fields = '__all__'

class ProductViewEventSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    user_email   = serializers.ReadOnlyField(source='user.email')
    class Meta:
        model = ProductViewEvent
        fields = '__all__'


# ─── Vendors ─────────────────────────────────────────────────────────────────

from vendors.models import Vendor

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'


# ─── Locations ────────────────────────────────────────────────────────────────

class GovernorateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Governorate
        fields = '__all__'

class AreaSerializer(serializers.ModelSerializer):
    governorate_name = serializers.ReadOnlyField(source='governorate.name')
    
    class Meta:
        model = Area
        fields = ['id', 'name', 'governorate', 'governorate_name', 'shipping_cost']
        read_only_fields = ['governorate_name']

class AddressSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')
    area_name = serializers.ReadOnlyField(source='area.name')
    governorate_name = serializers.ReadOnlyField(source='area.governorate.name')

    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['user_email', 'area_name', 'governorate_name', 'created_at', 'updated_at']

# ─── Marketing ───────────────────────────────────────────────────────────────

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'
