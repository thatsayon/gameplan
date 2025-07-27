from django.urls import path
from .views import UserLoginView, UserRegisterView

urlpatterns = [
    path('login/', UserLoginView.as_view()),
    path('sign-up/', UserRegisterView.as_view()),
]