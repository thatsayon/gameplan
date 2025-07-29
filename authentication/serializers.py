from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.files.storage import default_storage
from .models import Subscription
import base64
import uuid

User = get_user_model()

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(max_length=128, required=True, write_only=True)

class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(max_length=128, required=True, write_only=True)

class UserResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length=6, required=True)

class UpdatePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    new_password = serializers.CharField(max_length=128, required=True)
    confirm_password = serializers.CharField(max_length=128, required=True)

    def validate(self, data):
        password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")

        return data

class ProfileSerializer(serializers.ModelSerializer):
    profile_pic = serializers.CharField(required=False)
    profile_type = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'profile_pic', 'profile_type']

    def update(self, instance, validated_data):
        profile_pic_base64 = validated_data.pop('profile_pic', None)

        if profile_pic_base64:
            try:
                # Expecting data like: data:image/png;base64,iVBORw0KGgoAAAANS...
                format, imgstr = profile_pic_base64.split(';base64,') 
                ext = format.split('/')[-1]  # png, jpeg, etc.
                file_name = f"profile_pics/{uuid.uuid4()}.{ext}"

                # Save image to media storage
                file = ContentFile(base64.b64decode(imgstr), name=file_name)
                path = default_storage.save(file_name, file)
                instance.profile_pic = default_storage.url(path)  # Save full URL
            except Exception as e:
                raise serializers.ValidationError({"profile_pic": "Invalid base64 image."})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
    
    def get_profile_type(self, obj):
        sub = Subscription.objects.filter(user=obj).first()
        if sub:
            if sub.subscription_type == 'FREE':
                return "General Account"
            elif sub.subscription_type == 'PAID':
                return "Premium Account"
            elif sub.subscription_type == 'TRIAL':
                return "Trial Account"
        return None

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
        token['email'] = user.email
        token['profile_pic'] = user.profile_pic
        subscription_type = Subscription.objects.filter(user=user).first().subscription_type
        if subscription_type == 'TRIAL':
            token['trial_start_date'] = Subscription.objects.filter(user=user).first().start_date
        return token