from rest_framework import serializers
from users.models import ContactMessage
from crm.models import CustomerProfile


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class CustomerProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CustomerProfile
        fields = [
            'user_id', 'username', 'email',
            'total_spent', 'orders_count', 'last_order_date',
            'region_snapshot', 'lifetime_value', 'loyalty_score',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
