from products.models import Product
from django.db.models import F

def get_stock_needed(limit=5):
    products_qs = Product.objects.filter(quantity__lt=3).select_related('category').prefetch_related('gallery_images').order_by('quantity')[:limit]
    
    results = []
    for p in products_qs:
        image_obj = p.gallery_images.filter(is_primary=True).first() or p.gallery_images.first()
        results.append({
            'id': p.id,
            'name': p.name,
            'quantity': p.quantity,
            'category': p.category.name if p.category else 'No Category',
            'image': image_obj.image.url if image_obj and image_obj.image else None
        })
    return results
