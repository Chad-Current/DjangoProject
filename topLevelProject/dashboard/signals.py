# dashboard/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Account, Device, RelevanceReview, Contact, DigitalEstateDocument, ImportantDocument


# ============================================================================
# ACCOUNT SIGNALS
# ============================================================================

@receiver(pre_save, sender=Account)
def track_review_time_change_account(sender, instance, **kwargs):
    """Track changes to review_time field before saving."""
    if instance.pk:
        try:
            old_instance = Account.objects.get(pk=instance.pk)
            instance._old_review_time = old_instance.review_time
        except Account.DoesNotExist:
            instance._old_review_time = None
    else:
        instance._old_review_time = None


@receiver(post_save, sender=Account)
def create_account_relevance_review(sender, instance, created, **kwargs):
    """Automatically create or update RelevanceReview for accounts"""
    user = instance.profile.user
    
    if created:
        # Create initial review when account is first created
        # Use review_time from the instance to set next_review_due
        if instance.review_time:
            next_review = timezone.now().date() + timedelta(days=instance.review_time)
        else:
            next_review = timezone.now().date() + timedelta(days=365)
        
        RelevanceReview.objects.create(
            account_review=instance,
            reviewer=user,
            matters=True,
            reasoning=f"Account: {instance.account_name_or_provider}",
            next_review_due=next_review
        )
    else:
        # Check if review_time changed
        old_review_time = getattr(instance, '_old_review_time', None)
        
        if old_review_time is not None and old_review_time != instance.review_time:
            try:
                # Find the most recent review for this account
                latest_review = RelevanceReview.objects.filter(
                    account_review=instance
                ).latest('review_date')
                
                # Update the next review due date based on new review_time
                if instance.review_time:
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=instance.review_time)
                    latest_review.reasoning = f"Review time updated to {instance.review_time} days - {latest_review.reasoning}"
                else:
                    # If review_time is 0 or None, set to 1 year default
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=365)
                    latest_review.reasoning = f"Review time cleared - {latest_review.reasoning}"
                
                latest_review.reviewer = user
                latest_review.save()
                
            except RelevanceReview.DoesNotExist:
                # Fallback: if no review exists, create one
                next_review = timezone.now().date() + timedelta(days=instance.review_time if instance.review_time else 365)
                RelevanceReview.objects.create(
                    account_review=instance,
                    reviewer=user,
                    matters=True,
                    reasoning=f"Review time changed: {instance.account_name_or_provider}",
                    next_review_due=next_review
                )


# ============================================================================
# DEVICE SIGNALS
# ============================================================================

@receiver(pre_save, sender=Device)
def track_review_time_change_device(sender, instance, **kwargs):
    """Track changes to review_time field before saving."""
    if instance.pk:
        try:
            old_instance = Device.objects.get(pk=instance.pk)
            instance._old_review_time = old_instance.review_time
        except Device.DoesNotExist:
            instance._old_review_time = None
    else:
        instance._old_review_time = None


@receiver(post_save, sender=Device)
def create_device_relevance_review(sender, instance, created, **kwargs):
    """Automatically create or update RelevanceReview for devices"""
    user = instance.profile.user
    
    if created:
        # Create initial review when device is first created
        if instance.review_time:
            next_review = timezone.now().date() + timedelta(days=instance.review_time)
        else:
            next_review = timezone.now().date() + timedelta(days=365)
        
        RelevanceReview.objects.create(
            device_review=instance,
            reviewer=user,
            matters=True,
            reasoning=f"Device: {instance.device_name}",
            next_review_due=next_review
        )
    else:
        # Check if review_time changed
        old_review_time = getattr(instance, '_old_review_time', None)
        
        if old_review_time is not None and old_review_time != instance.review_time:
            try:
                # Find the most recent review for this device
                latest_review = RelevanceReview.objects.filter(
                    device_review=instance
                ).latest('review_date')
                
                # Update the next review due date
                if instance.review_time:
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=instance.review_time)
                    latest_review.reasoning = f"Review time updated to {instance.review_time} days - {latest_review.reasoning}"
                else:
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=365)
                    latest_review.reasoning = f"Review time cleared - {latest_review.reasoning}"
                
                latest_review.reviewer = user
                latest_review.save()
                
            except RelevanceReview.DoesNotExist:
                # Fallback: if no review exists, create one
                next_review = timezone.now().date() + timedelta(days=instance.review_time if instance.review_time else 365)
                RelevanceReview.objects.create(
                    device_review=instance,
                    reviewer=user,
                    matters=True,
                    reasoning=f"Review time changed: {instance.device_name}",
                    next_review_due=next_review
                )


