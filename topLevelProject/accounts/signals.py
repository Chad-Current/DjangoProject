from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def notify_subscription_change(sender, instance, created, **kwargs):
    """
    Send a confirmation email when a user's subscription status changes.
    Covers initial activation and renewal notifications.
    """
    if created or not instance.has_paid:
        return

    tier = instance.subscription_tier
    if tier not in ('essentials', 'legacy'):
        return

    # Only send when subscription is newly active (webhook sets this)
    if instance.subscription_status != 'active':
        return

    tier_name = tier.capitalize()
    interval = instance.subscription_interval.capitalize() if instance.subscription_interval else 'Annual'
    period_end = (
        instance.subscription_current_period_end.strftime('%B %d, %Y')
        if instance.subscription_current_period_end else 'N/A'
    )

    subject = f'Your {tier_name} Subscription is Active'
    message = f"""
Hello {instance.username},

Thank you for subscribing to the {tier_name} plan ({interval} billing)!

You now have full edit access to all your digital estate planning data.
Your subscription renews on {period_end}.

You can manage or cancel your subscription at any time from your account settings:
{settings.SITE_URL}/accounts/subscription/manage/

Best regards,
Your Team
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            fail_silently=True,
        )
    except Exception:
        pass


@receiver(post_save, sender=CustomUser)
def notify_subscription_cancellation(sender, instance, created, **kwargs):
    """
    Send a heads-up when a user schedules their subscription for cancellation.
    """
    if created or not instance.subscription_cancel_at_period_end:
        return

    period_end = (
        instance.subscription_current_period_end.strftime('%B %d, %Y')
        if instance.subscription_current_period_end else 'the end of your billing period'
    )

    subject = 'Your Subscription Cancellation is Scheduled'
    message = f"""
Hello {instance.username},

We've received your cancellation request.

You will retain full access to your data until {period_end}.
After that date, your account will switch to view-only mode — your data will always be accessible.

If you change your mind, you can resubscribe at any time:
{settings.SITE_URL}/accounts/payment/

Best regards,
Your Team
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            fail_silently=True,
        )
    except Exception:
        pass
