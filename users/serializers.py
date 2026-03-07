from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .models import (
    HeroSlide, PromoBanner,
    CustomUser, PromoGridCategory,
    Favorite,
    Governorate, Area, Address, ContactMessage,
)
from products.models import Product, Category, Subcategory, Color, Room, Style, ProductImage, Review
from orders.models import Cart, CartItem, Order, OrderItem
from marketing.models import Coupon

User = get_user_model()


# --- USER SERIALIZERS ---
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'name', 'email', 'phone_number', 'is_staff')


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, write_only=True, required=True)
    phone_number = serializers.CharField(max_length=15, write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'name', 'phone_number')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        username = validated_data['email']
        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name'),
            phone_number=validated_data.get('phone_number'),
        )
        return user


from django.contrib.auth import authenticate

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        request = self.context.get('request')
        
        self.user = authenticate(request=request, username=email, password=password)
        
        if not self.user:
            raise serializers.ValidationError({"detail": "No active account found with the given credentials"})
            
        refresh = self.get_token(self.user)
        
        data = {}
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['name'] = user.name
        token['email'] = user.email
        token['is_staff'] = getattr(user, 'is_staff', False)
        return token


# --- ROOMS AND STYLES SERIALIZERS ---
class RoomSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'name', 'name_en', 'name_ar', 'image']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class StyleSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Style
        fields = ['id', 'name', 'name_en', 'name_ar', 'image']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


# --- PRODUCT AND CATALOG SERIALIZERS ---
class ParentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name']


class SubcategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    parent_category = ParentCategorySerializer(read_only=True)

    class Meta:
        model = Subcategory
        fields = ['id', 'name', 'name_en', 'name_ar', 'image', 'parent_category']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class CategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    subcategories = SubcategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'name_en', 'name_ar', 'image', 'subcategories']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class HeroSlideSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = HeroSlide
        fields = ['id', 'title', 'subtitle', 'image', 'button_text', 'button_link']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class PromoBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoBanner
        fields = ['end_date']


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name', 'hex_code']


class ProductImageSerializer(serializers.ModelSerializer):
    color_hex = serializers.CharField(source='color.hex_code', read_only=True, allow_null=True)

    # Language specific fields (created by modeltranslation)
    alt_text_en = serializers.CharField(required=False, allow_blank=True)
    alt_text_ar = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'alt_text_en', 'alt_text_ar', 'color_hex']


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.email', read_only=True) # Changed from username to email
    
    class Meta:
        model = Review
        fields = ['id', 'user', 'rating', 'comment', 'created_at']
        read_only_fields = ['user', 'created_at']


class ProductSearchSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    category = serializers.StringRelatedField()
    subcategory = serializers.StringRelatedField()
    colors = ColorSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            # Expose both language variants when available
            'name', 'name_en', 'name_ar',
            'short_description', 'short_description_en', 'short_description_ar',
            'original_price',
            'sale_price',
            'is_on_sale',

            'rating',
            'image',
            'colors',
            'category',
            'subcategory',
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        # Try to get primary image, fallback to first image
        image_obj = obj.gallery_images.filter(is_primary=True).first()
        if not image_obj:
            image_obj = obj.gallery_images.first()
            
        if image_obj and image_obj.image and hasattr(image_obj.image, 'url'):
            return request.build_absolute_uri(image_obj.image.url) if request else image_obj.image.url
        return None




