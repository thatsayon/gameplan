from django.urls import path
from .views import CreateCheckoutSessionView, FreeTrialView, WebhookView, SubscriptionSettingView

urlpatterns = [
    path('create-checkout-session/', CreateCheckoutSessionView.as_view()),
    path('free-trial/', FreeTrialView.as_view()),
    path('setting/', SubscriptionSettingView.as_view()),
    path('webhook/', WebhookView.as_view()),
]