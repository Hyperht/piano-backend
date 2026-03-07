from rest_framework import serializers

class AnalyticsFilterSerializer(serializers.Serializer):
    vendor_id = serializers.IntegerField(required=False, allow_null=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