class ProductDetailSerializer(serializers.ModelSerializer):
    # ---------- NESTED READ-ONLY RELATIONS ----------
    colors = ColorSerializer(many=True, read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)
    styles = StyleSerializer(many=True, read_only=True)
    gallery_images = ProductImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    category = CategorySerializer(read_only=True)
    subcategory = SubcategorySerializer(read_only=True)

    # ---------- WRITE-ONLY IDS (ADMIN / CREATE USE) ----------
    category_id = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=Category.objects.all(),
        write_only=True,
        required=True
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        source='subcategory',
        queryset=Subcategory.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    # ---------- COMPUTED FIELDS ----------
    image = serializers.SerializerMethodField()

    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            # Provide both language variants to clients
            'name', 'name_en', 'name_ar',
            'description', 'description_en', 'description_ar',
            'short_description', 'short_description_en', 'short_description_ar',
            'dimensions',
            'original_price',
            'sale_price',
            'is_on_sale',
            'rating',

            'image',


            'gallery_images',
            'colors',
            'rooms',
            'styles',

            'category',
            'subcategory',
            'category_id',
            'subcategory_id',

            'is_favorited',
            'reviews',

            'is_active',
            'created_at',
        ]

    # ---------- IMAGE HELPERS ----------
    def get_image(self, obj):
        request = self.context.get('request')
        # Try to get primary image, fallback to first image
        image_obj = obj.gallery_images.filter(is_primary=True).first()
        if not image_obj:
            image_obj = obj.gallery_images.first()

        if image_obj and image_obj.image and hasattr(image_obj.image, 'url'):
            return request.build_absolute_uri(image_obj.image.url) if request else image_obj.image.url
        return None



    # ---------- FAVORITE CHECK ----------
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorite_set.filter(user=request.user).exists()
        return False

    def to_representation(self, instance):
        """
        Ensure the serialized product always contains arrays for collections
        and default values for optional fields to avoid frontend null errors.
        """
        data = super().to_representation(instance)
        # Collections that the frontend expects to iterate over
        data.setdefault('colors', [])
        data.setdefault('gallery_images', [])
        data.setdefault('reviews', [])
        data.setdefault('rooms', [])
        data.setdefault('styles', [])

        # Optional single values
        data.setdefault('is_favorited', False)
        data.setdefault('rating', getattr(instance, 'rating', 0))

        # Ensure language keys exist if modeltranslation created them
        data.setdefault('name_en', getattr(instance, 'name_en', ''))
        data.setdefault('name_ar', getattr(instance, 'name_ar', ''))
        data.setdefault('description_en', getattr(instance, 'description_en', ''))
        data.setdefault('description_ar', getattr(instance, 'description_ar', ''))
        data.setdefault('short_description_en', getattr(instance, 'short_description_en', ''))
        data.setdefault('short_description_ar', getattr(instance, 'short_description_ar', ''))

        return data

# -----------------------
# New Serializer for Promo Grid
# -----------------------
class PromoGridCategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = PromoGridCategory
        fields = ['id', 'title', 'title_en', 'title_ar', 'subtitle', 'subtitle_en', 'subtitle_ar', 'image', 'background_color']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

# --- LOCATION SERIALIZERS (Nested Read-Only) ---
class AreaNestedSerializer(serializers.ModelSerializer):
    """Used for nested representation within UserAddressSerializer (minimal fields)."""
    shipping_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Area
        fields = ['id', 'name', 'name_en', 'name_ar', 'shipping_cost']

class GovernorateNestedSerializer(serializers.ModelSerializer):
    """Used for nested representation within UserAddressSerializer (minimal fields)."""
    class Meta:
        model = Governorate
        fields = ['id', 'name', 'name_en', 'name_ar']

class AreaSerializer(AreaNestedSerializer):
    """Full Area serializer, includes Governorate link."""
    governorate = GovernorateNestedSerializer(read_only=True)
    class Meta(AreaNestedSerializer.Meta):
        fields = AreaNestedSerializer.Meta.fields + ['governorate']

class GovernorateSerializer(GovernorateNestedSerializer):
    """Full Governorate serializer, includes nested areas."""
    areas = AreaSerializer(many=True, read_only=True)
    class Meta(GovernorateNestedSerializer.Meta):
        fields = GovernorateNestedSerializer.Meta.fields + ['areas']

