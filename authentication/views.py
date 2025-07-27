from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from .serializers import (
    UserLoginSerializer,
    UserRegisterSerializer,
    CustomTokenObtainPairSerializer
)
from .utils import generate_unique_username

User = get_user_model()

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )

        if user is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        access = refresh.access_token

        response = Response({
            "access_token": str(access),
            "refresh_token": str(refresh),
        }, status=status.HTTP_200_OK,)


        return response

class UserRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=serializer.validated_data['email'],
                    password=serializer.validated_data['password'],
                    username=serializer.validated_data['username']
                )
                user.is_active = True
                user.save()
        except IntegrityError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        refresh = CustomTokenObtainPairSerializer.get_token(user)
        access = refresh.access_token

        response = Response({
            "access_token": str(access),
            "refresh_token": str(refresh),
        }, status=status.HTTP_200_OK,)

        return response