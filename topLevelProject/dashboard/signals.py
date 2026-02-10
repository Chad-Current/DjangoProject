# dashboard/signals.py
from django.db.models.signals import post_save, pre_save, m2m_changed, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Account, AccountRelevanceReview, DelegationGrant, DigitalEstateDocument, ImportantDocument


@receiver(pre_save, sender=Account)
def track_is_critical_change(sender, instance, **kwargs):
    """
    Track changes to is_critical field before saving.
    Store the old value on the instance for comparison in post_save.
    """
    if instance.pk:  # Only for existing objects
        try:
            old_instance = Account.objects.get(pk=instance.pk)
            instance._old_is_critical = old_instance.is_critical
        except Account.DoesNotExist:
            instance._old_is_critical = None
    else:
        instance._old_is_critical = None


@receiver(post_save, sender=Account)
def create_account_relevance_review(sender, instance, created, **kwargs):
    """
    Automatically create an AccountRelevanceReview ONLY when:
    1. An Account is initially created (one-time only)
    2. The is_critical status changes - UPDATE existing review instead of creating new
    
    Args:
        sender: The model class (Account)
        instance: The actual Account instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    # Get the user from the profile
    user = instance.profile.user
    
    if created:
        # Create a new review when account is first created (ONLY TIME WE CREATE)
        AccountRelevanceReview.objects.create(
            account=instance,  # FIXED: Changed from account_relevance to account
            reviewer=user,
            matters=True,
            reasoning=f"Initial review created for new account: {instance.account_name_or_provider}"
        )
    else:
        # Check if is_critical status changed
        old_is_critical = getattr(instance, '_old_is_critical', None)
        
        if old_is_critical is not None and old_is_critical != instance.is_critical:
            # is_critical status changed - UPDATE the most recent review
            try:
                latest_review = AccountRelevanceReview.objects.filter(
                    account=instance  # FIXED: Changed from account_relevance to account
                ).latest('review_date')
                
                # Update the existing review with new reasoning and next_review_due
                if instance.is_critical:
                    latest_review.reasoning = f"Account marked as critical - {latest_review.reasoning}"
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=90)
                else:
                    latest_review.reasoning = f"Account unmarked as critical - {latest_review.reasoning}"
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=365)
                
                latest_review.reviewer = user
                latest_review.save()
                
            except AccountRelevanceReview.DoesNotExist:
                # Fallback: if no review exists, create one
                AccountRelevanceReview.objects.create(
                    account=instance,  # FIXED: Changed from account_relevance to account
                    reviewer=user,
                    matters=True,
                    reasoning=f"Review created due to critical status change: {instance.account_name}"
                )


@receiver(m2m_changed, sender=DelegationGrant.delegate_estate_documents.through)
def cleanup_empty_delegation_estate(sender, instance, action, **kwargs):
    """
    Delete delegation grant if all documents are removed
    """
    if action in ["post_remove", "post_clear"]:
        # Check if delegation still has any documents
        if instance.has_no_documents():
            instance.delete()


@receiver(m2m_changed, sender=DelegationGrant.delegate_important_documents.through)
def cleanup_empty_delegation_important(sender, instance, action, **kwargs):
    """
    Delete delegation grant if all documents are removed
    """
    if action in ["post_remove", "post_clear"]:
        # Check if delegation still has any documents
        if instance.has_no_documents():
            instance.delete()


@receiver(post_delete, sender=DigitalEstateDocument)
def cleanup_delegations_on_estate_delete(sender, instance, **kwargs):
    """
    Clean up empty delegations when an estate document is deleted
    """
    # Get all delegations that had this document
    for grant in DelegationGrant.objects.filter(delegate_estate_documents=instance):
        # The M2M relationship is already removed by CASCADE
        # Now check if grant is empty
        if grant.has_no_documents():
            grant.delete()


@receiver(post_delete, sender=ImportantDocument)
def cleanup_delegations_on_important_delete(sender, instance, **kwargs):
    """
    Clean up empty delegations when an important document is deleted
    """
    # Get all delegations that had this document
    for grant in DelegationGrant.objects.filter(delegate_important_documents=instance):
        # The M2M relationship is already removed by CASCADE
        # Now check if grant is empty
        if grant.has_no_documents():
            grant.delete()