# -----------------------
# 🎯 ADDRESS SERIALIZERS (For UserAddressViewSet)
# -----------------------
class UserAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for CRUD operations on a user's saved addresses.
    Uses nested fields for read and PrimaryKey for write.
    """
    # Read-only nested representation
    area = AreaNestedSerializer(read_only=True)
    governorate = GovernorateNestedSerializer(source='area.governorate', read_only=True)
    
    # Write-only ID for creation/update (ID of the Area)
    # NOTE: The Area model already links to Governorate, so we only need Area ID.
    area_id = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), 
        source='area', 
        write_only=True
    )

    class Meta:
        model = Address
        fields = [
            'id', 
            'first_name', 
            'last_name',  
            'phone_number_1',
            'phone_number_2',
            'street_address', 
            'apartment_details', 
            'area', 
            'governorate', 
            'area_id', 
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

# -----------------------
# ADDRESS SERIALIZER FOR CHECKOUT (ShippingAddressSerializer)
# -----------------------
class ShippingAddressSerializer(serializers.ModelSerializer):
    """
    Used *only* inside the CheckoutSerializer to capture the address snapshot.
    It expects the Area ID for validation and provides nested Area/Governorate names for confirmation.
    """
    # Write-only Field: Address requires Area ID
    area_id = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), 
        source='area', 
        write_only=True
    )
    
    # Read-only confirmation fields (pulled from the Area object linked via source='area.governorate')
    governorate_name = serializers.CharField(source='area.governorate.name', read_only=True)
    area_name = serializers.CharField(source='area.name', read_only=True)

    class Meta:
        model = Address
        fields = [
            # 🎯 CRITICAL FIX: Add all fields necessary to create a new Address instance
            'first_name', 
            'last_name', 
            'phone_number_1', 
            'phone_number_2',
            'street_address', 
            'apartment_details', 
            # End of critical fields
            'id', 
            'area_id', 
            'governorate_name', 
            'area_name'
        ]
        read_only_fields = ['id', 'governorate_name', 'area_name']

# --- COUPON SERIALIZER ---
class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_type', 'discount_value', 'valid_from', 'expires_at', 'is_active']
        read_only_fields = ['discount_type', 'discount_value', 'valid_from', 'expires_at', 'is_active']

# --- SHOPPING CART SERIALIZERS ---
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSearchSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        source='product'
    )

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




# --- ORDER SERIALIZERS ---

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for displaying items within a submitted order (a historical record)."""
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_image = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        try:
            if obj.product:
                # Try to get primary image, fallback to first image
                image_obj = obj.product.gallery_images.filter(is_primary=True).first()
                if not image_obj:
                    image_obj = obj.product.gallery_images.first()
                
                if image_obj and image_obj.image:
                     request = self.context.get('request')
                     url = image_obj.image.url
                     if request is not None:
                         return request.build_absolute_uri(url)
                     return url
            return None
        except Exception:
            return None

    class Meta:
        model = OrderItem
        fields = ['product_id', 'product_name', 'product_image', 'quantity', 'price_at_purchase', 'get_total_price']
        read_only_fields = fields # All are read-only when viewing an order

class OrderListSerializer(serializers.ModelSerializer):
    """Simplified Serializer for listing a user's past orders."""
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
    """Detailed Serializer for viewing a single complete order."""
    items = OrderItemSerializer(many=True, read_only=True)
    # The address stored on the Order is used for the snapshot
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
            'items', # Nested order items
        ]
        read_only_fields = fields # All are read-only when retrieving a placed order

