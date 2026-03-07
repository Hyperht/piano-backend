from django.db.models import Prefetch
from products.models import Product, Review
from users.models import Favorite

def get_product_detail_queryset(user):
    """
    Selector for fetching highly optimized product details for the frontend.
    """
    qs = Product.objects.filter(is_active=True).select_related(
        'category',
        'subcategory'
    ).prefetch_related(
        'colors',
        'gallery_images__color',
        'rooms',
        'styles',
        Prefetch(
            'reviews',
            queryset=Review.objects.select_related('user').order_by('-created_at')
        )
    )

    if user.is_authenticated:
        qs = qs.prefetch_related(
            Prefetch(
                'favorite_set',
                queryset=Favorite.objects.filter(user=user)
            )
        )
    return qs

def get_most_watched(limit=5):
    """
    Returns the most watched products based on views_count.
    """
    return Product.objects.filter(is_active=True)\
        .values("id", "name", "views_count")\
        .order_by("-views_count")[:limit]
