from rest_framework import serializers

class CheckoutSessionSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    currency = serializers.CharField()
    duration_type = serializers.CharField()
    success_url = serializers.CharField()
    cancel_url = serializers.CharField()

    def validate_amount(self, value):
        if value < 0.5:
            raise serializers.ValidationError("Minimum amount is $0.50")
        return value