# --- CHECKOUT SERIALIZER ---
class CheckoutSerializer(serializers.Serializer):
    """
    Main serializer for receiving the final order submission payload from the frontend.
    It handles validation and the entire Order creation process.
    """
    # This uses the corrected ShippingAddressSerializer
    shipping_address = ShippingAddressSerializer(help_text="Nested fields for the shipping address.")
    
    payment_method = serializers.CharField(
        max_length=50, 
        help_text="e.g., 'Cash on Delivery', 'Credit Card', 'PayPal'."
    )
    # Support for optional coupon code
    coupon_code = serializers.CharField(
        max_length=50, 
        required=False, 
        allow_blank=True,
        help_text="Optional coupon code to apply."
    )
    
    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        
        # 1. Pop nested data
        address_data = validated_data.pop('shipping_address')
        payment_method = validated_data.pop('payment_method')
        coupon_code = validated_data.pop('coupon_code', None)
        
        # --- Pre-Order Checks and Calculations ---
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("User does not have an active cart.")
            
        if not cart.items.exists():
            raise serializers.ValidationError("Cannot checkout on an empty cart.")

        # Recalculate everything at the time of purchase
        cart_subtotal = cart.get_cart_total()

        # 2. Handle Shipping Address
        # We create the Address model instance right here
        # The area is validated by the nested serializer and passed as the Area object
        shipping_address = Address.objects.create(user=user, **address_data)
        
        # 3. Calculate Shipping Cost
        # Since Address now only links to Area, we access shipping_cost through Area
        shipping_cost = shipping_address.area.shipping_cost if shipping_address.area else Decimal('0.00')

        # 4. Handle Coupon/Discount
        coupon = None
        coupon_discount_amount = Decimal('0.00')
        
        if coupon_code:
            from marketing.services.coupon_service import CouponService
            try:
                result = CouponService.validate_and_calculate_discount(
                    coupon_code=coupon_code,
                    cart_subtotal=cart_subtotal,
                    user=user
                )
                coupon = result['coupon']
                coupon_discount_amount = result['discount_amount']
            except ValidationError as e:
                # If the coupon is invalid at the final checkout step, we might want to error out
                # or just proceed without discount? Usually better to error to avoid surprise.
                raise serializers.ValidationError({"coupon_code": str(e.message) if hasattr(e, 'message') else str(e)})

        
        final_total = (cart_subtotal + shipping_cost) - coupon_discount_amount
        
        if final_total < Decimal('0.00'):
            final_total = Decimal('0.00')
        
        # Quantize all decimals for clean storage
        cart_subtotal = cart_subtotal.quantize(Decimal('0.01'))
        shipping_cost = shipping_cost.quantize(Decimal('0.01'))
        coupon_discount_amount = coupon_discount_amount.quantize(Decimal('0.01'))
        final_total = final_total.quantize(Decimal('0.01'))


        # 5. Create the Order
        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            cart_subtotal=cart_subtotal,
            shipping_cost=shipping_cost,
            coupon_discount=coupon_discount_amount,
            coupon_code_used=coupon.code if coupon else None,
            final_total=final_total,
            payment_method=payment_method,
            status='PENDING' 
        )
        
        # 6. Create Order Items (The snapshot)
        order_items = []
        for cart_item in cart.items.select_related('product', 'product__vendor').all():
            product = cart_item.product
            price_snapshot = product.get_current_price()
            subtotal = price_snapshot * cart_item.quantity
            
            # Calculate commission (assuming 10% default if not set on vendor)
            vendor = product.vendor
            commission_rate = vendor.commission_rate if vendor else Decimal('0.00')
            commission_amount = (subtotal * commission_rate / Decimal(100)).quantize(Decimal('0.01'))
            
            if not vendor:
                # Assign to a default/system vendor or handle error?
                # For now, we'll try to get the first vendor as generic placeholder or create one if needed?
                # Actually, OrderItem requires vendor.
                from vendors.models import Vendor
                vendor = Vendor.objects.first()
                if not vendor:
                     # Emergency fallback - creates a system vendor
                     vendor = Vendor.objects.create(name='System Vendor', commission_rate=0.00)

            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    vendor=vendor,
                    quantity=cart_item.quantity,
                    price_snapshot=price_snapshot,
                    subtotal=subtotal,
                    commission_amount=commission_amount
                )
            )
        OrderItem.objects.bulk_create(order_items)
            
        # 7. Clear/Deactivate the User's Cart
        cart.delete() # Clears the cart and all its items

        # 8. Record Coupon Usage (Post-Creation)
        if coupon:
            from marketing.services.coupon_service import CouponService
            CouponService.record_usage(
                coupon=coupon,
                user=user,
                order=order,
                discount_applied=coupon_discount_amount
            )

        return order # CRITICAL: Ensure the created order object is returned

# --- FAVORITE SERIALIZERS ---
class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSearchSerializer(read_only=True)
    # Expose the model's `created_at` timestamp under the API-friendly
    # name `added_at` so front-end code that expects `added_at` keeps working.
    added_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'product', 'added_at']


# --- USER PROFILE SERIALIZER ---
class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializers to display a user's profile, including their favorited products and orders.
    """
    favorites = FavoriteSerializer(many=True, read_only=True)
    # The related_name on Order.user is 'orders'
    orders = OrderListSerializer(many=True, read_only=True) 
    
    class Meta:
        model = CustomUser
        # 🌟 FIX: Removed 'username' as it likely doesn't exist on CustomUser
        # if email is used as the USERNAME_FIELD.
        fields = ['id', 'email', 'name', 'phone_number', 'is_staff', 'favorites', 'orders']


# -----------------------
# Contact Message Serializer
# -----------------------
class ContactMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for the ContactMessage model.
    """
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']