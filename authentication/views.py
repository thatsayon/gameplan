from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.mail import EmailMultiAlternatives
from datetime import datetime, timedelta
from .serializers import (
    UserLoginSerializer,
    UserRegisterSerializer,
    AboutSerializer,
    CustomTokenObtainPairSerializer,
    UserResetPasswordSerializer,
    UpdatePasswordSerializer,
    ProfileSerializer,
    OTPVerifySerializer,
)
from .models import OTP
from .utils import generate_unique_username
import random
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

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


class UserResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Validate input data using the serializer
        serializer = UserResetPasswordSerializer(data=request.data)

        # If serializer is not valid, return errors
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve user by email
        user = User.objects.filter(email=serializer.validated_data['email']).first()

        # If user doesn't exist, return error
        if not user:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the user is scheduled for deletion
        if user.deletion_scheduled_at:
            return Response(
                {"error": "User is scheduled for deletion."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate a secure OTP
        otp_code = random.randint(100000, 999999)
        otp = OTP.objects.create(user=user, code=str(otp_code), expire_at=datetime.now() + timedelta(minutes=10))

        # Email subject
        subject = "Reset your password"

        # HTML content (for better email formatting)
        html_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Password Reset Request</h2>
            <p>Hello {user.username},</p>
            <p>We received a request to reset your password. Use the OTP below to proceed:</p>

            <div style="background-color: #f4f4f4; padding: 20px; text-align: center; border-radius: 8px; font-size: 24px; font-weight: bold;">
                {otp_code}
            </div>

            <p>This OTP is valid for the next 10 minutes. If you did not request a password reset, please ignore this email.</p>

            <hr>
            <p style="font-size: 12px; color: #888;">If you’re having trouble, contact our support team.</p>
        </div>
        """

        # Plain text content (fallback for email clients that don't support HTML)
        text_content = f"""
        Password Reset Request
        ==========================
        Hello {user.username},

        We received a request to reset your password. Use the OTP below to proceed:

        OTP: {otp_code}

        This OTP is valid for the next 10 minutes. If you did not request a password reset, please ignore this email.

        If you’re having trouble, contact our support team.
        """

        # Send the email
        try:
            msg = EmailMultiAlternatives(subject, text_content, from_email=None, to=[user.email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Error sending email to {user.email}: {e}")
            return Response(
                {"error": "Failed to send reset email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"message": "Password reset OTP sent successfully."},
            status=status.HTTP_200_OK
        )


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.filter(email=serializer.validated_data['email']).first()
        if not user:
            return Response(
                {"error": "Invalid email."},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp = OTP.objects.filter(user=user, code=serializer.validated_data['otp']).first()

        if not otp:
            return Response(
                {"error": "Invalid OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp.is_expired():
            return Response(
                {"error": "OTP expired."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.can_update_pass = True  
        user.save()
        OTP.objects.filter(user=user).delete()

        return Response({
            "message": "You can now update your password."
        }, status=status.HTTP_200_OK)

class UpdatePasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UpdatePasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.filter(email=serializer.validated_data['email']).first()
        if not user:
            return Response(
                {"error": "Invalid email."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.can_update_pass:
            return Response(
                {"error": "You can't update your password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(serializer.validated_data['new_password'])  # securely hashes the password
        user.can_update_pass = False
        user.save()

        return Response({
            "message": "Password updated successfully."
        }, status=status.HTTP_200_OK)

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = ProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        user = request.user
        serializer = ProfileSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
