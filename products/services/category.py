from django.utils.text import slugify
from products.models import Category

def create_category(name: str, **kwargs) -> Category:
    """Handles business logic for category creation."""
    slug = kwargs.pop('slug', None) or slugify(name)
    category = Category.objects.create(name=name, slug=slug, **kwargs)
    return category
