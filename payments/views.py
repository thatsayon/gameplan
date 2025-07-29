from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from authentication.models import Subscription
from authentication.serializers import CustomTokenObtainPairSerializer
from django.utils import timezone
from .serializers import CheckoutSessionSerializer, SubscriptionSettingSerializer
from .stripe_service import create_checkout_session
import json
import stripe
from django.conf import settings

class CreateCheckoutSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        serializer = CheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = Subscription.objects.filter(user=request.user).first()
        if subscription and subscription.subscription_type == 'PAID':
            return Response({"detail": "Already subscribed"}, status=status.HTTP_400_BAD_REQUEST)
        
        session = create_checkout_session(**serializer.validated_data)
        if session:
            subscription = Subscription.objects.filter(user=request.user).first()
            if subscription:
                subscription.stripe_id = session.id
                subscription.duration_type = serializer.validated_data['duration_type']
                subscription.save()
            else:
                Subscription.objects.create(
                    user=request.user,
                    stripe_id=session.id
                )

        return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)


class FreeTrialView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        subscription = Subscription.objects.filter(user=request.user).first()
        if subscription and subscription.subscription_type == 'TRIAL':
            return Response({"detail": "Already subscribed"}, status=status.HTTP_400_BAD_REQUEST)

        new_subscription = Subscription.objects.create(
            user=request.user,
            subscription_type='TRIAL',
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=7),
            amount_paid=0,
            duration_type='WEEK'
        )

        # Generate tokens AFTER subscription is saved
        refresh = CustomTokenObtainPairSerializer.get_token(request.user)

        # Add trial_start_date explicitly
        refresh['trial_start_date'] = str(new_subscription.start_date)

        access = refresh.access_token

        response_data = {
            "access_token": str(access),
            "refresh_token": str(refresh),
            "message": "Free trial started successfully."
        }

        return Response(response_data, status=status.HTTP_200_OK)

class SubscriptionSettingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subscription = Subscription.objects.filter(user=request.user).first()
        if not subscription:
            return Response({"message": "No subscription found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = SubscriptionSettingSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        subscription = Subscription.objects.filter(user=request.user).first()
        if not subscription:
            return Response({"message": "No subscription found."}, status=status.HTTP_404_NOT_FOUND)
        
        subscription.subscription_type = 'FREE'
        subscription.amount_paid = 0
        subscription.start_date = None
        subscription.end_date = None
        subscription.save()

        return Response({"message": "Subscription deleted successfully."}, status=status.HTTP_200_OK)

class WebhookView(APIView):
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            return Response(status=400)
        except stripe.error.SignatureVerificationError:
            return Response(status=400)


        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            if session:
                subscription = Subscription.objects.filter(stripe_id=session.id).first()
                if subscription:
                    subscription.subscription_type = 'PAID'
                    subscription.amount_paid = session.amount_total / 100
                    subscription.start_date = timezone.now()
                    if subscription.duration_type == 'MONTH':
                        subscription.end_date = timezone.now() + timezone.timedelta(days=30)
                    elif subscription.duration_type == 'YEAR':
                        subscription.end_date = timezone.now() + timezone.timedelta(days=365)
                    elif subscription.duration_type == 'WEEK':
                        subscription.end_date = timezone.now() + timezone.timedelta(days=7)
                    subscription.save()


        return Response(status=200)