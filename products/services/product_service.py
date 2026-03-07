from django.db import transaction
from django.utils.text import slugify
from products.models import Product, Color, Room, Style, ProductSpecification, ProductSpecificationValue
from rest_framework.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

def _validate_product_data(data: dict, instance: Product = None):
    original_price = data.get('original_price', getattr(instance, 'original_price', 0))
    if original_price is not None and original_price <= 0:
        raise ValidationError({"original_price": "Price must be strictly greater than 0."})
        
    is_on_sale = data.get('is_on_sale', getattr(instance, 'is_on_sale', False))
    sale_price = data.get('sale_price', getattr(instance, 'sale_price', None))
    
    if is_on_sale:
        if sale_price is None or sale_price <= 0:
            raise ValidationError({"sale_price": "Sale price must be greater than 0 when on sale."})
        if sale_price >= original_price:
            raise ValidationError({"sale_price": "Sale price must be strictly less than original price."})
            
def _handle_specifications(product: Product, specs_data: list):
    # specs_data expected format: [{'name': 'Color', 'value': 'Red'}, ...]
    if not specs_data:
        return
        
    ProductSpecificationValue.objects.filter(product=product).delete()
    
    for spec in specs_data:
        spec_obj, _ = ProductSpecification.objects.get_or_create(name=spec['name'])
        ProductSpecificationValue.objects.create(
            product=product,
            specification=spec_obj,
            value=spec['value']
        )


class ProductService:
    @staticmethod
    @transaction.atomic
    def create_product(validated_data: dict, user=None) -> Product:
        """
        Handles the creation of a product, including setting up
        many-to-many relationships safely.
        """
        # Vendor ownership validation logic placeholder if needed via user
        if user and hasattr(user, 'vendor'):
            validated_data['vendor'] = user.vendor

        _validate_product_data(validated_data)
        
        # Extract M2M and related data safely
        colors = validated_data.pop('colors', [])
        rooms = validated_data.pop('rooms', [])
        styles = validated_data.pop('styles', [])
        specs_data = validated_data.pop('specifications_data', [])
        
        # Handle Category and Subcategory if passed as dicts (from nested serializers)
        category_data = validated_data.pop('category', None)
        if isinstance(category_data, dict) and 'id' in category_data:
            from products.models import Category
            validated_data['category_id'] = category_data['id']
            
        subcategory_data = validated_data.pop('subcategory', None)
        if isinstance(subcategory_data, dict) and 'id' in subcategory_data:
            from products.models import Subcategory
            validated_data['subcategory_id'] = subcategory_data['id']

        # Create the main product instance
        product = Product.objects.create(**validated_data)

        # Handle M2M relationships
        if colors:
            product.colors.set(colors)
        if rooms:
            product.rooms.set(rooms)
        if styles:
            product.styles.set(styles)
            
        _handle_specifications(product, specs_data)

        return product

    @staticmethod
    @transaction.atomic
    def update_product(product: Product, validated_data: dict, user=None) -> Product:
        """
        Handles updating an existing product, including 
        many-to-many relationships safely.
        """
        if user and hasattr(user, 'vendor') and product.vendor != user.vendor:
            raise ValidationError({"vendor": "You do not own this product."})

        _validate_product_data(validated_data, instance=product)

        colors = validated_data.pop('colors', None)
        rooms = validated_data.pop('rooms', None)
        styles = validated_data.pop('styles', None)
        specs_data = validated_data.pop('specifications_data', None)

        category_data = validated_data.pop('category', None)
        if isinstance(category_data, dict) and 'id' in category_data:
            validated_data['category_id'] = category_data['id']
        elif category_data is not None and not isinstance(category_data, dict):
            validated_data['category'] = category_data
            
        subcategory_data = validated_data.pop('subcategory', None)
        if isinstance(subcategory_data, dict) and 'id' in subcategory_data:
            validated_data['subcategory_id'] = subcategory_data['id']
        elif subcategory_data is not None and not isinstance(subcategory_data, dict):
            validated_data['subcategory'] = subcategory_data

        # Update direct fields
        for field, value in validated_data.items():
            setattr(product, field, value)
        product.save()

        # Update M2M relationships if provided
        if colors is not None:
            product.colors.set(colors)
        if rooms is not None:
            product.rooms.set(rooms)
        if styles is not None:
            product.styles.set(styles)
            
        if specs_data is not None:
            _handle_specifications(product, specs_data)

        return product

    @staticmethod
    def delete_product(product: Product, user=None):
        """
        Deletes a product, but only if it's not tied to active orders.
        """
        if user and hasattr(user, 'vendor') and product.vendor != user.vendor:
            raise ValidationError({"vendor": "You do not own this product."})

        has_active_orders = product.orderitem_set.filter(
            order__status__in=['NEW', 'CONFIRMED', 'SHIPPED']
        ).exists()
        
        if has_active_orders:
            raise ValidationError("Cannot delete product: it is associated with active orders.")
            
        product.delete()

    @staticmethod
    @transaction.atomic
    def update_stock(product: Product, quantity_change: int):
        """
        Updates stock for a product and emits StockLowEvent if threshold is breached.
        """
        product.quantity += quantity_change
        if product.quantity < 0:
            raise ValidationError("Insufficient stock available.")
            
        product.save(update_fields=['quantity'])
        
        if product.quantity < product.low_stock_threshold:
            from core.events.dispatcher import emit
            from core.events.events import StockLowEvent
            emit(StockLowEvent(
                product_id=product.id,
                vendor_id=product.vendor_id if product.vendor else None,
                current_stock=product.quantity
            ))
