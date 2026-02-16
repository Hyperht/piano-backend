from rest_framework import serializers
from users.models import Product, Category, Subcategory, Order, OrderItem, CustomUser, Color, Room, Style, PromoBanner

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class SubcategorySerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='parent_category.name')
    
    class Meta:
        model = Subcategory
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    subcategory_name = serializers.ReadOnlyField(source='subcategory.name')
    
    class Meta:
        model = Product
        fields = '__all__'

    def validate(self, data):
        # Validation for Subcategory Parent
        category = data.get('category')
        subcategory = data.get('subcategory')
        
        # If partial update, get from instance if not in data
        if self.instance:
            if 'category' not in data:
                category = self.instance.category
            if 'subcategory' not in data:
                subcategory = self.instance.subcategory

        if subcategory and category:
            if subcategory.parent_category != category:
                raise serializers.ValidationError({"subcategory": "Selected subcategory does not belong to the chosen category."})
        
        return data

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = OrderItem
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = Order
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined']

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
class PromoBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoBanner
        fields = '__all__'

