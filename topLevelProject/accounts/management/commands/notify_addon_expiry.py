"""
Management command: notify_addon_expiry

Finds users whose add-on subscription has expired (addon_active=True but
addon_expires is in the past), sends each one an expiry notification email,
then sets addon_active=False so the command is idempotent on subsequent runs.

Vault data (VaultEntry rows) is never touched — passwords remain encrypted
in the database and are restored as soon as the user renews.

Usage:
    python manage.py notify_addon_expiry

Recommended cron (daily at 3 AM):
    0 3 * * * /path/to/venv/bin/python manage.py notify_addon_expiry
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import CustomUser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Email users whose add-on has expired and mark addon_active=False.'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_users = CustomUser.objects.filter(
            addon_active=True,
            addon_expires__lt=now,
        )

        count = 0
        for user in expired_users:
            self._notify(user)
            user.addon_active = False
            user.save(update_fields=['addon_active'])
            count += 1
            logger.info("notify_addon_expiry: processed user %s (pk=%s)", user.email, user.pk)

        self.stdout.write(self.style.SUCCESS(f'Processed {count} expired add-on(s).'))

    def _notify(self, user):
        subject = 'Your Password Vault Add-On Has Expired'
        site_url = getattr(settings, 'SITE_URL', '')
        message = (
            f"Hello {user.username},\n\n"
            "Your Password Vault add-on subscription has expired. "
            "Your stored passwords are still safely encrypted — no data has been deleted.\n\n"
            "To restore vault access for yourself and any designated contacts, "
            f"renew your add-on at:\n{site_url}/accounts/addon/\n\n"
            "Best regards,\nYour Team"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as exc:
            logger.error(
                "notify_addon_expiry: failed to email %s — %s", user.email, exc
            )
