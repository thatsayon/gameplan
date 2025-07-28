from django.urls import path
from .views import (
    UserLoginView, 
    UserRegisterView,
    AboutView,
)

urlpatterns = [
    path('login/', UserLoginView.as_view()),
    path('sign-up/', UserRegisterView.as_view()),
    path('about/', AboutView.as_view()),
]