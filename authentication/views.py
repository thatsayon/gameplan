from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from .serializers import (
    UserLoginSerializer,
    UserRegisterSerializer,
    AboutSerializer,
    CustomTokenObtainPairSerializer,
)
from .utils import generate_unique_username

User = get_user_model()

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )

        if user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        refresh = CustomTokenObtainPairSerializer.get_token(user)
        access = refresh.access_token

        return Response({
            "access_token": str(access),
            "refresh_token": str(refresh),
            "message": "Login successful."
        }, status=status.HTTP_200_OK)


class UserRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"error": "Username or email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        refresh = CustomTokenObtainPairSerializer.get_token(user)
        access = refresh.access_token

        return Response({
            "access_token": str(access),
            "refresh_token": str(refresh),
            "message": "User registered successfully."
        }, status=status.HTTP_201_CREATED)

class AboutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = AboutSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        user = request.user

        if user.favorite_sport or user.details:
            return Response({
                "message": "About already updated."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AboutSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save(user=request.user)

        return Response({
            "message": "About updated successfully."
        }, status=status.HTTP_200_OK)