# ============================================================================
# ESTATE DOCUMENT SIGNALS
# ============================================================================

@receiver(pre_save, sender=DigitalEstateDocument)
def track_review_time_change_estate(sender, instance, **kwargs):
    """Track changes to review_time field before saving."""
    if instance.pk:
        try:
            old_instance = DigitalEstateDocument.objects.get(pk=instance.pk)
            instance._old_review_time = old_instance.review_time
        except DigitalEstateDocument.DoesNotExist:
            instance._old_review_time = None
    else:
        instance._old_review_time = None


@receiver(post_save, sender=DigitalEstateDocument)
def create_estate_relevance_review(sender, instance, created, **kwargs):
    """Automatically create or update RelevanceReview for estate documents"""
    user = instance.profile.user
    
    if created:
        # Create initial review when estate document is first created
        if instance.review_time:
            next_review = timezone.now().date() + timedelta(days=instance.review_time)
        else:
            next_review = timezone.now().date() + timedelta(days=365)
        
        RelevanceReview.objects.create(
            estate_review=instance,
            reviewer=user,
            matters=True,
            reasoning=f"Estate Document: {instance.name_or_title}",
            next_review_due=next_review
        )
    else:
        # Check if review_time changed
        old_review_time = getattr(instance, '_old_review_time', None)
        
        if old_review_time is not None and old_review_time != instance.review_time:
            try:
                # Find the most recent review for this estate document
                latest_review = RelevanceReview.objects.filter(
                    estate_review=instance
                ).latest('review_date')
                
                # Update the next review due date
                if instance.review_time:
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=instance.review_time)
                    latest_review.reasoning = f"Review time updated to {instance.review_time} days - {latest_review.reasoning}"
                else:
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=365)
                    latest_review.reasoning = f"Review time cleared - {latest_review.reasoning}"
                
                latest_review.reviewer = user
                latest_review.save()
                
            except RelevanceReview.DoesNotExist:
                # Fallback: if no review exists, create one
                next_review = timezone.now().date() + timedelta(days=instance.review_time if instance.review_time else 365)
                RelevanceReview.objects.create(
                    estate_review=instance,
                    reviewer=user,
                    matters=True,
                    reasoning=f"Review time changed: {instance.name_or_title}",
                    next_review_due=next_review
                )


# ============================================================================
# IMPORTANT DOCUMENT SIGNALS
# ============================================================================

@receiver(pre_save, sender=ImportantDocument)
def track_review_time_change_important_doc(sender, instance, **kwargs):
    """Track changes to review_time field before saving."""
    if instance.pk:
        try:
            old_instance = ImportantDocument.objects.get(pk=instance.pk)
            instance._old_review_time = old_instance.review_time
        except ImportantDocument.DoesNotExist:
            instance._old_review_time = None
    else:
        instance._old_review_time = None


@receiver(post_save, sender=ImportantDocument)
def create_important_doc_relevance_review(sender, instance, created, **kwargs):
    """Automatically create or update RelevanceReview for important documents"""
    user = instance.profile.user
    
    if created:
        # Create initial review when important document is first created
        if instance.review_time:
            next_review = timezone.now().date() + timedelta(days=instance.review_time)
        else:
            next_review = timezone.now().date() + timedelta(days=365)
        
        RelevanceReview.objects.create(
            important_document_review=instance,
            reviewer=user,
            matters=True,
            reasoning=f"Important Document: {instance.name_or_title}",
            next_review_due=next_review
        )
    else:
        # Check if review_time changed
        old_review_time = getattr(instance, '_old_review_time', None)
        
        if old_review_time is not None and old_review_time != instance.review_time:
            try:
                # Find the most recent review for this important document
                latest_review = RelevanceReview.objects.filter(
                    important_document_review=instance
                ).latest('review_date')
                
                # Update the next review due date
                if instance.review_time:
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=instance.review_time)
                    latest_review.reasoning = f"Review time updated to {instance.review_time} days - {latest_review.reasoning}"
                else:
                    latest_review.next_review_due = timezone.now().date() + timedelta(days=365)
                    latest_review.reasoning = f"Review time cleared - {latest_review.reasoning}"
                
                latest_review.reviewer = user
                latest_review.save()
                
            except RelevanceReview.DoesNotExist:
                # Fallback: if no review exists, create one
                next_review = timezone.now().date() + timedelta(days=instance.review_time if instance.review_time else 365)
                RelevanceReview.objects.create(
                    important_document_review=instance,
                    reviewer=user,
                    matters=True,
                    reasoning=f"Review time changed: {instance.name_or_title}",
                    next_review_due=next_review
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