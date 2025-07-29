from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import UserAccount, Subscription
from chatbot.models import FreeLimit

@receiver(post_save, sender=UserAccount)
def create_subscription(sender, instance, created, **kwargs):
    """Create a Subscription record when a new UserAccount is created."""
    if created:  # Check if the user is being created (not updated)
        # Create a default subscription (for free users initially)
        Subscription.objects.create(
            user=instance,
            subscription_type='free',  # Set the default subscription type
            start_date=None,
            end_date=None  # Free users might not have an end date initially
        )

        FreeLimit.objects.create(
            user=instance,
        )
