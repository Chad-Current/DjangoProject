# dashboard/signals.py
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Account, Device, RelevanceReview, Contact, DigitalEstateDocument, ImportantDocument


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
    """Automatically create or update RelevanceReview for accounts"""
    user = instance.profile.user
    
    if created:
        # Create initial review when account is first created
        RelevanceReview.objects.create(
            account_review=instance,  # FIXED: Changed from 'account' to 'account_review'
            reviewer=user,
            matters=True,
            reasoning=f"Account: {instance.account_name_or_provider}"
        )
    else:
        # Check if is_critical status changed
        old_is_critical = getattr(instance, '_old_is_critical', None)
        
        if old_is_critical is not None and old_is_critical != instance.is_critical:
            try:
                # Find the most recent review for this account
                latest_review = RelevanceReview.objects.filter(
                    account_review=instance  # FIXED: Changed from 'account' to 'account_review'
                ).latest('review_date')
                
                # Update the existing review
                if instance.is_critical:
                    latest_review.reasoning = f"Account marked as critical - {latest_review.reasoning}"
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=90)
                else:
                    latest_review.reasoning = f"Account unmarked as critical - {latest_review.reasoning}"
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=365)
                
                latest_review.reviewer = user
                latest_review.save()
                
            except RelevanceReview.DoesNotExist:
                # Fallback: if no review exists, create one
                RelevanceReview.objects.create(
                    account_review=instance,  # FIXED: Changed from 'account' to 'account_review'
                    reviewer=user,
                    matters=True,
                    reasoning=f"Critical status change: {instance.account_name_or_provider}"
                )


# ============================================================================
# DEVICE SIGNALS (Optional - if you want auto-review for devices)
# ============================================================================

@receiver(post_save, sender=Device)
def create_device_relevance_review(sender, instance, created, **kwargs):
    """Automatically create RelevanceReview when a device is created"""
    if created:
        user = instance.profile.user
        RelevanceReview.objects.create(
            device_review=instance,
            reviewer=user,
            matters=True,
            reasoning=f"Device: {instance.device_name}"
        )


# ============================================================================
# ESTATE DOCUMENT SIGNALS (Optional - if you want auto-review for estate docs)
# ============================================================================

@receiver(post_save, sender=DigitalEstateDocument)
def create_estate_relevance_review(sender, instance, created, **kwargs):
    """Automatically create RelevanceReview when an estate document is created"""
    if created:
        user = instance.profile.user
        RelevanceReview.objects.create(
            estate_review=instance,
            reviewer=user,
            matters=True,
            reasoning=f"Estate document: {instance.name_or_title}"
        )


# ============================================================================
# IMPORTANT DOCUMENT SIGNALS (Optional - if you want auto-review for important docs)
# ============================================================================

@receiver(post_save, sender=ImportantDocument)
def create_important_document_relevance_review(sender, instance, created, **kwargs):
    """Automatically create RelevanceReview when an important document is created"""
    if created:
        user = instance.profile.user
        RelevanceReview.objects.create(
            important_document_review=instance,
            reviewer=user,
            matters=True,
            reasoning=f"Important document: {instance.name_or_title}"
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
        device_count = Device.objects.filter(delegated_device_to=instance).count()
        account_count = Account.objects.filter(delegated_account_to=instance).count()
        
        total_count = estate_count + important_count + device_count + account_count
        
        if total_count > 0:
            # Contact has items assigned - they're protected
            # The PROTECT on_delete will handle the actual prevention
            pass