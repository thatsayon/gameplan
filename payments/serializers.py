from rest_framework import serializers
from authentication.models import Subscription

class CheckoutSessionSerializer(serializers.Serializer):
    amount = serializers.DecimalField(decimal_places=2, max_digits=3)
    currency = serializers.CharField()
    duration_type = serializers.CharField()
    success_url = serializers.CharField()
    cancel_url = serializers.CharField()

    def validate_amount(self, value):
        if value < 0.5:
            raise serializers.ValidationError("Minimum amount is $0.50")
        return value

class SubscriptionSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['id', 'subscription_type', 'amount_paid', 'end_date']