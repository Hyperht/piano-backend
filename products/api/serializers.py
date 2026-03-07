from rest_framework import serializers
from products.models import Product, Category, Subcategory, Color, Room, Style, ProductImage, Review
from users.models import Favorite

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
        if obj.image:
            return obj.image.url
        return None

class CategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    subcategories = SubcategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'name_en', 'name_ar', 'image', 'subcategories']

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name', 'hex_code']

class RoomSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'name', 'name_en', 'name_ar', 'image']

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

class StyleSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Style
        fields = ['id', 'name', 'name_en', 'name_ar', 'image']

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.ImageField(source='image', read_only=True)
    color = ColorSerializer(read_only=True)

    class Meta:
        model = ProductImage
        fields = ['id', 'url', 'color', 'is_primary']

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'user_name', 'rating', 'title', 'comment', 'created_at']
        read_only_fields = ['user', 'created_at']

class ProductSearchSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    subcategory = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'short_description', 'original_price', 
            'sale_price', 'is_on_sale', 'image', 'rating',
            'category', 'subcategory', 'is_favorited'
        ]

    def get_image(self, obj):
        image_obj = obj.gallery_images.filter(is_primary=True).first()
        if not image_obj:
            image_obj = obj.gallery_images.first()
            
        if image_obj and image_obj.image:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(image_obj.image.url)
            return image_obj.image.url
        return None

    def get_category(self, obj):
        if obj.category:
            return {"id": obj.category.id, "name": obj.category.name}
        return None

    def get_subcategory(self, obj):
        if obj.subcategory:
            return {"id": obj.subcategory.id, "name": obj.subcategory.name}
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                # Optimized: obj.favorite_set might be prefetch_related
                for fav in obj.favorite_set.all():
                    if fav.user_id == request.user.id:
                        return True
            except AttributeError:
                return Favorite.objects.filter(user=request.user, product=obj).exists()
        return False


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    subcategory = SubcategorySerializer(read_only=True)
    colors = ColorSerializer(many=True, read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)
    styles = StyleSerializer(many=True, read_only=True)
    gallery_images = ProductImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'short_description', 'description',
            'original_price', 'sale_price', 'is_on_sale', 'quantity',
            'dimensions', 'specifications',
            'image', 'gallery_images',
            'category', 'subcategory', 'colors', 'rooms', 'styles',
            'rating', 'reviews', 'is_favorited'
        ]
        
    def get_image(self, obj):
        image_obj = obj.gallery_images.filter(is_primary=True).first()
        if not image_obj:
            image_obj = obj.gallery_images.first()
            
        if image_obj and image_obj.image:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(image_obj.image.url)
            return image_obj.image.url
        return None


    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                for fav in obj.favorite_set.all():
                    if fav.user_id == request.user.id:
                        return True
            except AttributeError:
                return Favorite.objects.filter(user=request.user, product=obj).exists()
        return False
