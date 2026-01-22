from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Account, AccountRelevanceReview


@receiver(post_save, sender=Account)
def create_account_relevance_review(sender, instance, created, **kwargs):
    """
    Automatically create an AccountRelevanceReview when a new Account is created.
    """
    if created:
        AccountRelevanceReview.objects.create(
            account_relevance=instance,
            reviewer=instance.profile.user,  # Assuming Profile has a user field
            matters=True,  # Default to True for new accounts
            reasoning="Initial review created automatically upon account creation."
        )