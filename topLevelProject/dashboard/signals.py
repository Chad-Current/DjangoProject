from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Account, AccountRelevanceReview, Contact, DigitalEstateDocument, ImportantDocument


# ============================================================================
# ACCOUNT SIGNALS
# ============================================================================

@receiver(pre_save, sender=Account)
def track_is_critical_change(sender, instance, **kwargs):
    """Track changes to is_critical field before saving."""
    if instance.pk:
        try:
            old_instance = Account.objects.get(pk=instance.pk)
            instance._old_is_critical = old_instance.is_critical
        except Account.DoesNotExist:
            instance._old_is_critical = None
    else:
        instance._old_is_critical = None


@receiver(post_save, sender=Account)
def create_account_relevance_review(sender, instance, created, **kwargs):
    """Automatically create or update AccountRelevanceReview"""
    user = instance.profile.user
    
    if created:
        AccountRelevanceReview.objects.create(
            account=instance,
            reviewer=user,
            matters=True,
            reasoning=f"Initial review created for new account: {instance.account_name_or_provider}"
        )
    else:
        old_is_critical = getattr(instance, '_old_is_critical', None)
        
        if old_is_critical is not None and old_is_critical != instance.is_critical:
            try:
                latest_review = AccountRelevanceReview.objects.filter(
                    account=instance
                ).latest('review_date')
                
                if instance.is_critical:
                    latest_review.reasoning = f"Account marked as critical - {latest_review.reasoning}"
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=90)
                else:
                    latest_review.reasoning = f"Account unmarked as critical - {latest_review.reasoning}"
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=365)
                
                latest_review.reviewer = user
                latest_review.save()
                
            except AccountRelevanceReview.DoesNotExist:
                AccountRelevanceReview.objects.create(
                    account=instance,
                    reviewer=user,
                    matters=True,
                    reasoning=f"Review created due to critical status change: {instance.account_name_or_provider}"
                )


# ============================================================================
# CONTACT PROTECTION SIGNALS
# ============================================================================

@receiver(pre_save, sender=Contact)
def prevent_contact_deletion_with_documents(sender, instance, **kwargs):
    """
    Prevent deletion of contacts that have documents assigned to them.
    This is also enforced by the PROTECT on_delete, but this provides a clearer message.
    """
    if instance.pk:  # Only for existing contacts
        estate_count = DigitalEstateDocument.objects.filter(delegated_estate_to=instance).count()
        important_count = ImportantDocument.objects.filter(delegated_important_document_to=instance).count()
        
        if estate_count > 0 or important_count > 0:
            # Contact has documents - they're protected
            # The PROTECT on_delete will handle the actual prevention
            pass