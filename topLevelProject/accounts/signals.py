from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser

@receiver(post_save, sender=CustomUser)
def send_tier_expiration_warning(sender, instance, created, **kwargs):
    """
    Send email warning when Essentials tier is about to expire
    """
    if not created and instance.subscription_tier == 'essentials':
        days_remaining = instance.days_until_essentials_expires()
        
        # Send warning at 30 days, 7 days, and 1 day before expiration
        if days_remaining in [30, 7, 1]:
            subject = f'Your Essentials Edit Access Expires in {days_remaining} Day(s)'
            message = f"""
            Hello {instance.username},
            
            Your Essentials tier edit access will expire in {days_remaining} day(s).
            
            After expiration, you will still have view-only access to all your data,
            but you won't be able to add, edit, or delete items.
            
            Consider upgrading to Legacy tier for lifetime full access.
            
            Visit your account dashboard to upgrade: {settings.SITE_URL}/accounts/payment/
            
            Best regards,
            Your Team
            """
            
            # Only send if email settings are configured
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.email],
                    fail_silently=True,
                )
            except:
                pass


@receiver(post_save, sender=CustomUser)
def notify_tier_upgrade(sender, instance, created, **kwargs):
    """
    Send confirmation email when user upgrades tier
    """
    if not created and instance.has_paid:
        if instance.subscription_tier == 'essentials' and instance.payment_date:
            subject = 'Welcome to Essentials Tier!'
            message = f"""
            Hello {instance.username},
            
            Thank you for upgrading to Essentials tier!
            
            You now have full edit access for 1 year until {instance.essentials_expires.strftime('%B %d, %Y')}.
            After that, you'll have lifetime view-only access.
            
            Best regards,
            Your Team
            """
        elif instance.subscription_tier == 'legacy':
            subject = 'Welcome to Legacy Tier!'
            message = f"""
            Hello {instance.username},
            
            Thank you for upgrading to Legacy tier!
            
            You now have lifetime full access to all features.
            
            Best regards,
            Your Team
            """
        else:
            return
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                fail_silently=True,
            )
        except:
            pass