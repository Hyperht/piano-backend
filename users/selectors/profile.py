from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from rest_framework.exceptions import NotFound, APIException

from users.models import Favorite
from orders.models import Order

User = get_user_model()

def get_user_profile(user):
    """
    Selector for fetching a comprehensive user profile, 
    including their favorites and recent orders.
    """
    try:
        qs = User.objects.filter(pk=user.pk).prefetch_related(
            Prefetch('favorites', queryset=Favorite.objects.select_related('product')),
            Prefetch('orders', queryset=Order.objects.order_by('-created_at'))
        )
        return qs.get()
    except User.DoesNotExist:
        raise NotFound("User not found")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise APIException("Failed to retrieve user profile")
