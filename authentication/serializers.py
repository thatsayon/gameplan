from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Subscription

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(max_length=128, required=True, write_only=True)

class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(max_length=128, required=True, write_only=True)

class AboutSerializer(serializers.Serializer):
    favorite_sport = serializers.CharField(max_length=20)
    details = serializers.CharField(max_length=1000)

    def update(self, instance, validated_data):
        instance.favorite_sport = validated_data.get('favorite_sport', instance.favorite_sport)
        instance.details = validated_data.get('details', instance.details)
        instance.save()
        return instance

    def save(self, **kwargs):
        user = kwargs.get('user')
        return self.update(user, self.validated_data)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username  # Add username to the token payload
        token['full_name'] = user.full_name
        subscription_type = Subscription.objects.filter(user=user).first().subscription_type
        if subscription_type == 'TRIAL':
            token['trial_start_date'] = Subscription.objects.filter(user=user).first().start_date
        return token