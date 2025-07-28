from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from authentication.models import Subscription
from django.utils import timezone
from .serializers import CheckoutSessionSerializer
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
                subscription.save()
            else:
                Subscription.objects.create(
                    user=request.user,
                    stripe_id=session.id
                )

        return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)

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
                    subscription.end_date = timezone.now() + timezone.timedelta(days=30)
                    subscription.save()


        return Response(status=200)