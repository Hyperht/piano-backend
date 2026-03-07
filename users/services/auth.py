from django.db import transaction, IntegrityError
from rest_framework.exceptions import APIException
from users.models import Address

def set_default_address(user, address_id: int) -> Address:
    """
    Sets a specific address as the default for a user, 
    un-setting any other default addresses atomically.
    """
    try:
        address_to_set = Address.objects.get(user=user, pk=address_id)
        with transaction.atomic():
            Address.objects.filter(user=user, is_default=True).exclude(pk=address_id).update(is_default=False)
            address_to_set.is_default = True
            address_to_set.save(update_fields=['is_default'])
        return address_to_set
    except Address.DoesNotExist:
        raise Address.DoesNotExist("Address not found.")
    except IntegrityError:
        raise APIException('Failed to set default address due to a database constraint.')
