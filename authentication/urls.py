from django.urls import path
from .views import (
    UserLoginView, 
    UserRegisterView,
    SocialLoginView,
    UserResetPasswordView,
    VerifyOTPView,
    UpdatePasswordView,
    ProfileView,
    AboutView,
)

urlpatterns = [
    path('login/', UserLoginView.as_view()),
    path('sign-up/', UserRegisterView.as_view()),
    path('social/', SocialLoginView.as_view()),
    path('reset-password/', UserResetPasswordView.as_view()),
    path('verify-otp/', VerifyOTPView.as_view()),
    path('update-password/', UpdatePasswordView.as_view()),
    path('profile/', ProfileView.as_view()),
    path('about/', AboutView.as_view()),
]