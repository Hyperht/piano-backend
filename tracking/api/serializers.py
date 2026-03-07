from rest_framework import serializers

class ProductTrackingSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)

class EmptyTrackingSerializer(serializers.Serializer):
    pass
