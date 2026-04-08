from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='recovery.ProfileAccessGrant')
def notify_grantee_on_create(sender, instance, created, **kwargs):
    """Email the grantee immediately when a new ProfileAccessGrant is created."""
    if created and instance.is_active:
        from recovery.views import _send_grant_access_email
        _send_grant_access_email(instance)
