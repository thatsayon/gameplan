from django.urls import path
from .views import CreateCheckoutSessionView, WebhookView

urlpatterns = [
    path('create-checkout-session/', CreateCheckoutSessionView.as_view()),
    path('webhook/', WebhookView.as_view()),
]